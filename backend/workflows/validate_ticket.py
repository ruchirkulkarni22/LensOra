# File: backend/workflows/validate_ticket.py
from datetime import timedelta
from temporalio import workflow
# --- FLAWLESS FIX ---
# RetryPolicy is imported from temporalio.common, not workflow.
from temporalio.common import RetryPolicy
from .shared import TicketValidationInput, TicketContext, LLMVerdict, ResolutionInput
from .find_resolution import FindResolutionWorkflow

@workflow.defn
class ValidateTicketWorkflow:
    @workflow.run
    async def run(self, input_data: TicketValidationInput) -> str:
        # --- FLAWLESS FIX ---
        # We now correctly instantiate RetryPolicy directly.
        retry_policy = RetryPolicy(maximum_attempts=3)
        activity_options = { "start_to_close_timeout": timedelta(minutes=5), "retry_policy": retry_policy }

        ticket_context_raw = await workflow.execute_activity(
            "fetch_and_bundle_ticket_context_activity", input_data.ticket_key, **activity_options
        )
        ticket_context = TicketContext(**ticket_context_raw) if isinstance(ticket_context_raw, dict) else ticket_context_raw

        llm_verdict_raw = await workflow.execute_activity(
            "get_llm_verdict_activity", ticket_context, **activity_options
        )
        llm_verdict = LLMVerdict(**llm_verdict_raw) if isinstance(llm_verdict_raw, dict) else llm_verdict_raw

        await workflow.execute_activity(
            "log_validation_result_activity", args=[input_data.ticket_key, llm_verdict], **activity_options
        )

        if llm_verdict.validation_status == "incomplete":
            workflow.logger.info(f"Verdict for {input_data.ticket_key}: INCOMPLETE.")
            if ticket_context.reporter_id:
                result_message = await workflow.execute_activity(
                    "comment_and_reassign_activity",
                    args=[input_data.ticket_key, llm_verdict, ticket_context.reporter_id],
                    **activity_options
                )
                return f"Workflow complete. Status: Incomplete. {result_message}"
            else:
                result_message = await workflow.execute_activity(
                    "comment_and_reassign_activity",
                    args=[input_data.ticket_key, llm_verdict, None],
                    **activity_options
                )
                return f"Workflow complete. Status: Incomplete. {result_message} (no reporter to reassign)."

        elif llm_verdict.validation_status == "complete":
            workflow.logger.info(f"Verdict for {input_data.ticket_key}: COMPLETE. This ticket is ready for human review.")
            
            # Note: We no longer automatically start the resolution workflow here.
            # Instead, the ticket is now marked as 'complete' in the database,
            # and will be displayed in the Admin UI queue for human review.
            
            # Add a comment to the ticket informing the reporter that the ticket is being processed
            result_message = await workflow.execute_activity(
                "notify_ticket_in_queue_activity",
                args=[input_data.ticket_key],
                **activity_options
            )
            
            return f"Workflow complete. Status: Complete. Ticket is ready for human review in the Admin UI."
        
        else:
            workflow.logger.error(f"LLM returned an error status for {input_data.ticket_key}.")
            return "Workflow failed. Reason: LLM processing error."

