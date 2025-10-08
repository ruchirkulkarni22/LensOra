# File: backend/api/routes.py
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Request, Body, Path
# StreamingResponse no longer required after removing live log SSE endpoints
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from backend.config import settings
from backend.workflows.shared import TicketValidationInput, ResolutionInput
from backend.services.db_service import db_service
from .schemas import (
    KnowledgeUploadResponse, 
    JiraWebhookPayload, 
    SolvedTicketsUploadResponse,
    SolutionApproval
)
from backend.services.polling_service import polling_service
from backend.services.rag_service import rag_service
import pandas as pd
import io
import asyncio
from typing import List, Dict, Optional
from sqlalchemy import select  # Added for /validation-stats endpoint
import time

# Session-level caches / guards
_GEN_RATE_LIMIT_SECONDS = 25
_last_generation: dict[str, float] = {}
_inflight: set[str] = set()
_session_solution_cache: dict[str, Dict] = {}
_active_sessions: dict[str, Dict] = {}

 # (previous in-memory guard vars replaced above)


router = APIRouter(prefix="/api")

@router.get("/health", status_code=200)
async def health(warm: Optional[bool] = False):
    db_ok = True
    temporal_ok = True
    model_loaded = False
    external_ok = True  # Placeholder; could add a lightweight ping later
    retrieval_mode = False
    try:
        db_service.count_incomplete()
    except Exception:
        db_ok = False
    try:
        # shallow Temporal connect attempt (timeout kept short implicitly)
        client = await Client.connect(settings.TEMPORAL_ADDRESS, namespace=settings.TEMPORAL_NAMESPACE)
        await client.close()
    except Exception:
        temporal_ok = False
    # embedding model warm check
    try:
        from backend.services.rag_service import rag_service as _rag
        if warm and _rag.embedding_model is None:
            _rag._ensure_model()
        model_loaded = _rag.embedding_model is not None
    except Exception:
        model_loaded = False
    if not model_loaded:
        retrieval_mode = True
    return {
        "status": "ok" if all([db_ok, temporal_ok]) else "degraded",
        "db_ok": db_ok,
        "temporal_ok": temporal_ok,
        "embedding_model_loaded": model_loaded,
        "external_search_ok": external_ok,
        "retrieval_only_mode": retrieval_mode
    }

