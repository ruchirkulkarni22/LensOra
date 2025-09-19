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

        solution_result_raw = await workflow.execute_activity(
            "find_and_synthesize_solutions_activity",
            input_data,
            **activity_options
        )

        if isinstance(solution_result_raw, dict):
            solution_result = SynthesizedSolution(**solution_result_raw)
        else:
            solution_result = solution_result_raw

        # --- FINAL FEATURE ---
        # Call the new activities to post the solution and log the result.
        await workflow.execute_activity(
            "post_solution_to_jira_activity",
            args=[input_data.ticket_key, solution_result],
            **activity_options,
        )

        await workflow.execute_activity(
            "log_resolution_activity",
            args=[input_data.ticket_key, solution_result],
            **activity_options,
        )

        workflow.logger.info(f"Resolution workflow for {input_data.ticket_key} completed and posted.")
        return f"Solution posted to JIRA ticket {input_data.ticket_key}."

