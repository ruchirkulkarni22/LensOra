# File: backend/workflows/find_resolution.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from .shared import ResolutionInput, SynthesizedSolution

@workflow.defn
class FindResolutionWorkflow:
    @workflow.run
    async def run(self, input_data: ResolutionInput) -> str:
        """
        Executes the full resolution process for a validated ticket.
        """
        workflow.logger.info(f"Resolution workflow started for ticket: {input_data.ticket_key}")

        retry_policy = RetryPolicy(maximum_attempts=2)
        activity_options = {
            "start_to_close_timeout": timedelta(minutes=5),
            "retry_policy": retry_policy
        }

        # The activity returns a result that might be a dict due to serialization.
        solution_result_raw = await workflow.execute_activity(
            "find_and_synthesize_solutions_activity",
            input_data,
            **activity_options
        )

        # --- FLAWLESS FIX ---
        # We apply our resilient pattern: check if the result is a dict,
        # and if so, convert it back to the expected SynthesizedSolution object.
        if isinstance(solution_result_raw, dict):
            workflow.logger.info("Solution received as dict, converting to SynthesizedSolution object.")
            solution_result = SynthesizedSolution(**solution_result_raw)
        else:
            solution_result = solution_result_raw

        workflow.logger.info(f"Resolution workflow for {input_data.ticket_key} completed.")
        return f"Resolution Found: {solution_result.solution_text}"

