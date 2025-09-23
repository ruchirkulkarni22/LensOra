# File: backend/config.py
import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Settings:
    # Database settings
    DB_USER = os.getenv("DB_USER", "lensora")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "lensora")
    DB_HOST = os.getenv("DB_HOST", "localhost") 
    DB_PORT = os.getenv("DB_PORT", "5433")      
    DB_NAME = os.getenv("DB_NAME", "lensora")
    
    @property
    def DATABASE_URL(self):
        host = self.DB_HOST
        # This logic is for docker-compose vs local running
        if host == "postgres" and os.environ.get("DOCKER_ENV") != "true":
            host = "localhost"
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{host}:{self.DB_PORT}/{self.DB_NAME}"

    # Temporal settings
    TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost")
    TEMPORAL_PORT = int(os.getenv("TEMPORAL_PORT", 7233))
    TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")

    # JIRA settings
    JIRA_URL = os.getenv("JIRA_URL")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
    JIRA_AGENT_USER_ACCOUNT_ID = os.getenv("JIRA_AGENT_USER_ACCOUNT_ID")
    
    # LLM API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # --- FEATURE 1.1.3 ENHANCEMENT ---
    # Fallback chain for LLM providers. The service will try them in this order.
    # We can add more models here in the future.
    LLM_FALLBACK_CHAIN: List[str] = [
        # "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemma-3-27b-it",
        # add openAI models after adding API key
    ]


settings = Settings()

