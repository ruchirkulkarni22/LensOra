# File: backend/services/jira_client.py
import requests
from jira import JIRA, JIRAError
from backend.config import settings
import json

class JiraService:
    """
    A client to interact with the JIRA API.
    """
    def __init__(self):
        if not all([settings.JIRA_URL, settings.JIRA_USERNAME, settings.JIRA_API_TOKEN]):
            raise ValueError("JIRA credentials are not fully configured in .env file.")
        
        self.client = JIRA(
            server=settings.JIRA_URL,
            basic_auth=(settings.JIRA_USERNAME, settings.JIRA_API_TOKEN),
            options={'headers': {'Accept': 'application/json'}}
        )

    def get_ticket_details(self, ticket_key: str) -> dict:
        """
        Fetches the summary, description, reporter, and attachments of a JIRA ticket.
        """
        issue = self.client.issue(ticket_key)
        
        # --- FLAWLESS UPGRADE ---
        # We now separate image attachments from other file types so the
        # multimodal LLM can process them correctly.
        image_attachments = []
        other_attachments = []
        for attachment in issue.fields.attachment:
            attachment_details = {
                "filename": attachment.filename,
                "url": attachment.content,
                "mimeType": attachment.mimeType
            }
            if 'image' in attachment.mimeType:
                image_attachments.append(attachment_details)
            else:
                other_attachments.append(attachment_details)
        
        reporter_id = None
        if hasattr(issue.fields.reporter, 'accountId'):
            reporter_id = issue.fields.reporter.accountId
        
        return {
            "summary": issue.fields.summary,
            "description": issue.fields.description,
            "reporter_id": reporter_id,
            "image_attachments": image_attachments,
            "other_attachments": other_attachments
        }

    def download_attachment(self, url: str) -> bytes:
        """
        Downloads the content of a ticket attachment.
        """
        response = requests.get(
            url,
            auth=(settings.JIRA_USERNAME, settings.JIRA_API_TOKEN),
            stream=True
        )
        response.raise_for_status()
        return response.content

    def add_comment(self, ticket_key: str, comment: str):
        """
        Adds a comment to a JIRA ticket. This is the safe fallback action.
        """
        print(f"Adding comment only to {ticket_key}")
        self.client.add_comment(ticket_key, comment)
    
    def comment_and_reassign(self, ticket_key: str, comment: str, assignee_id: str):
        """
        Adds a comment and then robustly reassigns the ticket using a direct API call.
        """
        self.client.add_comment(ticket_key, comment)
        assign_url = f"{self.client._options['server']}/rest/api/2/issue/{ticket_key}/assignee"
        payload = json.dumps({"accountId": assignee_id})
        session = self.client._session
        headers = {"Content-Type": "application/json"}
        print(f"Attempting to reassign {ticket_key} to {assignee_id} via direct API call.")
        response = session.put(assign_url, data=payload, headers=headers)
        response.raise_for_status()

jira_service = JiraService()

