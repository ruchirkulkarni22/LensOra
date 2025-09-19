# File: backend/api/routes.py
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Request
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from backend.config import settings
from backend.workflows.shared import TicketValidationInput
from backend.services.db_service import db_service
from .schemas import KnowledgeUploadResponse, JiraWebhookPayload, SolvedTicketsUploadResponse
from backend.services.polling_service import polling_service
# --- FEATURE 2.2 ENHANCEMENT ---
from backend.services.rag_service import rag_service
import pandas as pd
import io

router = APIRouter(prefix="/api")

@router.post("/jira-webhook", status_code=status.HTTP_200_OK)
async def handle_jira_webhook(payload: JiraWebhookPayload, request: Request):
    """
    Listens for issue_created and issue_updated events from JIRA
    and triggers the validation workflow.
    """
    print(f"Received JIRA webhook for event: {payload.webhook_event}")
    if payload.webhook_event in ["jira:issue_created", "jira:issue_updated"]:
        ticket_key = payload.issue.key
        print(f"Webhook triggered for ticket: {ticket_key}. Starting validation workflow.")
        try:
            client = await Client.connect(
                f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
                namespace=settings.TEMPORAL_NAMESPACE
            )
            workflow_input = TicketValidationInput(ticket_key=ticket_key)
            await client.start_workflow(
                "ValidateTicketWorkflow",
                workflow_input,
                id=f"validate-ticket-{ticket_key}",
                task_queue="lensora-task-queue",
                id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            )
        except Exception as e:
            print(f"❌ Webhook failed to trigger workflow for {ticket_key}. Error: {e}")
    return {"status": "received"}


# --- FEATURE 2.2 ENHANCEMENT ---
# New endpoint to upload the internal knowledge base of solved tickets.
@router.post("/upload-solved-tickets", response_model=SolvedTicketsUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_solved_tickets(file: UploadFile = File(...)):
    """
    Allows an admin to upload a CSV/Excel file containing previously solved
    JIRA tickets to be used as an internal knowledge base.
    """
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
    """
    Allows an admin to upload a CSV or Excel file to update the agent's
    knowledge base of modules and mandatory fields.
    """
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file format.")
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content)) if file.filename.endswith('.csv') else pd.read_excel(io.BytesIO(content))
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        required_columns = {'module_name', 'field_name'}
        if not required_columns.issubset(df.columns):
            raise ValueError(f"File is missing one of the required columns: {required_columns}")
        result = db_service.upsert_module_knowledge(df)
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
    """
    API endpoint to manually trigger the ticket validation workflow.
    """
    try:
        client = await Client.connect(
            f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
            namespace=settings.TEMPORAL_NAMESPACE,
        )
        workflow_input = TicketValidationInput(ticket_key=ticket_key)
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

