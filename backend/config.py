# File: backend/config.py
import os
from dotenv import load_dotenv

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

    # Email settings
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    
    # NEW: Gemini API Key
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

settings = Settings()

