# File: backend/api/routes.py
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from backend.config import settings
from backend.workflows.shared import TicketValidationInput
# --- FEATURE 1.1.4 ENHANCEMENT ---
from backend.services.db_service import db_service
from .schemas import KnowledgeUploadResponse
import pandas as pd
import io

router = APIRouter(prefix="/api")

# --- FEATURE 1.1.4 ENHANCEMENT ---
# A new endpoint dedicated to ingesting knowledge from uploaded files.
@router.post("/upload-knowledge", response_model=KnowledgeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_knowledge(file: UploadFile = File(...)):
    """
    Allows an admin to upload a CSV or Excel file to update the agent's
    knowledge base of modules and mandatory fields.
    """
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a CSV or XLSX file."
        )

    try:
        content = await file.read()
        
        # Use pandas to read the file content from memory
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
            
        # Standardize column names
        df.columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        # --- PRD Requirement: Validate Headers ---
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
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


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
