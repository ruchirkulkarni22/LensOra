# File: backend/workflows/resolution_activities.py
from temporalio import activity
from backend.workflows.shared import ResolutionInput, SynthesizedSolution
from typing import List, Dict

@activity.defn
class ResolutionActivities:
    def __init__(self):
        from backend.services.rag_service import rag_service
        from backend.services.llm_service import llm_service
        self.rag_service = rag_service
        self.llm_service = llm_service

    @activity.defn
    async def find_and_synthesize_solutions_activity(self, data: ResolutionInput) -> SynthesizedSolution:
        """
        This is the core activity of the Resolution Agent.
        1. Finds similar tickets from the internal knowledge base.
        2. Uses an LLM to synthesize the findings into a new solution.
        """
        activity.logger.info(f"Resolution: Finding similar solutions for ticket {data.ticket_key}...")
        
        # --- FLAWLESS FIX ---
        # We now use the 'ticket_bundled_text' directly from the serializable input object.
        similar_tickets = self.rag_service.find_similar_solutions(
            query_text=data.ticket_bundled_text,
            top_k=3
        )

        if not similar_tickets:
            activity.logger.warning(f"No similar tickets found for {data.ticket_key}.")
            return SynthesizedSolution(solution_text="I could not find any similar past issues in our knowledge base. This may be a new type of issue that requires manual investigation.")

        activity.logger.info(f"Found {len(similar_tickets)} similar tickets. Synthesizing solution...")
        
        # We also pass the 'ticket_bundled_text' to the synthesis prompt.
        synthesized_text = self.llm_service.synthesize_solutions(
            ticket_context=data.ticket_bundled_text,
            ranked_solutions=similar_tickets
        )
        
        activity.logger.info(f"Successfully synthesized solution for {data.ticket_key}.")
        print("--- Synthesized Solution ---")
        print(synthesized_text)
        print("----------------------------")

        return SynthesizedSolution(solution_text=synthesized_text)

