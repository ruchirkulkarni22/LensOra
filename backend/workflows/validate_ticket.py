# File: backend/workflows/validate_ticket.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# --- FLAWLESS FIX ---
# We no longer import the activity functions directly from '.activities'.
# This completely decouples the workflow's deterministic code from the
# activity's non-deterministic code, satisfying the Temporal sandbox.

# We still need the shared data classes, which are safe.
from .shared import TicketValidationInput, TextBundle, LLMVerdict

@workflow.defn
class ValidateTicketWorkflow:
    @workflow.run
    async def run(self, input_data: TicketValidationInput) -> str:
        """
        Executes the ticket validation workflow using the new single-LLM-call architecture.
        """
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=10),
            backoff_coefficient=2.0,
        )
        
        activity_options = {
            "start_to_close_timeout": timedelta(minutes=5),
            "retry_policy": retry_policy
        }

        # 1. Gather Context: Fetch ticket and perform OCR
        workflow.logger.info(f"Starting ticket validation for {input_data.ticket_key}")
        # We now call the activity by its string name. The worker knows how to route this.
        text_bundle_raw = await workflow.execute_activity(
            "fetch_and_bundle_ticket_text_activity",
            input_data.ticket_key,
            **activity_options
        )
        
        # Handle the case where text_bundle_result might be a dict instead of TextBundle
        workflow.logger.info(f"Text bundle type: {type(text_bundle_raw)}, data: {text_bundle_raw}")
        if isinstance(text_bundle_raw, dict):
            workflow.logger.info("Converting text bundle dict to TextBundle object")
            text_bundle_result = TextBundle(
                bundled_text=text_bundle_raw.get("bundled_text", ""),
                reporter_id=text_bundle_raw.get("reporter_id", "default_reporter")
            )
        else:
            text_bundle_result = text_bundle_raw

        # 2. Get the Verdict: Ask the "Brain" (LLM)
        # Add explicit type annotation to help Temporal with serialization/deserialization
        llm_verdict_raw = await workflow.execute_activity(
            "get_llm_verdict_activity",
            text_bundle_result,
            **activity_options
        )
        # Log the verdict details to help with debugging
        workflow.logger.info(f"Raw LLM verdict type: {type(llm_verdict_raw)}, data: {llm_verdict_raw}")

        # 3. Act on the Verdict - Now with robust type handling
        # Convert to LLMVerdict if it came back as a dict 
        if isinstance(llm_verdict_raw, dict):
            workflow.logger.info("Converting dict to LLMVerdict")
            llm_verdict = LLMVerdict(
                detected_module=llm_verdict_raw.get("detected_module", "Unknown"),
                validation_status=llm_verdict_raw.get("validation_status", "error"),
                missing_fields=llm_verdict_raw.get("missing_fields", [])
            )
        else:
            llm_verdict = llm_verdict_raw
        
        # Extract reporter_id safely
        reporter_id = text_bundle_result.reporter_id if hasattr(text_bundle_result, "reporter_id") else "default_reporter"
        workflow.logger.info(f"Using reporter_id: {reporter_id}")
        
        # Now proceed with the properly typed verdict
        if llm_verdict.validation_status == "incomplete":
            workflow.logger.info(f"LLM verdict for {input_data.ticket_key}: INCOMPLETE. Missing fields: {llm_verdict.missing_fields}")
            result_message = await workflow.execute_activity(
                "comment_and_reassign_activity",
                args=[input_data.ticket_key, llm_verdict, reporter_id],
                **activity_options
            )
            return f"Workflow complete for {input_data.ticket_key}. Status: Incomplete. {result_message}"
        
        elif llm_verdict.validation_status == "complete":
            workflow.logger.info(f"LLM verdict for {input_data.ticket_key}: COMPLETE.")
            return f"Workflow complete for {input_data.ticket_key}. Status: Complete. No action taken."
        
        else: # Handle errors from the LLM
            error_status = getattr(llm_verdict, "validation_status", "unknown")
            workflow.logger.error(f"LLM returned an error status for {input_data.ticket_key}: {error_status}")
            return f"Workflow failed for {input_data.ticket_key}. Reason: LLM processing error."

