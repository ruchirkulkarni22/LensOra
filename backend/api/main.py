# File: backend/api/main.py
from fastapi import FastAPI
import asyncio
from . import routes
# --- FEATURE 1.1.5 ENHANCEMENT ---
from backend.services.polling_service import polling_service

app = FastAPI(
    title="LensOraAI",
    description="AI-powered integration agent for Oracle ERP and JIRA.",
    version="0.1.0",
)

# --- FEATURE 1.1.5 ENHANCEMENT ---
# This event handler will run when the FastAPI application starts.
# It creates a background task to run our polling service indefinitely.
@app.on_event("startup")
async def startup_event():
    print("Application startup: Creating background task for JIRA polling.")
    asyncio.create_task(polling_service.start_polling())

app.include_router(routes.router)

@app.get("/")
async def root():
    return {"message": "LensOraAI is running!"}
