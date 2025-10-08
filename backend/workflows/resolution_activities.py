# File: backend/workflows/resolution_activities.py
from temporalio import activity
from backend.workflows.shared import ResolutionInput, SynthesizedSolution
from typing import List, Dict
from backend.services.constants import AGENT_SIGNATURE
# Removed unused sqrt import
import numpy as np

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))

def cluster_embeddings(items: List[Dict], embeddings: List[np.ndarray], similarity_threshold: float = 0.90) -> List[int]:
    """Return indices of representatives after simple agglomerative clustering.
    Greedy: iterate, assign to existing cluster if sim > threshold.
    Representative = first (lowest distance previously computed externally) entry in cluster.
    """
    clusters: List[List[int]] = []
    for idx, emb in enumerate(embeddings):
        placed = False
        for cluster in clusters:
            rep_idx = cluster[0]
            if _cosine(embeddings[rep_idx], emb) >= similarity_threshold:
                cluster.append(idx)
                placed = True
                break
        if not placed:
            clusters.append([idx])
    # Representative indices are first element of each cluster
    return [cluster[0] for cluster in clusters]

def compute_confidence(distances: List[float], coverage_ratio: float, external_used: bool) -> float:
    sims = [1/(1+d) for d in distances if d is not None]
    if not sims:
        return 0.15
    top_sim = max(sims)
    avg_sim = sum(sims)/len(sims)
    external_boost = 0.05 if external_used and top_sim < 0.45 else 0
    raw = 0.55*top_sim + 0.30*avg_sim + 0.10*coverage_ratio + external_boost
    return max(0.0, min(raw, 0.98))

