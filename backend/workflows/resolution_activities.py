# File: backend/workflows/resolution_activities.py
from temporalio import activity
from backend.workflows.shared import ResolutionInput, SynthesizedSolution
from typing import List, Dict

@activity.defn
class ResolutionActivities:
    def __init__(self):
        from backend.services.rag_service import rag_service
        from backend.services.llm_service import llm_service
        from backend.services.jira_client import jira_service
        from backend.services.db_service import db_service
        
        self.rag_service = rag_service
        self.llm_service = llm_service
        self.jira_service = jira_service
        self.db_service = db_service
        
    @activity.defn
    async def find_and_synthesize_solutions_activity(self, data: ResolutionInput) -> Dict:
        """
        Finds similar tickets and uses an LLM to synthesize multiple potential solutions.
        Returns top 3 solutions to be presented in the Admin UI.
        """
        activity.logger.info(f"Resolution: Finding similar solutions for ticket {data.ticket_key}...")
        
        similar_tickets = self.rag_service.find_similar_solutions(
            query_text=data.ticket_bundled_text,
            top_k=5  # Get more similar tickets to generate better solution alternatives
        )

        if not similar_tickets:
            activity.logger.warning(f"No similar tickets found for {data.ticket_key}.")
            return {
                "solutions": [
                    {
                        "solution_text": "I could not find any similar past issues in our knowledge base. This may be a new type of problem.",
                        "confidence": 0.0,
                        "llm_provider_model": "system-generated",
                        "sources": []
                    }
                ],
                "ticket_context": data.ticket_bundled_text
            }

        activity.logger.info(f"Found {len(similar_tickets)} similar tickets in the database.")
        
        # Modified to get multiple solution alternatives
        solutions = self.llm_service.generate_solution_alternatives(
            ticket_context=data.ticket_bundled_text,
            ranked_solutions=similar_tickets,
            num_alternatives=3
        )
        
        return {
            "solutions": solutions,
            "ticket_context": data.ticket_bundled_text
        }

    @activity.defn
    async def post_solution_to_jira_activity(self, ticket_key: str, solution: SynthesizedSolution) -> str:
        """
        Posts the synthesized solution as a comment on the JIRA ticket.
        """
        activity.logger.info(f"Posting solution to JIRA ticket {ticket_key}...")
        try:
            comment = (
                f"Hello,\n\n"
                f"Based on an analysis of similar past issues, here is a suggested resolution for your ticket:\n\n"
                f"---\n"
                f"{solution.solution_text}\n"
                f"---\n\n"
                f"This is an automated suggestion generated to assist you. Please review the steps before taking action.\n\n"
                f"Sincerely,\nLensOraAI Agent"
            )
            self.jira_service.add_comment(ticket_key, comment)
            message = f"Successfully posted solution to JIRA ticket {ticket_key}."
            activity.logger.info(message)
            return message
        except Exception as e:
            error_message = f"Failed to post solution to JIRA ticket {ticket_key}. Error: {e}"
            activity.logger.error(error_message)
            return error_message

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

