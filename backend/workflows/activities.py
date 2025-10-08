# File: backend/workflows/activities.py
from temporalio import activity
from jira.exceptions import JIRAError
from backend.workflows.shared import TicketContext, LLMVerdict
import json
from backend.services.constants import AGENT_SIGNATURE
from backend.services.priority_service import classify_priority
from backend.services.compliance_filter import scrub as compliance_scrub
from backend.services.rag_service import rag_service

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
        
        # Compliance scrub
        scrubbed_text, redactions = compliance_scrub(ticket_context.bundled_text)
        if redactions:
            activity.logger.info(f"Compliance scrub applied: {redactions} redaction(s)")
        verdict_dict = self.llm_service.get_validation_verdict(
            ticket_text_bundle=scrubbed_text,
            module_knowledge=module_knowledge,
            image_attachments=ticket_context.image_attachments
        )

        # Priority classification
        priority, reason = classify_priority(None, ticket_context.bundled_text)
        # Simple vagueness heuristic: very short or missing fields & low token diversity
        words = set([w.lower() for w in ticket_context.bundled_text.split() if w.isalpha()])
        is_vague = len(words) < 12 or ('error' in words and len(words) < 5)
        if is_vague:
            verdict_dict['is_vague'] = True
            verdict_dict['vagueness_reason'] = 'Low information density'
        verdict_dict['priority'] = priority
        # Duplicate detection using solved tickets similarity
        try:
            duplicate = rag_service.find_potential_duplicate(ticket_context.bundled_text)
            if duplicate:
                verdict_dict['duplicate_of'] = duplicate['ticket_key']
        except Exception as e:
            activity.logger.warning(f"Duplicate detection failed: {e}")
        
        return LLMVerdict(
            module=verdict_dict.get("module", "Unknown"),
            validation_status=verdict_dict.get("validation_status", "error"),
            missing_fields=verdict_dict.get("missing_fields", []),
            confidence=verdict_dict.get("confidence", 0.0),
            llm_provider_model=verdict_dict.get("llm_provider_model", "unknown"),
            priority=verdict_dict.get('priority'),
            is_vague=verdict_dict.get('is_vague', False),
            vagueness_reason=verdict_dict.get('vagueness_reason'),
            duplicate_of=verdict_dict.get('duplicate_of')
        )

    @activity.defn
    async def log_validation_result_activity(self, ticket_key: str, verdict: LLMVerdict) -> str:
        activity.logger.info(f"Logging validation verdict for {ticket_key}...")
        try:
            self.db_service.log_validation_result(ticket_key, verdict)
            message = f"Successfully logged validation verdict for {ticket_key} using model {verdict.llm_provider_model}."
            activity.logger.info(message)
            return message
        except Exception as e:
            error_message = f"Failed to log validation verdict for {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            return error_message

    @activity.defn
    async def comment_and_reassign_activity(self, ticket_key: str, verdict: LLMVerdict, reporter_id: str) -> str:
        missing_fields_str = ", ".join(verdict.missing_fields or [])
        message = (
            f"Hello,\n\n"
            f"This ticket (module: {verdict.module}) is incomplete. Please add the missing field(s):\n"
            f"- {missing_fields_str or 'None'}\n\n"
            f"Once updated, the validation agent will re-check it automatically." + AGENT_SIGNATURE
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
            
    @activity.defn
    async def notify_ticket_in_queue_activity(self, ticket_key: str) -> str:
        """
        Notifies the reporter that the ticket is now in the resolution queue.
        """
        message = (
            f"Hello,\n\n"
            f"Your ticket has passed automated validation and entered the resolution queue. "
            f"You will be notified when a proposed solution is posted." + AGENT_SIGNATURE
        )
        
        try:
            self.jira_service.add_comment(ticket_key, message)
            return f"Ticket {ticket_key} successfully notified that it's in the resolution queue."
        except Exception as e:
            error_message = f"Failed to notify ticket {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            return error_message