@activity.defn
class ResolutionActivities:
    def __init__(self):
        from backend.services.rag_service import rag_service
        from backend.services.llm_service import llm_service
        from backend.services.jira_client import jira_service
        from backend.services.db_service import db_service
        
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.jira_service = jira_service
        self.db_service = db_service
        
    @activity.defn
    async def find_and_synthesize_solutions_activity(self, data: ResolutionInput) -> Dict:
        """
        Finds similar tickets and uses an LLM to synthesize multiple potential solutions.
        Returns top 3 solutions to be presented in the Admin UI.
        """
        activity.logger.info(f"Resolution: Finding similar solutions for ticket {data.ticket_key}...")
        
        similar_tickets = self.rag_service.find_similar_solutions(
            query_text=data.ticket_bundled_text,
            top_k=8,  # fetch a few more then threshold filter will prune
            max_distance=1.0  # tuneable threshold; lower = stricter similarity
        )
        internal_distances = [t.get("distance") for t in similar_tickets if t.get("distance") is not None]

        # Smarter external augmentation trigger (quality aware)
        top_distance = min(internal_distances) if internal_distances else None
        need_external = (
            not internal_distances or
            (top_distance is not None and top_distance > 0.55) or
            (len(internal_distances) > 1 and (sorted(internal_distances)[1] - sorted(internal_distances)[0]) / (sorted(internal_distances)[0] + 1e-6) > 1.2)
        )

        # --- External augmentation (Phase 1 heuristic) ---
        from backend.services.web_search_service import web_search_service
        from backend.services.external_ingest_service import external_ingest_service
        external_sources: List[Dict] = []
        if need_external:
            try:
                activity.logger.info("Resolution: Triggering external augmentation (quality heuristics).")
                raw_results = web_search_service.search(data.ticket_bundled_text, max_results=3)
                if raw_results:
                    external_sources = external_ingest_service.ingest_results(raw_results)
                    activity.logger.info(f"Resolution: Ingested {len(external_sources)} external sources.")
            except Exception as e:
                activity.logger.warning(f"External augmentation failed (continuing with internal only): {e}")

        # Normalize internal similar ticket format to align with external for mixed prompting
        normalized_internal = []
        if similar_tickets:
            # Embeddings for clustering: reuse rag_service model lazily
            self.rag_service._ensure_model()
            embeddings = [self.rag_service.embedding_model.encode(f"{t['summary']}\n{t['resolution']}") for t in similar_tickets]
            rep_indices = cluster_embeddings(similar_tickets, embeddings)
            for idx in rep_indices:
                t = similar_tickets[idx]
                normalized_internal.append({
                    "source_type": "internal",
                    "ticket_key": t["ticket_key"],
                    "summary": t["summary"],
                    "resolution": t["resolution"],
                    "distance": t["distance"],
                })
            activity.logger.info(f"Resolution: Reduced {len(similar_tickets)} internal tickets to {len(normalized_internal)} representatives via clustering.")

        combined_for_llm = normalized_internal + external_sources
        if not combined_for_llm:
            # Force external search attempt one more time (defensive) then bail with explicit empty internal notice
            activity.logger.warning(f"No internal or external sources after augmentation for {data.ticket_key}.")
            return {
                "solutions": [{
                    "solution_text": "No internal knowledge available and external search produced no actionable context. Provide generic triage: (1) Reproduce issue (2) Collect logs (3) Capture recent config changes (4) Escalate with performance diagnostics.",
                    "confidence": 0.0,
                    "llm_provider_model": "no-context",
                    "sources": []
                }],
                "ticket_context": data.ticket_bundled_text
            }

        activity.logger.info(f"Resolution: Internal={len(similar_tickets)} External={len(external_sources)} sources prepared for synthesis.")
        # Tag sources more explicitly for downstream display
        for s in combined_for_llm:
            if s.get("source_type") == "internal":
                s["display_ref"] = f"INT:{s['ticket_key']}"
            elif s.get("source_type") == "external":
                s["display_ref"] = f"WEB:{s.get('title','ext')}"

        # Modified to get multiple solution alternatives
        solutions = self.llm_service.generate_solution_alternatives(
            ticket_context=data.ticket_bundled_text,
            ranked_solutions=combined_for_llm,
            num_alternatives=3
        )

        # Compute evidence-based confidence & guardrail validate
        coverage_ratio = 1.0  # Placeholder: could derive from validation log later
        external_used = bool(external_sources)
        base_conf = compute_confidence(internal_distances, coverage_ratio, external_used)

        from backend.services.solution_validator import validate_solution
        internal_keys = [t["ticket_key"] for t in normalized_internal]
        external_indices = [str(i+1) for i, _ in enumerate(external_sources)]

        adjusted: List[Dict] = []
        decay = [1.0, 0.93, 0.87]
        for i, sol in enumerate(solutions):
            cleaned_text, issues, is_valid = validate_solution(sol.get("solution_text", ""), internal_keys, external_indices)
            local_conf = base_conf * decay[i if i < len(decay) else -1]
            if not is_valid:
                local_conf = min(local_conf, 0.55)  # penalize invalid
            sol["solution_text"] = cleaned_text
            sol["confidence"] = round(local_conf, 4)
            sol["validation_issues"] = [iss.to_dict() for iss in issues]
            sol["guardrail_valid"] = is_valid
            adjusted.append(sol)
        solutions = adjusted
        # Local heuristic fallback if all solutions empty or failed
        if not solutions or all((not s.get('solution_text')) or 'No alternatives generated.' in s.get('solution_text') for s in solutions):
            activity.logger.warning("All LLM solutions empty/failed; injecting heuristic fallback solution.")
            fallback_text = (
                "Preliminary heuristic guidance (LLM unavailable):\n"
                "1. Reproduce and capture exact error/log snippet.\n"
                "2. Identify recent changes (deployments/config).\n"
                "3. Compare working vs failing environment.\n"
                "4. Collect impact scope (users/transactions).\n"
                "5. Escalate with diagnostics if unresolved." )
            solutions = [{
                'solution_text': fallback_text,
                'confidence': round(base_conf * 0.5, 4),
                'llm_provider_model': 'local-fallback',
                'sources': [],
                'reasoning': 'Heuristic fallback due to LLM failure',
                'validation_issues': [],
                'guardrail_valid': True
            }]
        # Attach explicit sources references list to each solution (subset already done inside llm_service by ticket_key/summary pair)
        for sol in solutions:
            # Replace generic sources list with display_ref if available
            if sol.get("sources"):
                enriched = []
                for src in sol["sources"]:
                    if isinstance(src, dict) and src.get("key"):
                        enriched.append(src.get("key"))
                    elif isinstance(src, dict) and src.get("summary"):
                        # attempt to map back to combined_for_llm via summary
                        ref = next((c.get("display_ref") for c in combined_for_llm if c.get("summary") == src.get("summary")), src.get("summary"))
                        enriched.append(ref)
                    else:
                        enriched.append(str(src))
                sol["sources"] = enriched
        
        # Escalation flag if any candidate is low confidence
        escalate_flag = any(sol.get('confidence', 0) < 0.2 for sol in solutions)
        return {"solutions": solutions, "ticket_context": data.ticket_bundled_text, "escalate": escalate_flag}

    @activity.defn
    async def post_solution_to_jira_activity(self, ticket_key: str, solution: SynthesizedSolution) -> str:
        """
        Posts the synthesized solution as a comment on the JIRA ticket.
        """
        activity.logger.info(f"Posting solution to JIRA ticket {ticket_key}...")
        try:
            comment = (
                f"Hello,\n\n"
                f"Based on an analysis of similar past issues, here is a suggested resolution for your ticket:\n\n"
                f"---\n"
                f"{solution.solution_text}\n"
                f"---\n\n"
                f"This is an automated suggestion. Please review before executing any steps." + AGENT_SIGNATURE
            )
            self.jira_service.add_comment(ticket_key, comment)
            message = f"Successfully posted solution to JIRA ticket {ticket_key}."
            activity.logger.info(message)
            return message
        except Exception as e:
            error_message = f"Failed to post solution to JIRA ticket {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            return error_message

    @activity.defn
    async def log_resolution_activity(self, ticket_key: str, solution: SynthesizedSolution) -> str:
        """
        Logs the details of the successful resolution to the database.
        """
        activity.logger.info(f"Logging resolution for ticket {ticket_key}...")
        try:
            self.db_service.log_resolution(ticket_key, solution)
            message = f"Successfully logged resolution for ticket {ticket_key}."
            activity.logger.info(message)
            return message
        except Exception as e:
            error_message = f"Failed to log resolution for {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            return error_message