@router.get("/validation-stats", status_code=status.HTTP_200_OK)
async def get_validation_stats():
    """Diagnostic endpoint: returns counts of validation statuses to help debug empty dashboards."""
    from sqlalchemy import func
    from backend.db.models import ValidationsLog
    try:
        db = db_service.SessionLocal()
        rows = db.execute(
            select(ValidationsLog.status, func.count(ValidationsLog.id)).group_by(ValidationsLog.status)
        ).all()
        stats = {status: count for status, count in rows}
        return {"status_counts": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {e}")
    finally:
        try:
            db.close()
        except Exception:
            pass

## Live log endpoints removed per new requirements



@router.post("/jira-webhook", status_code=status.HTTP_200_OK)
async def handle_jira_webhook(payload: JiraWebhookPayload, request: Request):
    """
    Listens for issue_created and issue_updated events from JIRA
    and triggers the validation workflow.
    """
    # This logic remains unchanged
    # ... (existing code)
    print(f"Received JIRA webhook for event: {payload.webhook_event}")
    if payload.webhook_event in ["jira:issue_created", "jira:issue_updated"]:
        ticket_key = payload.issue.key
        print(f"Webhook triggered for ticket: {ticket_key}. Starting validation workflow.")
        try:
            client = await Client.connect(
                settings.TEMPORAL_ADDRESS,
                namespace=settings.TEMPORAL_NAMESPACE,
            )
            workflow_input = TicketValidationInput(ticket_key=ticket_key)
            await client.start_workflow(
                "ValidateTicketWorkflow",
                workflow_input,
                id=f"validate-ticket-{ticket_key}",
                task_queue="assistiq-task-queue",
                id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            )
        except Exception as e:
            print(f"❌ Webhook failed to trigger workflow for {ticket_key}. Error: {e}")
    return {"status": "received"}


@router.post("/upload-solved-tickets", response_model=SolvedTicketsUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_solved_tickets(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a CSV or XLSX file."
        )
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content)) if file.filename.endswith('.csv') else pd.read_excel(io.BytesIO(content))
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        required_columns = {'ticket_key', 'summary', 'resolution'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"File is missing one of the required columns: {required_columns}")

        result = rag_service.upsert_solved_tickets(df)
        
        if result["errors"]:
            raise ValueError(f"Errors occurred during processing: {'; '.join(result['errors'])}")

        return SolvedTicketsUploadResponse(
            filename=file.filename,
            status="success",
            message="Solved tickets knowledge base updated successfully.",
            rows_processed=len(df),
            rows_upserted=result["rows_upserted"]
        )
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/upload-knowledge", response_model=KnowledgeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge(file: UploadFile = File(...)):
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file format.")
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content)) if file.filename.endswith('.csv') else pd.read_excel(io.BytesIO(content))
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        required_columns = {'module_name', 'field_name'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"File is missing one of the required columns: {required_columns}")
        result = db_service.upsert_knowledge_from_dataframe(df)
        if result["errors"]:
            raise ValueError(f"Errors occurred during processing: {'; '.join(result['errors'])}")
        return KnowledgeUploadResponse(
            filename=file.filename,
            status="success",
            message="Knowledge base updated successfully.",
            rows_processed=len(df),
            rows_upserted=result["rows_upserted"]
        )
    except ValueError as e:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/trigger-validation/{ticket_key}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_validation(ticket_key: str):
    try:
        client = await Client.connect(
            settings.TEMPORAL_ADDRESS,
            namespace=settings.TEMPORAL_NAMESPACE,
        )
        workflow_input = TicketValidationInput(ticket_key=ticket_key)
        await client.start_workflow(
            "ValidateTicketWorkflow",
            workflow_input,
            id=f"validate-ticket-{ticket_key}",
            task_queue="assistiq-task-queue",
            id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        return {
            "status": "success",
            "message": f"Workflow 'validate-ticket-{ticket_key}' started successfully.",
            "workflow_id": f"validate-ticket-{ticket_key}"
        }
    except Exception as e:
        print(f"ERROR starting workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}",
        )

# --- ADMIN UI ENDPOINTS ---

@router.get("/complete-tickets", status_code=status.HTTP_200_OK)
async def get_complete_tickets():
    try:
        complete_tickets = db_service.get_complete_tickets()
        return {"tickets": complete_tickets}
    except Exception as e:
        print(f"ERROR getting complete tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get complete tickets: {str(e)}",
        )

# --- NEW: Endpoint to fetch incomplete tickets ---
@router.get("/incomplete-tickets", status_code=status.HTTP_200_OK)
async def get_incomplete_tickets():
    """
    API endpoint for the Admin UI to retrieve all tickets that have been validated as 'incomplete'.
    """
    try:
        incomplete_tickets = db_service.get_incomplete_tickets()
        # Calculate the next poll time based on the polling service's interval
        from backend.services.polling_service import polling_service
        next_poll_time = None
        try:
            # Get the current time plus the interval in milliseconds
            import time
            from datetime import datetime, timedelta
            
            # Using the adaptive interval logic from polling_service
            incomplete_count = db_service.count_incomplete()
            base = polling_service.interval_minutes * 60  # in seconds
            adaptive_min = 60  # 1 minute
            adaptive_max = 600  # 10 minutes ceiling
            
            if incomplete_count == 0:
                interval = base
            elif incomplete_count < 5:
                interval = max(base * 0.6, adaptive_min)
            elif incomplete_count < 15:
                interval = max(base * 0.4, adaptive_min)
            else:
                interval = adaptive_min
                
            interval = min(interval, adaptive_max)
            
            # Calculate next poll time (current time + interval)
            next_poll_time = int(time.time() * 1000) + int(interval * 1000)  # in milliseconds
        except Exception as e:
            print(f"Error calculating next poll time: {e}")
            # Default fallback if calculation fails
            next_poll_time = int(time.time() * 1000) + (polling_service.interval_minutes * 60 * 1000)
            
        return {"tickets": incomplete_tickets, "next_poll_time": next_poll_time}
    except Exception as e:
        print(f"ERROR getting incomplete tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get incomplete tickets: {str(e)}",
        )

@router.post("/generate-solutions/{ticket_key}", status_code=status.HTTP_202_ACCEPTED)
async def generate_solutions(ticket_key: str):
    try:
        # Rate limiting / single-flight
        now = time.time()
        last = _last_generation.get(ticket_key)
        if last and (now - last) < _GEN_RATE_LIMIT_SECONDS:
            retry_in = int(_GEN_RATE_LIMIT_SECONDS - (now - last))
            raise HTTPException(status_code=429, detail=f"Solution generation for {ticket_key} recently requested. Retry in {retry_in}s.")
        if ticket_key in _inflight:
            raise HTTPException(status_code=409, detail=f"Solution generation already in progress for {ticket_key}.")
        _inflight.add(ticket_key)
        _last_generation[ticket_key] = now
        _active_sessions[ticket_key] = {"started": now}

        from backend.services.jira_client import jira_service
        from backend.services.compliance_filter import scrub as compliance_scrub

        details = jira_service.get_ticket_details(ticket_key)
        # Duplicate short-circuit pre-check (if already validated & has duplicate_of)
        validation_record = db_service.get_validation_record(ticket_key)
        if validation_record and validation_record.get('duplicate_of'):
            solved = db_service.get_solved_ticket(validation_record['duplicate_of'])
            preview = None
            if solved:
                preview = (solved['resolution'] or '')[:600]
            dup_payload = {
                "status": "duplicate",
                "ticket_key": ticket_key,
                "duplicate_of": validation_record['duplicate_of'],
                "resolution_preview": preview
            }
            _session_solution_cache[ticket_key] = dup_payload
            db_service.add_event(ticket_key, 'duplicate_short_circuit', f"Duplicate of {validation_record['duplicate_of']}")
            return dup_payload
        text_parts = [
            f"Ticket Key: {ticket_key}",
            f"Summary: {details.get('summary', '')}",
            f"Description: {details.get('description', '')}"
        ]
        bundled_text = "\n".join(text_parts)

        client = await Client.connect(
            settings.TEMPORAL_ADDRESS,
            namespace=settings.TEMPORAL_NAMESPACE,
        )

        # Vague / low-info heuristic
        if len(bundled_text) < 120:
            follow_up = [
                "What environment (Prod/Test) is affected?",
                "Exact error message or code?",
                "Recent change before issue started?",
                "How many users or transactions impacted?"
            ]
            redacted, _ = compliance_scrub(bundled_text)
            payload = {"status": "needs_more_info", "ticket_key": ticket_key, "ticket_context": redacted, "follow_up_questions": follow_up}
            _session_solution_cache[ticket_key] = payload
            return payload

        resolution_input = ResolutionInput(ticket_key=ticket_key, ticket_bundled_text=bundled_text)
        handle = await client.start_workflow(
            "FindResolutionWorkflow",
            resolution_input,
            id=f"find-resolution-{ticket_key}",
            task_queue="assistiq-task-queue",
            id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        result = await handle.result()
        # Enrich solutions (confidence explanation + guardrail summary, strip model names)
        enriched = []
        for sol in result["solutions"]:
            issues = sol.get("validation_issues", [])
            guardrail_summary = None
            if issues:
                guardrail_summary = {
                    "issue_count": len(issues),
                    "unsafe_removed": sum(1 for i in issues if 'unsafe' in str(i).lower()),
                    "citation_issues": sum(1 for i in issues if 'citation' in str(i).lower())
                }
            confidence = sol.get("confidence")
            explanation_parts = []
            if confidence is not None:
                explanation_parts.append(f"score={confidence}")
            if guardrail_summary:
                explanation_parts.append(f"guardrail_issues={guardrail_summary['issue_count']}")
            confidence_explanation = "; ".join(explanation_parts) if explanation_parts else None
            enriched.append({
                "solution_text": sol.get("solution_text"),
                "confidence": confidence,
                "sources": sol.get("sources", []),
                "confidence_explanation": confidence_explanation,
                "guardrail_summary": guardrail_summary,
                "reasoning": sol.get("reasoning")
            })
        payload = {"status": "success", "ticket_key": ticket_key, "solutions": enriched, "ticket_context": result["ticket_context"], "escalate": result.get("escalate", False)}
        _session_solution_cache[ticket_key] = payload
        db_service.add_event(ticket_key, 'solutions_generated', f"solutions={len(enriched)} escalate={payload['escalate']}")
        return payload
    except Exception as e:
        # --- Enhanced diagnostics & fallback path ---
        print(f"ERROR generating solutions via Temporal workflow for {ticket_key}: {e}")
        temporal_error = str(e)
        # Attempt direct (synchronous) fallback execution of the activity logic to avoid a hard 500.
        try:
            from backend.workflows.shared import ResolutionInput
            from backend.workflows.resolution_activities import ResolutionActivities
            from jira import JIRAError
            resolution_input = ResolutionInput(ticket_key=ticket_key, ticket_bundled_text=bundled_text if 'bundled_text' in locals() else ticket_key)

            activities = ResolutionActivities()
            fallback_result = await activities.find_and_synthesize_solutions_activity(resolution_input)
            print(f"Fallback (direct activity) succeeded for {ticket_key} after Temporal failure.")
            fallback_solutions = []
            for sol in fallback_result.get("solutions", []):
                fallback_solutions.append({
                    "solution_text": sol.get("solution_text"),
                    "confidence": sol.get("confidence"),
                    "sources": sol.get("sources", []),
                    "confidence_explanation": None,
                    "guardrail_summary": None,
                    "reasoning": sol.get("reasoning")
                })
            payload = {"status": "success_fallback","ticket_key": ticket_key,"solutions": fallback_solutions,"ticket_context": fallback_result.get("ticket_context"),"note": "Returned via direct activity fallback (Temporal workflow failed)","temporal_error": temporal_error, "escalate": fallback_result.get("escalate", False)}
            _session_solution_cache[ticket_key] = payload
            return payload
        except ValueError as ve:
            # Likely configuration issue (e.g., JIRA creds or missing LLM API key during client init)
            print(f"CONFIG ERROR during fallback generation for {ticket_key}: {ve}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Configuration error generating solutions (check env vars / API keys): {ve} | Original: {temporal_error}",
            )
        except JIRAError as je:  # type: ignore
            print(f"JIRA ERROR during fallback generation for {ticket_key}: {je}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"JIRA access issue while generating solutions: {je.text if hasattr(je, 'text') else je}",
            )
        except Exception as fe:
            print(f"FALLBACK FAILURE for {ticket_key}: {fe}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate solutions (workflow + fallback both failed): {fe} | Original: {temporal_error}",
            )
    finally:
        _inflight.discard(ticket_key)
        _active_sessions.pop(ticket_key, None)

@router.get("/solutions-cache/{ticket_key}", status_code=200)
async def get_cached_solutions(ticket_key: str):
    data = _session_solution_cache.get(ticket_key)
    if not data:
        raise HTTPException(status_code=404, detail="No cached solutions for ticket")
    return data

@router.post("/save-draft/{ticket_key}", status_code=201)
async def save_draft(ticket_key: str, body: Dict):
    from backend.services.db_service import db_service as _db
    txt = body.get('draft_text')
    if not txt:
        raise HTTPException(status_code=400, detail="draft_text required")
    saved = _db.save_draft(ticket_key, txt, author=body.get('author'))
    db_service.add_event(ticket_key, 'draft_saved', 'Draft created')
    return {"status": "saved", "draft": saved}

@router.get("/drafts/{ticket_key}", status_code=200)
async def list_drafts(ticket_key: str):
    from backend.services.db_service import db_service as _db
    drafts = _db.list_drafts(ticket_key)
    return {"drafts": drafts}
        
@router.post("/post-solution/{ticket_key}", status_code=status.HTTP_202_ACCEPTED)
async def post_solution(ticket_key: str = Path(...), solution: SolutionApproval = Body(...)):
    try:
        client = await Client.connect(
            settings.TEMPORAL_ADDRESS,
            namespace=settings.TEMPORAL_NAMESPACE,
        )
        
        solution_dict = solution.model_dump()
        
        await client.start_workflow(
            "PostResolutionWorkflow",
            args=[ticket_key, solution_dict],
            id=f"post-resolution-{ticket_key}",
            task_queue="assistiq-task-queue",
            id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
        )
        
        db_service.add_event(ticket_key, 'solution_posted', 'Solution workflow initiated')
        return {
            "status": "success",
            "message": f"Solution posted to JIRA ticket {ticket_key} successfully.",
            "workflow_id": f"post-resolution-{ticket_key}"
        }
    except Exception as e:
        print(f"ERROR posting solution via Temporal workflow: {e}")
        temporal_error = str(e)
        # Fallback: directly execute the two activities synchronously if Temporal is unavailable
        try:
            from backend.workflows.resolution_activities import ResolutionActivities
            from backend.workflows.shared import SynthesizedSolution
            activities = ResolutionActivities()
            synthesized = SynthesizedSolution(
                solution_text=solution.solution_text,
                llm_provider_model=solution.llm_provider_model or "human-approved"
            )
            # Post to JIRA directly
            await activities.post_solution_to_jira_activity(ticket_key, synthesized)
            # Log resolution directly
            await activities.log_resolution_activity(ticket_key, synthesized)
            db_service.add_event(ticket_key, 'solution_posted_direct', 'Posted without workflow')
            return {
                "status": "success_fallback",
                "message": f"Solution posted directly without Temporal for ticket {ticket_key}",
                "temporal_error": temporal_error
            }
        except Exception as fe:
            print(f"FALLBACK post solution failed: {fe}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to post solution (workflow + fallback failed): {fe} | Original: {temporal_error}",
            )

@router.get("/solutions-active", status_code=200)
async def list_active_solution_generations():
    return {"active": [{"ticket_key": k, **v} for k, v in _active_sessions.items()]}

@router.get("/impact-counters", status_code=200)
async def impact_counters():
    return db_service.get_impact_counters()

@router.get("/timeline/{ticket_key}", status_code=200)
async def ticket_timeline(ticket_key: str):
    return {"ticket_key": ticket_key, "timeline": db_service.get_timeline(ticket_key)}

