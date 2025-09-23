# File: backend/services/llm_service.py
import google.generativeai as genai
from openai import OpenAI, AuthenticationError
from google.api_core.exceptions import ResourceExhausted
import json
import time
import random
from backend.config import settings
from typing import List, Dict, Tuple
from backend.workflows.shared import SynthesizedSolution

class LLMService:
    """
    The "Brain" of the operation. Handles LLM calls for both validation and synthesis,
    with a built-in fallback chain and retry logic for reliability.
    """
    def __init__(self):
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.model_fallback_chain = settings.LLM_FALLBACK_CHAIN

    def _get_client(self, model_name: str):
        if "gemini" in model_name:
            if not self.gemini_api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            genai.configure(api_key=self.gemini_api_key)
            return genai.GenerativeModel(model_name)
        elif "gpt" in model_name:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not configured.")
            return OpenAI(api_key=self.openai_api_key)
        else:
            raise ValueError(f"Unsupported model provider for: {model_name}")

    def _make_api_call(self, client, model_name: str, content_parts: List) -> str:
        if "gemini" in model_name:
            response = client.generate_content(content_parts)
            return response.text
        elif "gpt" in model_name:
            messages = [{"role": "user", "content": [part if isinstance(part, str) else {"type": "image_url", "image_url": {"url": f"data:{part['mime_type']};base64,{part['data'].hex()}"}} for part in content_parts]}]
            response = client.chat.completions.create(model=model_name, messages=messages)
            return response.choices[0].message.content
        return ""
        
    def get_validation_verdict(self, ticket_text_bundle: str, module_knowledge: dict, image_attachments: List[bytes] = None) -> dict:
        prompt = self._build_validation_prompt(ticket_text_bundle, module_knowledge)
        content_parts = [prompt]
        if image_attachments:
            print(f"Adding {len(image_attachments)} image(s) to the LLM prompt.")
            for image_bytes in image_attachments:
                content_parts.append({"mime_type": "image/png", "data": image_bytes})
        
        last_error = None
        for model_name in self.model_fallback_chain:
            max_retries = 3
            base_delay = 2  # Start with a 2-second delay

            for attempt in range(max_retries):
                try:
                    print(f"--- Attempting validation with model: {model_name} (Attempt {attempt + 1}/{max_retries}) ---")
                    client = self._get_client(model_name)
                    raw_response = self._make_api_call(client, model_name, content_parts)
                    cleaned_response = raw_response.strip().replace("```json", "").replace("```", "")
                    
                    print("--- Received Response ---")
                    print(cleaned_response)
                    print("-------------------------")

                    verdict = json.loads(cleaned_response)
                    verdict['llm_provider_model'] = model_name
                    print(f"✅ Success with model: {model_name}")
                    return verdict

                except (ResourceExhausted) as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"Rate limit exceeded for {model_name}. Retrying in {delay:.2f} seconds...")
                        time.sleep(delay)
                    else:
                        print(f"Rate limit exceeded for {model_name}. Max retries reached.")
                        break # Break from retry loop, move to next model
                
                except AuthenticationError as e:
                    last_error = e
                    print(f"Authentication error for {model_name}. Check your API key. Skipping to next model.")
                    break # Break from retry loop, no point in retrying auth error

                except Exception as e:
                    last_error = e
                    print(f"❌ API call failed for model {model_name} on attempt {attempt + 1}. Error: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(base_delay) # Wait before generic retry
                    continue
            
            # If the retry loop completes without success, the outer loop continues to the next model
        
        return {
            "module": "Unknown", "validation_status": "error", "missing_fields": [],
            "confidence": 0.0, "llm_provider_model": "all_failed",
            "error_message": f"All LLM providers failed. Last error: {str(last_error)}"
        }

    def synthesize_solutions(self, ticket_context: str, ranked_solutions: List[Dict]) -> SynthesizedSolution:
        prompt = self._build_synthesis_prompt(ticket_context, ranked_solutions)
        content_parts = [prompt]
        
        last_error = None
        for model_name in self.model_fallback_chain:
            try:
                print(f"--- Attempting synthesis with model: {model_name} ---")
                client = self._get_client(model_name)
                response_text = self._make_api_call(client, model_name, content_parts)
                
                print(f"✅ Synthesis success with model: {model_name}")
                return SynthesizedSolution(
                    solution_text=response_text,
                    llm_provider_model=model_name
                )
            except Exception as e:
                last_error = e
                print(f"❌ Synthesis failed for model {model_name}. Error: {e}")
                continue

        return SynthesizedSolution(
            solution_text=f"Could not generate a solution. All LLM providers failed. Last error: {last_error}",
            llm_provider_model="all_failed"
        )
    
    def generate_solution_alternatives(self, ticket_context: str, ranked_solutions: List[Dict], num_alternatives: int = 3) -> List[Dict]:
        solutions_by_approach = [
            ranked_solutions[:2],
            ranked_solutions[2:4] if len(ranked_solutions) > 2 else ranked_solutions[:1],
            ranked_solutions[-2:] if len(ranked_solutions) > 4 else ranked_solutions[:1]
        ]
        
        alternatives = []
        prompt_templates = [
            "Focus on step-by-step troubleshooting for the user",
            "Focus on the most direct solution path based on similar cases",
            "Focus on explaining the root cause and how to prevent this in the future"
        ]
        
        model_name = self.model_fallback_chain[0]
        
        try:
            client = self._get_client(model_name)
            
            for i in range(min(num_alternatives, len(prompt_templates))):
                try:
                    approach_prompt = self._build_alternative_solution_prompt(
                        ticket_context, 
                        solutions_by_approach[i], 
                        prompt_templates[i]
                    )
                    content_parts = [approach_prompt]
                    
                    response_text = self._make_api_call(client, model_name, content_parts)
                    
                    confidence = 0.9 - (i * 0.1)
                    
                    alternatives.append({
                        "solution_text": response_text,
                        "confidence": confidence,
                        "llm_provider_model": model_name,
                        "sources": [{"key": ticket["ticket_key"], "summary": ticket["summary"]} for ticket in solutions_by_approach[i]]
                    })
                except Exception as e:
                    print(f"Failed to generate alternative {i+1}: {e}")
        except Exception as e:
            print(f"Failed to initialize LLM client: {e}")
            
        if not alternatives:
            alternatives.append({
                "solution_text": "Could not generate solution alternatives. Please check the system logs.",
                "confidence": 0.0,
                "llm_provider_model": "fallback",
                "sources": []
            })
            
        return alternatives


    def _build_validation_prompt(self, ticket_text_bundle: str, module_knowledge: dict) -> str:
        knowledge_str = json.dumps(module_knowledge, indent=2)
        return f"""
        **System Preamble**
        You are an expert AI agent for Oracle ERP systems. Your task is to analyze a JIRA ticket's text AND ANY ATTACHED IMAGES to determine if it contains all mandatory information for a business process.

        **Instructions**
        1. Analyze the 'JIRA Ticket Text Bundle' and any images provided.
        2. Determine which ERP module the ticket relates to from the 'Module Knowledge Base'.
        3. Check if all 'mandatory_fields' for that module are present.
        4. Provide your verdict in a single, clean JSON object. Do not add any explanatory text.

        **JSON Output Format**
        {{
          "module": "The name of the module you identified (e.g., 'AP.Invoice')",
          "validation_status": "Either 'complete' or 'incomplete'",
          "missing_fields": ["A list of missing mandatory fields. Empty if complete."],
          "confidence": A float from 0.0 to 1.0 indicating your confidence in the verdict.
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

    def _build_synthesis_prompt(self, ticket_context: str, ranked_solutions: List[Dict]) -> str:
        solutions_str = "\n\n---\n\n".join([
            f"**Ticket:** {sol['ticket_key']}\n**Summary:** {sol['summary']}\n**Resolution:** {sol['resolution']}"
            for sol in ranked_solutions
        ])
        
        return f"""
        **System Preamble**
        You are an expert AI agent for Oracle ERP systems. Your task is to act as a helpful senior support engineer. You will be given a new JIRA ticket and a list of historical tickets that are similar. Your goal is to synthesize the historical resolutions into a concise, actionable set of recommendations for the new ticket.

        **Instructions**
        1.  Carefully read the 'New JIRA Ticket'.
        2.  Analyze the 'Historical Solutions' provided. These are from past tickets that were similar.
        3.  Synthesize the information into a clear, step-by-step guide or a set of questions to help the user solve their problem.
        4.  IMPORTANT: Do not just copy the old resolutions. Combine the ideas. If the historical solutions all point to a common root cause (e.g., a locked account), state that as the likely problem.
        5.  Keep your response concise and professional. Start with a polite opening.
        
        ---
        **New JIRA Ticket**
        ```text
        {ticket_context}
        ```
        ---
        **Historical Solutions**
        ```text
        {solutions_str}
        ```
        ---
        **Your Recommended Solution**
        """
        
    def _build_alternative_solution_prompt(self, ticket_context: str, ranked_solutions: List[Dict], approach_focus: str) -> str:
        solutions_str = "\n\n---\n\n".join([
            f"**Ticket:** {sol['ticket_key']}\n**Summary:** {sol['summary']}\n**Resolution:** {sol['resolution']}"
            for sol in ranked_solutions
        ])
        
        return f"""
        **System Preamble**
        You are an expert AI agent for Oracle ERP systems. Your task is to act as a helpful senior support engineer. You will be given a new JIRA ticket and a list of historical tickets that are similar. Your goal is to synthesize the historical resolutions into a concise, actionable set of recommendations for the new ticket.

        **Instructions**
        1.  Carefully read the 'New JIRA Ticket'.
        2.  Analyze the 'Historical Solutions' provided. These are from past tickets that were similar.
        3.  Synthesize the information into a clear, step-by-step guide or a set of questions to help the user solve their problem.
        4.  IMPORTANT: {approach_focus}
        5.  Keep your response concise and professional. Start with a polite opening.
        
        ---
        **New JIRA Ticket**
        ```text
        {ticket_context}
        ```
        ---
        **Historical Solutions**
        ```text
        {solutions_str}
        ```
        ---
        **Your Recommended Solution**
        """

llm_service = LLMService()
