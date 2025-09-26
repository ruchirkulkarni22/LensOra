# File: backend/services/polling_service.py
import asyncio
import os
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from backend.config import settings
from backend.workflows.shared import TicketValidationInput
from typing import List, Dict
from collections import deque
from datetime import datetime

class PollingService:
    def __init__(self):
        self.interval_minutes = 5
        self.temporal_client: Client | None = None
        self.jql_query = 'project = LENS'
        self.log_deque: deque = None
        
        # Initial message to confirm service is ready
        self._initial_log(f"Polling service initialized. Query: '{self.jql_query}'")

    def _initial_log(self, message: str):
         # This is a simple print for the initial setup before the deque is passed
         print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def _log(self, message: str):
        """Logs a message to both the console and the shared deque for SSE."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        if self.log_deque is not None:
            self.log_deque.append(log_entry)

    async def _ensure_client_connected(self):
        if self.temporal_client is None:
            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    self._log(f"Connecting to Temporal (attempt {retry_count + 1}/{max_retries})...")
                    # Use localhost when running locally and not inside Docker
                    host = settings.TEMPORAL_HOST
                    if host == "temporal" and os.environ.get("DOCKER_ENV") != "true":
                        host = "localhost"
                    self._log(f"Connecting to Temporal at {host}:{settings.TEMPORAL_PORT}")
                    self.temporal_client = await Client.connect(
                        f"{host}:{settings.TEMPORAL_PORT}",
                        namespace=settings.TEMPORAL_NAMESPACE
                    )
                    self._log("✅ Temporal client connected for polling.")
                    return
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self._log(f"❌ Failed to connect to Temporal after {max_retries} attempts: {e}")
                        raise
                    wait_time = 3 * retry_count
                    self._log(f"Connection error: {e}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

    async def start_polling(self, log_deque: deque):
        """Main polling loop."""
        self.log_deque = log_deque
        self._log(f"✅ Starting JIRA polling service. Interval: {self.interval_minutes} minutes.")
        
        while True:
            self._log(f"--- Polling JIRA for ticket updates ---")
            try:
                from .jira_client import jira_service 
                from .db_service import db_service    
                
                await self._ensure_client_connected()

                all_jira_tickets = None
                try:
                    self._log("Fetching all tickets from JIRA...")
                    all_jira_tickets = jira_service.client.search_issues(self.jql_query, maxResults=50) 
                    self._log(f"✅ Successfully fetched {len(all_jira_tickets)} tickets from JIRA.")
                except Exception as e:
                    self._log(f"❌ JIRA API error: {e}. Skipping this cycle.")
                    await asyncio.sleep(60)
                    continue

                if not all_jira_tickets:
                    self._log("No tickets found in the JIRA project.")
                    await asyncio.sleep(self.interval_minutes * 60)
                    continue

                ticket_keys = [issue.key for issue in all_jira_tickets]
                self._log(f"Found {len(ticket_keys)} ticket(s): {', '.join(ticket_keys[:5])}...")

                known_statuses = db_service.get_last_known_ticket_statuses(ticket_keys)
                
                new_tickets = []
                incomplete_tickets_to_revalidate = []
                
                for issue in all_jira_tickets:
                    ticket_key = issue.key
                    last_status = known_statuses.get(ticket_key)
                    
                    if last_status is None:
                        new_tickets.append(ticket_key)
                    elif last_status == "incomplete":
                        last_jira_update_str = issue.fields.updated
                        last_db_validation_str = db_service.get_last_validation_timestamp(ticket_key)
                        
                        if not last_db_validation_str or last_jira_update_str > last_db_validation_str:
                             self._log(f"WARN: Ticket {ticket_key} was updated. Re-validating.")
                             incomplete_tickets_to_revalidate.append(ticket_key)
                
                self._log(f"Categorization complete. New: {len(new_tickets)}, To Re-validate: {len(incomplete_tickets_to_revalidate)}.")
                
                tickets_to_process = new_tickets + incomplete_tickets_to_revalidate
                
                if tickets_to_process:
                    self._log(f"Processing {len(tickets_to_process)} ticket(s): {tickets_to_process}")
                    for ticket_key in tickets_to_process:
                        await self.trigger_workflow(ticket_key)
                else:
                    self._log("No tickets require validation at this time.")
                
            except Exception as e:
                self._log(f"❌ Unhandled error during JIRA polling: {e}")
                if "ConnectionError" in str(e) or "timeout" in str(e).lower():
                    self.temporal_client = None
                    self._log("WARN: Network error. Will try reconnecting on next cycle.")
                    await asyncio.sleep(60)
                    continue
            
            self._log(f"Polling cycle complete. Next poll in {self.interval_minutes} minutes.")
            await asyncio.sleep(self.interval_minutes * 60)

    async def trigger_workflow(self, ticket_key: str):
        try:
            self._log(f"  -> Triggering validation for {ticket_key}...")
            workflow_input = TicketValidationInput(ticket_key=ticket_key)
            await self.temporal_client.start_workflow(
                "ValidateTicketWorkflow",
                workflow_input,
                id=f"validate-ticket-{ticket_key}",
                task_queue="lensora-task-queue",
                id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            )
            self._log(f"     ✅ Workflow triggered for {ticket_key}.")
        except Exception as e:
            self._log(f"     ❌ Failed to trigger workflow for {ticket_key}. Error: {e}")

polling_service = PollingService()

