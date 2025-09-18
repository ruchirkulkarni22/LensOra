# File: backend/worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from backend.config import settings
from backend.workflows.validate_ticket import ValidateTicketWorkflow

# Import the correct class name from activities
from backend.workflows.activities import ValidationActivities


async def main():
    print("Connecting to Temporal server...")
    client = await Client.connect(
        f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
        namespace=settings.TEMPORAL_NAMESPACE
    )
    print("Temporal client connected.")

    # Instantiate the ValidationActivities class.
    # The service imports happen here, safely outside the workflow sandbox.
    activities_instance = ValidationActivities()

    worker = Worker(
        client,
        task_queue="lensora-task-queue",
        workflows=[ValidateTicketWorkflow],
        # Pass the methods from the instantiated class to the worker.
        activities=[
            activities_instance.fetch_and_bundle_ticket_text_activity,
            activities_instance.get_llm_verdict_activity,
            activities_instance.comment_and_reassign_activity,
        ],
    )
    print("Temporal worker started. Waiting for tasks...")
    await worker.run()

if __name__ == "__main__":
    print("Starting Temporal worker...")
    asyncio.run(main())
