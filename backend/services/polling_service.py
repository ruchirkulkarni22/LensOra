# File: backend/services/polling_service.py
import asyncio
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from backend.config import settings
from backend.workflows.shared import TicketValidationInput
from typing import List, Dict, Set

class PollingService:
    def __init__(self):
        self.interval_minutes = 5
        self.temporal_client: Client | None = None
        
        # We'll use a simple query to get all tickets in the LENS project
        # and then filter them based on our database records
        self.jql_query = 'project = LENS'
        
        print(f"INFO: Polling service will use query '{self.jql_query}' and then filter tickets based on database status")

    async def _ensure_client_connected(self):
        """
        Ensures the Temporal client is connected, with retry logic for resilience.
        This helps recover from system sleep or network issues.
        """
        # If client is None, we need to create a new connection
        if self.temporal_client is None:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    print(f"Connecting to Temporal (attempt {retry_count + 1}/{max_retries})...")
                    self.temporal_client = await Client.connect(
                        f"{settings.TEMPORAL_HOST}:{settings.TEMPORAL_PORT}",
                        namespace=settings.TEMPORAL_NAMESPACE
                        # The connection_timeout parameter is not supported
                    )
                    print("✅ Temporal client connected for polling.")
                    return
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        print(f"❌ Failed to connect to Temporal after {max_retries} attempts: {e}")
                        raise
                    wait_time = 3 * retry_count
                    print(f"Connection error: {e}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

    async def start_polling(self):
        print(f"✅ Starting JIRA polling service. Will poll every {self.interval_minutes} minutes.")
        print(f"   Using stateful polling with JIRA query: {self.jql_query}")
        
        await asyncio.sleep(10) # Give a few seconds for other services to start up
        
        while True:
            print(f"--- Polling JIRA for ticket updates ({self.interval_minutes} min interval) ---")
            try:
                # Local imports to avoid potential circular dependency issues on startup
                from .jira_client import jira_service 
                from .db_service import db_service    
                
                await self._ensure_client_connected()

                # 1. Get ALL tickets from the LENS project with retry logic
                max_retries = 3
                retry_count = 0
                all_jira_tickets = None
                
                while retry_count < max_retries:
                    try:
                        print(f"Fetching JIRA tickets (attempt {retry_count + 1}/{max_retries})...")
                        all_jira_tickets = jira_service.client.search_issues(self.jql_query)
                        print(f"Successfully fetched tickets from JIRA")
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count >= max_retries:
                            raise  # Re-raise if we've exhausted retries
                        wait_time = 5 * retry_count  # Progressive backoff
                        print(f"JIRA API error: {e}. Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                
                if not all_jira_tickets:
                    print("No tickets found in the LENS project.")
                    await asyncio.sleep(self.interval_minutes * 60)
                    continue

                ticket_keys = [issue.key for issue in all_jira_tickets]
                print(f"Found {len(ticket_keys)} ticket(s) in JIRA: {ticket_keys}")

                # 2. Get their last known status from our database (the agent's memory)
                known_statuses = db_service.get_last_known_ticket_statuses(ticket_keys)
                print(f"Known statuses from validation database: {known_statuses}")

                # 3. Identify tickets that need validation according to our plan:
                new_tickets = []          # Never seen before by our system
                incomplete_tickets = []    # Previously marked as incomplete
                complete_tickets = []      # Already processed and complete
                
                for ticket_key in ticket_keys:
                    last_status = known_statuses.get(ticket_key)

                    if last_status == "complete":
                        # Skip tickets that are already processed successfully
                        complete_tickets.append(ticket_key)
                    elif last_status == "incomplete":
                        # Check if the ticket has been updated since our last check
                        # We'll need to get the last updated timestamp from JIRA
                        try:
                            issue = jira_service.client.issue(ticket_key)
                            last_updated = issue.fields.updated
                            last_validated = db_service.get_last_validation_timestamp(ticket_key)
                            
                            if last_validated and last_updated > last_validated:
                                # Ticket was updated after our last validation, revalidate
                                print(f"Ticket {ticket_key} was updated since last validation. Revalidating.")
                                incomplete_tickets.append(ticket_key)
                            else:
                                # Ticket hasn't been updated, skip revalidation
                                print(f"Ticket {ticket_key} hasn't been updated since last validation. Skipping.")
                        except Exception as e:
                            print(f"Error checking update status for {ticket_key}: {e}")
                            # On error, we'll revalidate to be safe
                            incomplete_tickets.append(ticket_key)
                    else:
                        # This means last_status is None (it's a new ticket)
                        new_tickets.append(ticket_key)
                
                # 4. Log the categorization for debugging
                print(f"Ticket categorization:")
                print(f"  - New tickets: {new_tickets}")
                print(f"  - Previously incomplete tickets: {incomplete_tickets}")
                print(f"  - Already complete tickets: {complete_tickets}")
                
                # 5. Process tickets that need validation (new or incomplete)
                tickets_to_process = new_tickets + incomplete_tickets
                
                if tickets_to_process:
                    print(f"Processing {len(tickets_to_process)} ticket(s) that require validation: {tickets_to_process}")
                    for ticket_key in tickets_to_process:
                        print(f"  -> Starting validation for {ticket_key}...")
                        await self.trigger_workflow(ticket_key)
                else:
                    print("No tickets require validation at this time.")
                
                # 6. Summary
                print(f"Polling cycle complete. New: {len(new_tickets)}, Revalidating: {len(incomplete_tickets)}, Skipped: {len(complete_tickets)}")

            except Exception as e:
                print(f"❌ Error during JIRA polling: {e}")
                
                # If this is a connection error, it might be due to system sleep
                if "ConnectionError" in str(e) or "timeout" in str(e).lower():
                    # Reset the temporal client to force reconnection on next loop
                    self.temporal_client = None
                    print("Network error detected. Will attempt to reconnect on next polling cycle.")
                    # Use shorter wait time to recover faster
                    await asyncio.sleep(60)  # Wait 1 minute instead of full interval
                    continue
            
            # Calculate next poll time and log it
            next_poll_time = self.interval_minutes * 60
            print(f"Next polling cycle will begin in {self.interval_minutes} minutes")
            await asyncio.sleep(next_poll_time)


    async def trigger_workflow(self, ticket_key: str):
        """
        Triggers the ValidateTicketWorkflow for a specific ticket key.
        
        This starts the validation process which will determine if the ticket
        has all required information. The result will be stored in the validations_log
        table with a status of either "complete" or "incomplete".
        
        For tickets that come back as "complete", they will be ready for the 
        Resolution Agent (UI) to process them.
        For tickets that come back as "incomplete", they will be commented on 
        and reassigned in JIRA, and will be reprocessed when updated.
        """
        try:
            workflow_input = TicketValidationInput(ticket_key=ticket_key)
            
            # Use the TERMINATE_IF_RUNNING policy to ensure we don't have duplicate workflows
            # This is important if a ticket is being rapidly updated in quick succession
            await self.temporal_client.start_workflow(
                "ValidateTicketWorkflow",
                workflow_input,
                id=f"validate-ticket-{ticket_key}",
                task_queue="lensora-task-queue",
                id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            )
            print(f"     ✅ Workflow triggered for {ticket_key}. The workflow will:")
            print(f"        - Validate if the ticket has complete information")
            print(f"        - Update the validations_log table with status (complete/incomplete)")
            print(f"        - For 'incomplete' tickets: comment and reassign in JIRA")
            print(f"        - For 'complete' tickets: make them available for the Resolution UI")
        except Exception as e:
            print(f"     ❌ Failed to trigger workflow for {ticket_key}. Error: {e}")

# Singleton instance
polling_service = PollingService()

