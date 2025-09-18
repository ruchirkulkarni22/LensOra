# File: backend/api/routes.py
from fastapi import APIRouter, HTTPException, status
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from backend.config import settings
from backend.workflows.shared import TicketValidationInput

router = APIRouter(prefix="/api")

@router.post("/trigger-validation/{ticket_key}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_validation(ticket_key: str):
    """
    API endpoint to trigger the ticket validation workflow.
    """
    try:
        client = await Client.connect(
            f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
            namespace=settings.TEMPORAL_NAMESPACE,
        )

        workflow_input = TicketValidationInput(ticket_key=ticket_key)
        
        # --- FLAWLESS FIX ---
        # We now add an "ID Reuse Policy".
        # TERMINATE_IF_RUNNING tells Temporal: If a workflow with this ID
        # is already active, kill it and start this new one. This makes our
        # API endpoint re-runnable and robust.
        await client.start_workflow(
            "ValidateTicketWorkflow",
            workflow_input,
            id=f"validate-ticket-{ticket_key}",
            task_queue="lensora-task-queue",
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

