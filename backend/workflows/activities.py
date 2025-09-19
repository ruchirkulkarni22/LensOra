# File: backend/workflows/activities.py
from temporalio import activity
from jira.exceptions import JIRAError
from backend.workflows.shared import TicketContext, LLMVerdict
import json

@activity.defn
class ValidationActivities:
    def __init__(self):
        # Lazy imports to avoid circular dependencies and speed up worker start
        from backend.services.jira_client import jira_service
        from backend.services.ocr_service import ocr_service
        from backend.services.db_service import db_service
        from backend.services.llm_service import llm_service
        self.jira_service = jira_service
        self.ocr_service = ocr_service
        self.db_service = db_service
        self.llm_service = llm_service

    @activity.defn
    async def fetch_and_bundle_ticket_context_activity(self, ticket_key: str) -> TicketContext:
        activity.logger.info(f"Fetching context for ticket: {ticket_key}")
        details = self.jira_service.get_ticket_details(ticket_key)
        
        text_parts = [
            f"Ticket Key: {ticket_key}",
            f"Summary: {details.get('summary', '')}",
            f"Description: {details.get('description', '')}"
        ]
        
        image_bytes_list = []
        for attachment in details.get("image_attachments", []):
            activity.logger.info(f"Downloading image attachment: {attachment['filename']}")
            image_bytes = self.jira_service.download_attachment(attachment['url'])
            image_bytes_list.append(image_bytes)

        for attachment in details.get("other_attachments", []):
            activity.logger.info(f"Processing non-image attachment: {attachment['filename']}")
            content_bytes = self.jira_service.download_attachment(attachment['url'])
            extracted_text = self.ocr_service.extract_text_from_bytes(content_bytes, attachment['mimeType'])
            text_parts.append(f"\n--- Attachment: {attachment['filename']} ---\n{extracted_text}")

        return TicketContext(
            bundled_text="\n".join(text_parts), 
            reporter_id=details.get('reporter_id'),
            image_attachments=image_bytes_list
        )

    @activity.defn
    async def get_llm_verdict_activity(self, ticket_context: TicketContext) -> LLMVerdict:
        activity.logger.info("Fetching module knowledge and sending context to LLM...")
        module_knowledge = self.db_service.get_all_modules_with_fields()
        
        verdict_dict = self.llm_service.get_validation_verdict(
            ticket_text_bundle=ticket_context.bundled_text,
            module_knowledge=module_knowledge,
            image_attachments=ticket_context.image_attachments
        )
        
        return LLMVerdict(
            module=verdict_dict.get("module", "Unknown"),
            validation_status=verdict_dict.get("validation_status", "error"),
            missing_fields=verdict_dict.get("missing_fields", []),
            confidence=verdict_dict.get("confidence", 0.0),
            llm_provider_model=verdict_dict.get("llm_provider_model", "unknown")
        )

    @activity.defn
    async def log_validation_result_activity(self, ticket_key: str, verdict: LLMVerdict) -> str:
        activity.logger.info(f"Logging validation verdict for {ticket_key}...")
        try:
            # --- FLAWLESS FIX ---
            # Corrected the method name from log_validation_verdict to log_validation_result
            self.db_service.log_validation_result(ticket_key, verdict)
            message = f"Successfully logged validation verdict for {ticket_key} using model {verdict.llm_provider_model}."
            activity.logger.info(message)
            return message
        except Exception as e:
            error_message = f"Failed to log validation verdict for {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            # We will not raise the exception to avoid failing the whole workflow
            return error_message

    @activity.defn
    async def comment_and_reassign_activity(self, ticket_key: str, verdict: LLMVerdict, reporter_id: str) -> str:
        missing_fields_str = ", ".join(verdict.missing_fields or [])
        message = (
            f"Hello,\n\n"
            f"This ticket, identified for the '{verdict.module}' process, is currently incomplete. "
            f"To proceed, please provide the following missing information:\n"
            f"- {missing_fields_str}\n\n"
            f"This ticket requires your attention. Please update it with the required details.\n\n"
            f"Thank you,\nLensOraAI Agent"
        )
        
        if not reporter_id:
            activity.logger.warning(f"No reporter found for ticket {ticket_key}. Adding comment only.")
            self.jira_service.add_comment(ticket_key, message)
            return f"Ticket {ticket_key} commented on successfully (no reassignment)."

        try:
            self.jira_service.comment_and_reassign(
                ticket_key=ticket_key,
                comment=message,
                assignee_id=reporter_id
            )
            return f"Ticket {ticket_key} commented on and reassigned to reporter."
        except JIRAError as e:
            activity.logger.error(f"Failed to reassign ticket {ticket_key}, falling back to comment-only. Error: {e}")
            self.jira_service.add_comment(ticket_key, message)
            return f"Ticket {ticket_key} commented on, but reassignment failed."

