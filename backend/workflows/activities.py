# File: backend/workflows/activities.py
from temporalio import activity
from jira.exceptions import JIRAError
from backend.workflows.shared import TextBundle, LLMVerdict

@activity.defn
class ValidationActivities:
    def __init__(self):
        from backend.services.jira_client import jira_service
        from backend.services.ocr_service import ocr_service
        from backend.services.db_service import db_service
        from backend.services.llm_service import llm_service
        self.jira_service = jira_service
        self.ocr_service = ocr_service
        self.db_service = db_service
        self.llm_service = llm_service

    @activity.defn
    async def fetch_and_bundle_ticket_text_activity(self, ticket_key: str) -> TextBundle:
        activity.logger.info(f"Fetching details for ticket: {ticket_key}")
        details = self.jira_service.get_ticket_details(ticket_key)
        
        text_parts = [
            f"Ticket Key: {ticket_key}",
            f"Summary: {details.get('summary', '')}",
            f"Description: {details.get('description', '')}"
        ]
        
        for attachment in details.get("attachments", []):
            content_bytes = self.jira_service.download_attachment(attachment['url'])
            extracted_text = self.ocr_service.extract_text_from_bytes(content_bytes, attachment['mimeType'])
            text_parts.append(f"\n--- Attachment: {attachment['filename']} ---\n{extracted_text}")

        return TextBundle(
            bundled_text="\n".join(text_parts), 
            reporter_id=details.get('reporter_id') # Can be None if no reporter
        )

    @activity.defn
    async def get_llm_verdict_activity(self, text_bundle: TextBundle) -> LLMVerdict:
        activity.logger.info("Fetching module knowledge and sending to LLM...")
        module_knowledge = self.db_service.get_all_modules_with_fields()
        
        verdict_dict = self.llm_service.get_validation_verdict(
            ticket_text_bundle=text_bundle.bundled_text,
            module_knowledge=module_knowledge
        )
        
        return LLMVerdict(
            detected_module=verdict_dict.get("detected_module", "Unknown"),
            validation_status=verdict_dict.get("validation_status", "error"),
            missing_fields=verdict_dict.get("missing_fields", [])
        )

    @activity.defn
    async def comment_and_reassign_activity(self, ticket_key: str, verdict: LLMVerdict, reporter_id: str) -> str:
        missing_fields_str = ", ".join(verdict.missing_fields or [])
        message = (
            f"Hello,\n\n"
            f"This ticket, identified for the '{verdict.detected_module}' process, is currently incomplete. "
            f"To proceed, please provide the following missing information:\n"
            f"- {missing_fields_str}\n\n"
            f"This ticket requires your attention. Please update it with the required details.\n\n"
            f"Thank you,\nLensOraAI Agent"
        )
        
        # --- FLAWLESS FIX ---
        # Implement the resilient fallback logic you designed.
        if not reporter_id:
            activity.logger.warning(f"No reporter found for ticket {ticket_key}. Adding comment only.")
            self.jira_service.add_comment(ticket_key, message)
            return f"Ticket {ticket_key} commented on successfully (no reassignment)."

        try:
            # Attempt the full comment and reassign operation.
            self.jira_service.comment_and_reassign(
                ticket_key=ticket_key,
                comment=message,
                assignee_id=reporter_id
            )
            return f"Ticket {ticket_key} commented on and reassigned to reporter."
        except JIRAError as e:
            # If the reassignment fails, log the error and fall back to commenting.
            activity.logger.error(f"Failed to reassign ticket {ticket_key} to {reporter_id}. Error: {e}. Falling back to comment only.")
            # We don't need to call add_comment here because the first step of 
            # comment_and_reassign already posted the comment before it failed.
            return f"Ticket {ticket_key} commented on, but reassignment failed."

