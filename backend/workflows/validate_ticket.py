# File: backend/workflows/validate_ticket.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from .shared import TicketValidationInput, TicketContext, LLMVerdict

@workflow.defn
class ValidateTicketWorkflow:
    @workflow.run
    async def run(self, input_data: TicketValidationInput) -> str:
        retry_policy = RetryPolicy(maximum_attempts=3)
        activity_options = { "start_to_close_timeout": timedelta(minutes=5), "retry_policy": retry_policy }

        workflow.logger.info(f"Gathering multimodal context for {input_data.ticket_key}")
        
        ticket_context_raw = await workflow.execute_activity(
            "fetch_and_bundle_ticket_context_activity", input_data.ticket_key, **activity_options
        )

        if isinstance(ticket_context_raw, dict):
            workflow.logger.info("Context received as dict, converting to TicketContext object.")
            ticket_context = TicketContext(**ticket_context_raw)
        else:
            ticket_context = ticket_context_raw

        llm_verdict_raw = await workflow.execute_activity(
            "get_llm_verdict_activity", ticket_context, **activity_options
        )

        if isinstance(llm_verdict_raw, dict):
            workflow.logger.info("Verdict received as dict, converting to LLMVerdict object.")
            llm_verdict = LLMVerdict(**llm_verdict_raw)
        else:
            llm_verdict = llm_verdict_raw
        
        # --- FEATURE 1.1 ENHANCEMENT ---
        # The logic for the fallback based on confidence will be added here in a future step.
        # For now, we are just logging the confidence score.
        workflow.logger.info(f"LLM Verdict received with confidence: {llm_verdict.confidence}")


        if llm_verdict.validation_status == "incomplete":
            workflow.logger.info(f"Verdict for {input_data.ticket_key}: INCOMPLETE. Missing: {llm_verdict.missing_fields}")
            if ticket_context.reporter_id:
                result_message = await workflow.execute_activity(
                    "comment_and_reassign_activity",
                    args=[input_data.ticket_key, llm_verdict, ticket_context.reporter_id],
                    **activity_options
                )
                return f"Workflow complete. Status: Incomplete. {result_message}"
            else:
                # The activity will fall back to commenting only.
                result_message = await workflow.execute_activity(
                    "comment_and_reassign_activity",
                    args=[input_data.ticket_key, llm_verdict, None],
                    **activity_options
                )
                return f"Workflow complete. Status: Incomplete. {result_message} (no reporter to reassign)."

        elif llm_verdict.validation_status == "complete":
            workflow.logger.info(f"Verdict for {input_data.ticket_key}: COMPLETE.")
            return f"Workflow complete. Status: Complete. No action taken."
        
        else:
            workflow.logger.error(f"LLM returned an error status for {input_data.ticket_key}.")
            return f"Workflow failed. Reason: LLM processing error."
