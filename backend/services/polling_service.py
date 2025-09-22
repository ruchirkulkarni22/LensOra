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
        self.temporal_client: Client | None = None

        # --- SPAM CONTROL ENHANCEMENT (POLLING) ---
        # We construct the JQL query dynamically.
        # It finds tickets updated recently BUT excludes tickets where the
        # last update was performed by our agent's own user account.
        # This prevents the poller from getting into a loop.
        base_jql = f'project = LENS AND updated >= "-{self.interval_minutes}m"'
        if settings.JIRA_AGENT_USER_ACCOUNT_ID:
            agent_id = settings.JIRA_AGENT_USER_ACCOUNT_ID
            self.jql_query = f'{base_jql} AND updatedBy != "{agent_id}"'
        else:
            self.jql_query = base_jql
            print("WARNING: JIRA_AGENT_USER_ACCOUNT_ID is not set. Polling loop protection is disabled.")


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
        print(f"   Using JQL Query: {self.jql_query}")
        
        # We will use a shorter interval for the very first poll on startup.
        # This makes testing faster.
        is_first_run = True

        while True:
            if is_first_run:
                await asyncio.sleep(10) # Wait 10 seconds on first run
                is_first_run = False
            else:
                await asyncio.sleep(self.interval_minutes * 60)

            print(f"\n--- Polling JIRA for updates ({self.interval_minutes} min interval) ---")
            try:
                # Local import to avoid circular dependency issues on startup
                from .jira_client import jira_service 
                await self._ensure_client_connected()

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
