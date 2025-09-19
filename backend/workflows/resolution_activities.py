# File: backend/workflows/resolution_activities.py
from temporalio import activity
from backend.workflows.shared import ResolutionInput, SynthesizedSolution
from typing import List, Dict

@activity.defn
class ResolutionActivities:
    def __init__(self):
        from backend.services.rag_service import rag_service
        from backend.services.llm_service import llm_service
        # --- FINAL FEATURE ---
        # Add the jira_service and db_service for the new activities.
        from backend.services.jira_client import jira_service
        from backend.services.db_service import db_service
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.jira_service = jira_service
        self.db_service = db_service

    @activity.defn
    async def find_and_synthesize_solutions_activity(self, data: ResolutionInput) -> SynthesizedSolution:
        """
        Finds similar tickets and uses an LLM to synthesize a new solution.
        """
        activity.logger.info(f"Resolution: Finding similar solutions for ticket {data.ticket_key}...")
        
        similar_tickets = self.rag_service.find_similar_solutions(
            query_text=data.ticket_bundled_text,
            top_k=3
        )

        if not similar_tickets:
            activity.logger.warning(f"No similar tickets found for {data.ticket_key}.")
            return SynthesizedSolution(solution_text="I could not find any similar past issues in our knowledge base. This may be a new type of issue that requires manual investigation.", llm_provider_model="N/A")

        activity.logger.info(f"Found {len(similar_tickets)} similar tickets. Synthesizing solution...")
        
        synthesized_text, model_used = self.llm_service.synthesize_solutions(
            ticket_context=data.ticket_bundled_text,
            ranked_solutions=similar_tickets
        )
        
        activity.logger.info(f"Successfully synthesized solution for {data.ticket_key}.")
        print("--- Synthesized Solution ---")
        print(synthesized_text)
        print("----------------------------")

        return SynthesizedSolution(solution_text=synthesized_text, llm_provider_model=model_used)

    # --- FINAL FEATURE ---
    # New activity to post the final solution as a comment in JIRA.
    @activity.defn
    async def post_solution_to_jira_activity(self, ticket_key: str, solution: SynthesizedSolution) -> str:
        """
        Posts the synthesized solution to the JIRA ticket as a public comment.
        """
        activity.logger.info(f"Posting solution to JIRA ticket {ticket_key}...")
        try:
            comment = (
                f"Hello,\n\n"
                f"LensOraAI has analyzed this ticket and found potential solutions based on past issues:\n\n"
                f"---\n\n"
                f"{solution.solution_text}\n\n"
                f"---\n\n"
                f"This is an automated suggestion. Please review and verify the steps.\n"
                f"(Model used: {solution.llm_provider_model})"
            )
            self.jira_service.add_comment(ticket_key, comment)
            message = f"Successfully posted solution to JIRA ticket {ticket_key}."
            activity.logger.info(message)
            return message
        except Exception as e:
            error_message = f"Failed to post solution to JIRA ticket {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            # Do not fail the workflow, just log the error.
            return error_message
            
    # --- FINAL FEATURE ---
    # New activity to log the successful resolution to our database.
    @activity.defn
    async def log_resolution_activity(self, ticket_key: str, solution: SynthesizedSolution) -> str:
        """
        Logs the details of the successful resolution to the database.
        """
        activity.logger.info(f"Logging resolution for ticket {ticket_key}...")
        try:
            self.db_service.log_resolution(ticket_key, solution)
            message = f"Successfully logged resolution for ticket {ticket_key}."
            activity.logger.info(message)
            return message
        except Exception as e:
            error_message = f"Failed to log resolution for {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            return error_message

