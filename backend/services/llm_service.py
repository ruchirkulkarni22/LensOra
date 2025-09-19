# File: backend/services/llm_service.py
import google.generativeai as genai
import json
from backend.config import settings
from typing import List

class LLMService:
    """
    The "Brain" of the operation. This service constructs the prompt,
    calls the Gemini API with multimodal capabilities, and parses the response.
    """
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in the environment.")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def get_validation_verdict(self, ticket_text_bundle: str, module_knowledge: dict, image_attachments: List[bytes] = None) -> dict:
        """
        Calls the Gemini LLM with text and optionally images to get a
        final verdict on the ticket's completeness.
        """
        prompt = self._build_prompt(ticket_text_bundle, module_knowledge)
        
        content_parts = [prompt]
        if image_attachments:
            print(f"Adding {len(image_attachments)} image(s) to the LLM prompt.")
            for image_bytes in image_attachments:
                content_parts.append({"mime_type": "image/png", "data": image_bytes})
        
        print("--- Sending Multimodal Prompt to Gemini ---")
        
        try:
            response = self.model.generate_content(content_parts)
            cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
            
            print("--- Received Response from Gemini ---")
            print(cleaned_response)
            print("-------------------------------------")

            verdict = json.loads(cleaned_response)
            return verdict
        except Exception as e:
            print(f"Error calling Gemini API or parsing response: {e}")
            return {
                "module": "Unknown",
                "validation_status": "error",
                "missing_fields": [],
                "confidence": 0.0,
                "error_message": str(e)
            }

    def _build_prompt(self, ticket_text_bundle: str, module_knowledge: dict) -> str:
        """
        Constructs the detailed text part of the prompt for the Gemini LLM.
        """
        knowledge_str = json.dumps(module_knowledge, indent=2)
        
        # --- FEATURE 1.1 ENHANCEMENT ---
        # Updated prompt to request a confidence score and use the key 'module'.
        return f"""
        **System Preamble**
        You are an expert AI agent for Oracle ERP systems. Your task is to analyze a JIRA ticket's text AND ANY ATTACHED IMAGES to determine if it contains all the mandatory information for a business process.

        **Instructions**
        1.  Analyze the 'JIRA Ticket Text Bundle' and critically examine any images provided. Information can be in the text, images, or split between them.
        2.  Determine which ERP module the ticket relates to from the 'Module Knowledge Base'.
        3.  Check if all 'mandatory_fields' for that module are present in the combined text and image content.
        4.  Provide a confidence score (0.0 to 1.0) on how certain you are about your validation.
        5.  Provide your final verdict in a single, clean JSON object. Do not add any explanatory text.

        **JSON Output Format**
        {{
          "module": "The name of the module you identified",
          "validation_status": "Either 'complete' or 'incomplete'",
          "missing_fields": ["A list of missing mandatory fields. Empty if complete."],
          "confidence": 0.95
        }}

        ---
        **Module Knowledge Base**
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
