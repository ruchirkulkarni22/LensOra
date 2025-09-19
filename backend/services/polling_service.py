# File: backend/services/polling_service.py
import asyncio
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from backend.config import settings
from backend.workflows.shared import TicketValidationInput

class PollingService:
    """
    A service that periodically polls JIRA for updated tickets and triggers
    the validation workflow. This acts as a fallback for webhooks.
    """
    def __init__(self):
        self.interval_minutes = 5
        # JQL to find issues updated in the last X minutes, not yet validated by us.
        self.jql_query = f'project = LENS AND updated >= "-{self.interval_minutes}m"'
        self.temporal_client: Client | None = None

    async def _ensure_client_connected(self):
        """Connects to Temporal if not already connected."""
        if self.temporal_client is None or not self.temporal_client.is_connected:
            print("Connecting to Temporal for polling service...")
            self.temporal_client = await Client.connect(
                f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
                namespace=settings.TEMPORAL_NAMESPACE
            )
            print("Temporal client connected for polling.")

    async def start_polling(self):
        """The main loop that runs forever, polling at a set interval."""
        print(f"✅ Starting JIRA polling service. Will poll every {self.interval_minutes} minutes.")
        while True:
            await asyncio.sleep(self.interval_minutes * 60)
            print(f"⏰ Polling JIRA for tickets updated in the last {self.interval_minutes} minutes...")
            try:
                from .jira_client import jira_service # Local import to avoid circular dependency
                await self._ensure_client_connected()

                # Search for issues using the JQL query
                issues = jira_service.client.search_issues(self.jql_query)
                
                if not issues:
                    print("No recently updated tickets found.")
                    continue

                print(f"Found {len(issues)} recently updated ticket(s). Triggering validation...")
                for issue in issues:
                    await self.trigger_workflow(issue.key)

            except Exception as e:
                print(f"❌ Error during JIRA polling: {e}")

    async def trigger_workflow(self, ticket_key: str):
        """Triggers the validation workflow for a given ticket key."""
        try:
            workflow_input = TicketValidationInput(ticket_key=ticket_key)
            await self.temporal_client.start_workflow(
                "ValidateTicketWorkflow",
                workflow_input,
                id=f"validate-ticket-{ticket_key}",
                task_queue="lensora-task-queue",
                id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            )
            print(f"   -> Workflow triggered for {ticket_key} via polling.")
        except Exception as e:
            print(f"❌ Failed to trigger workflow for {ticket_key} via polling. Error: {e}")

polling_service = PollingService()
