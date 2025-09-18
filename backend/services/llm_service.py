# File: backend/services/llm_service.py
import google.generativeai as genai
import json
from backend.config import settings

class LLMService:
    """
    The "Brain" of the operation. This service constructs the prompt,
    calls the Gemini API, and parses the response.
    """
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in the environment.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def get_validation_verdict(self, ticket_text_bundle: str, module_knowledge: dict) -> dict:
        """
        Calls the Gemini LLM with the ticket context and module knowledge to get a
        final verdict on the ticket's completeness.
        """
        prompt = self._build_prompt(ticket_text_bundle, module_knowledge)
        
        print("--- Sending Prompt to Gemini ---")
        print(prompt)
        print("---------------------------------")
        
        try:
            response = self.model.generate_content(prompt)
            # The response text might be enclosed in markdown backticks
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            
            print("--- Received Response from Gemini ---")
            print(cleaned_response)
            print("-------------------------------------")

            verdict = json.loads(cleaned_response)
            return verdict
        except Exception as e:
            print(f"Error calling Gemini API or parsing response: {e}")
            # Fallback response in case of LLM error
            return {
                "detected_module": "Unknown",
                "validation_status": "error",
                "missing_fields": [],
                "error_message": str(e)
            }

    def _build_prompt(self, ticket_text_bundle: str, module_knowledge: dict) -> str:
        """
        Constructs the detailed prompt for the Gemini LLM.
        """
        # Convert the knowledge dictionary to a formatted string for the prompt
        knowledge_str = json.dumps(module_knowledge, indent=2)
        
        return f"""
        **System Preamble**
        You are an expert AI agent for Oracle ERP systems. Your task is to analyze a JIRA ticket's text and determine if it contains all the mandatory information required for a specific business process module.

        **Instructions**
        1.  Analyze the 'JIRA Ticket Text Bundle' provided below.
        2.  First, determine which ERP module the ticket relates to. Choose from one of the modules listed in the 'Module Knowledge Base'. If the ticket doesn't match any module, classify it as 'General.Inquiry'.
        3.  Once the module is identified, check if all the 'mandatory_fields' for that module are present in the ticket text.
        4.  Provide your final verdict in a single, clean JSON object. Do not add any explanatory text before or after the JSON object.

        **JSON Output Format**
        Your response MUST be a JSON object with the following structure:
        {{
          "detected_module": "The name of the module you identified (e.g., 'AP.Invoice')",
          "validation_status": "Either 'complete' or 'incomplete'",
          "missing_fields": ["A list of strings of the mandatory fields that are missing. This should be an empty list if the status is 'complete'."]
        }}

        ---
        **Module Knowledge Base (All possible modules and their required fields)**
        ```json
        {knowledge_str}
        ```
        ---
        **JIRA Ticket Text Bundle**
        ```text
        {ticket_text_bundle}
        ```
        ---
        **Your Verdict (JSON only)**
        """

llm_service = LLMService()
