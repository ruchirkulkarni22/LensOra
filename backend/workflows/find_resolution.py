# File: backend/workflows/find_resolution.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from .shared import ResolutionInput, SynthesizedSolution
from typing import Dict, List, Any

@workflow.defn
class FindResolutionWorkflow:
    @workflow.run
    async def run(self, input_data: ResolutionInput) -> Dict:
        """
        Generates solution alternatives for a ticket but does not post them.
        The results will be displayed in the Admin UI for human review.
        
        Returns a dictionary with all solution alternatives and ticket context.
        """
        workflow.logger.info(f"Resolution workflow started for ticket: {input_data.ticket_key}")

        retry_policy = RetryPolicy(maximum_attempts=2)
        activity_options = {
            "start_to_close_timeout": timedelta(minutes=5),
            "retry_policy": retry_policy
        }

        # This now returns a dictionary with multiple solution alternatives
        solutions_data = await workflow.execute_activity(
            "find_and_synthesize_solutions_activity",
            input_data,
            **activity_options
        )
        
        workflow.logger.info(f"Resolution workflow for {input_data.ticket_key} completed with {len(solutions_data['solutions'])} solution alternatives.")
        return solutions_data
        
@workflow.defn
class PostResolutionWorkflow:
    """
    A new workflow for posting a human-approved solution to JIRA.
    This is triggered from the Admin UI after a human reviews and selects a solution.
    """
    @workflow.run
    async def run(self, ticket_key: str, solution: Dict[str, Any]) -> str:
        """
        Posts a human-approved solution to JIRA and logs it in the database.
        """
        workflow.logger.info(f"Posting approved solution for ticket: {ticket_key}")
        
        retry_policy = RetryPolicy(maximum_attempts=2)
        activity_options = {
            "start_to_close_timeout": timedelta(minutes=5),
            "retry_policy": retry_policy
        }
        
        # Convert the solution dict to a SynthesizedSolution object
        synthesized_solution = SynthesizedSolution(
            solution_text=solution["solution_text"],
            llm_provider_model=solution.get("llm_provider_model", "human-approved")
        )
        
        # Post to JIRA
        await workflow.execute_activity(
            "post_solution_to_jira_activity",
            args=[ticket_key, synthesized_solution],
            **activity_options,
        )

        # Log the resolution
        await workflow.execute_activity(
            "log_resolution_activity",
            args=[ticket_key, synthesized_solution],
            **activity_options,
        )
        
        workflow.logger.info(f"Human-approved solution posted to JIRA ticket {ticket_key}.")
        return f"Human-approved solution posted to JIRA ticket {ticket_key}."
