# File: testing/test_validation_agent.py
#
# This is a standalone script to test individual services without running the full Temporal workflow.
# It helps in debugging the JIRA connection, OCR, DB queries, and the LLM prompt.
#
# To Run:
# 1. Make sure your .env file is in the root 'Code' directory.
# 2. Ensure your Docker containers (lensora_db, temporal) are running.
# 3. From the root 'Code' directory, run: python -m testing.test_validation_agent

import os
import sys

# Add the project root to the Python path to allow for absolute imports
# This line is crucial for finding the 'backend' module when run from the root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.services.db_service import db_service
from backend.services.jira_client import jira_service
from backend.services.ocr_service import ocr_service
from backend.services.llm_service import llm_service

# --- CONFIGURATION ---
# IMPORTANT: Change this to a real JIRA ticket key in your instance for testing
TEST_TICKET_KEY = "LENS-14" 

def test_db_service():
    print("\n--- Testing Database Service ---")
    try:
        knowledge = db_service.get_all_modules_with_fields()
        assert "AP.Invoice" in knowledge
        assert "PO.Creation" in knowledge
        print("✅ Success: Fetched module knowledge from the database.")
        print(knowledge)
        return knowledge
    except Exception as e:
        print(f"❌ Failure: Could not fetch data from the database. Error: {e}")
        return None

def test_jira_and_ocr_services():
    print("\n--- Testing JIRA and OCR Services ---")
    text_parts = []
    try:
        print(f"Fetching ticket {TEST_TICKET_KEY} from JIRA...")
        details = jira_service.get_ticket_details(TEST_TICKET_KEY)
        text_parts.append(f"Summary: {details['summary']}")
        text_parts.append(f"Description: {details['description']}")
        print("✅ Success: Fetched ticket details.")
        
        for attachment in details["attachments"]:
            print(f"Downloading and processing attachment: {attachment['filename']}...")
            content = jira_service.download_attachment(attachment['url'])
            text = ocr_service.extract_text_from_bytes(content, attachment['mimeType'])
            text_parts.append(f"--- Attachment: {attachment['filename']} ---\n{text}")
            print(f"✅ Success: Processed attachment {attachment['filename']}.")

        bundle = "\n".join(text_parts)
        print("\n--- Full Text Bundle ---")
        print(bundle)
        print("------------------------")
        return bundle
            
    except Exception as e:
        print(f"❌ Failure: Could not process JIRA ticket. Error: {e}")
        return None

def test_llm_service(bundle, knowledge):
    print("\n--- Testing LLM Service ---")
    if not bundle or not knowledge:
        print("❌ Skipping LLM test due to previous errors.")
        return
    try:
        verdict = llm_service.get_validation_verdict(bundle, knowledge)
        print("\n--- LLM Verdict ---")
        print(verdict)
        print("-------------------")
        assert "detected_module" in verdict
        assert "validation_status" in verdict
        print("✅ Success: Received a valid JSON verdict from the LLM.")
    except Exception as e:
        print(f"❌ Failure: LLM service failed. Error: {e}")


if __name__ == "__main__":
    print("🚀 Starting LensOraAI Service Integration Test 🚀")
    
    # Run the tests
    module_knowledge = test_db_service()
    ticket_bundle = test_jira_and_ocr_services()
    test_llm_service(ticket_bundle, module_knowledge)

    print("\n🏁 Test run finished. 🏁")

