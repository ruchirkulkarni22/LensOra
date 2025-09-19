# File: backend/services/llm_service.py
import google.generativeai as genai
import openai
import json
from backend.config import settings
from typing import List, Dict, Any

class LLMService:
    """
    The "Brain" of the operation. This service manages a chain of LLM providers,
    constructing prompts, calling APIs with robust fallback and retry logic,
    and parsing the structured JSON response.
    """
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        if settings.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        self.google_models = {}

    def _get_google_model(self, model_name: str):
        """Lazy initializes and caches Google Generative Models to save resources."""
        if model_name not in self.google_models:
            print(f"Initializing Google model: {model_name}")
            self.google_models[model_name] = genai.GenerativeModel(model_name)
        return self.google_models[model_name]

    def get_validation_verdict(self, ticket_text_bundle: str, module_knowledge: dict, image_attachments: List[bytes] = None) -> Dict[str, Any]:
        """
        Orchestrates calls to a chain of LLMs. It tries each model in the
        configured fallback chain until one returns a valid, parsable JSON verdict.
        """
        prompt = self._build_prompt(ticket_text_bundle, module_knowledge)
        
        for model_name in settings.LLM_FALLBACK_CHAIN:
            print(f"\n--- Attempting validation with model: {model_name} ---")
            
            for attempt in range(2): # Allow one retry for malformed JSON, as per PRD
                try:
                    raw_response = ""
                    if "gemini" in model_name:
                        raw_response = self._call_gemini(model_name, prompt, image_attachments)
                    elif "gpt" in model_name:
                        # Note: OpenAI's current API does not support images and text in a single prompt part.
                        # We will send the text prompt only for GPT models as a fallback.
                        if image_attachments:
                            print(f"WARNING: GPT model '{model_name}' does not support multimodal input. Sending text only.")
                        raw_response = self._call_openai(model_name, prompt)
                    else:
                        print(f"Unsupported model provider for: {model_name}")
                        continue

                    # Clean and parse the response
                    cleaned_response = raw_response.strip().replace("```json", "").replace("```", "")
                    verdict = json.loads(cleaned_response)
                    
                    # Add the successful model's name to the verdict
                    verdict['llm_provider_model'] = model_name
                    
                    print(f"✅ Success with model: {model_name}")
                    print("--- Received Response ---")
                    print(json.dumps(verdict, indent=2))
                    print("-------------------------")
                    return verdict

                except json.JSONDecodeError as e:
                    print(f"❌ Malformed JSON from {model_name} on attempt {attempt + 1}. Error: {e}")
                    if attempt == 0:
                        print("Retrying once with the same model...")
                    # On the second failed attempt, the outer loop will proceed to the next model.
                
                except Exception as e:
                    print(f"❌ API call failed for model {model_name}. Error: {e}")
                    # Break the retry loop and go to the next model immediately on API failure.
                    break 
        
        # If all models in the chain fail
        print("❌ All LLM providers in the fallback chain failed.")
        return {
            "module": "Unknown",
            "validation_status": "error",
            "missing_fields": [],
            "confidence": 0.0,
            "error_message": "All LLM providers failed.",
            "llm_provider_model": "N/A"
        }

    def _call_gemini(self, model_name: str, prompt: str, image_attachments: List[bytes]) -> str:
        """Calls the Google Gemini API."""
        model = self._get_google_model(model_name)
        content_parts = [prompt]
        if image_attachments:
            print(f"Adding {len(image_attachments)} image(s) to the Gemini prompt.")
            for image_bytes in image_attachments:
                # Gemini expects a dict for image data
                content_parts.append({"mime_type": "image/jpeg", "data": image_bytes})
        
        response = model.generate_content(content_parts)
        return response.text

    def _call_openai(self, model_name: str, prompt: str) -> str:
        """Calls the OpenAI API."""
        chat_completion = self.openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an expert AI agent. Please only respond with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            model=model_name,
            response_format={"type": "json_object"},
        )
        return chat_completion.choices[0].message.content

    def _build_prompt(self, ticket_text_bundle: str, module_knowledge: dict) -> str:
        """Constructs the detailed text prompt for the LLM."""
        knowledge_str = json.dumps(module_knowledge, indent=2)
        
        return f"""
        **System Preamble**
        You are an expert AI agent for Oracle ERP systems. Your task is to analyze a JIRA ticket's text and any attached images to determine if it contains all the mandatory information for a business process.

        **Instructions**
        1.  Analyze the 'JIRA Ticket Text Bundle' and critically examine any images provided.
        2.  Determine which ERP module the ticket relates to from the 'Module Knowledge Base'.
        3.  Check if all 'mandatory_fields' for that module are present in the combined content.
        4.  Provide a numeric confidence score (0.0 to 1.0) for your validation.
        5.  Provide your final verdict in a single, clean JSON object. Do not add any text outside the JSON.

        **JSON Output Format**
        {{
          "module": "The name of the module you identified (e.g., AP.Invoice)",
          "validation_status": "Either 'complete' or 'incomplete'",
          "missing_fields": ["A list of missing mandatory fields. Empty if complete."],
          "confidence": 1.0
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

