# File: backend/worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from backend.config import settings
from backend.workflows.validate_ticket import ValidateTicketWorkflow
from backend.workflows.find_resolution import FindResolutionWorkflow
from backend.workflows.activities import ValidationActivities
from backend.workflows.resolution_activities import ResolutionActivities


async def main():
    print("Connecting to Temporal server...")
    client = await Client.connect(
        f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
        namespace=settings.TEMPORAL_NAMESPACE
    )
    print("Temporal client connected.")

    validation_activities = ValidationActivities()
    resolution_activities = ResolutionActivities()

    worker = Worker(
        client,
        task_queue="lensora-task-queue",
        workflows=[ValidateTicketWorkflow, FindResolutionWorkflow],
        activities=[
            # Validation Activities
            validation_activities.fetch_and_bundle_ticket_context_activity,
            validation_activities.get_llm_verdict_activity,
            validation_activities.comment_and_reassign_activity,
            validation_activities.log_validation_result_activity,
            
            # Resolution Activities
            resolution_activities.find_and_synthesize_solutions_activity,
            # --- FINAL FEATURE ---
            # Register the new notification and logging activities.
            resolution_activities.post_solution_to_jira_activity,
            resolution_activities.log_resolution_activity,
        ],
    )
    print("Temporal worker started. Waiting for tasks...")
    await worker.run()

if __name__ == "__main__":
    print("Starting Temporal worker...")
    asyncio.run(main())

