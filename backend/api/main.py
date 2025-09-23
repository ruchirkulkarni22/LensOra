# File: backend/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from . import routes
from backend.services.polling_service import polling_service
# --- FIX: Import the shared state instead of defining it here ---
from .shared_state import POLLING_LOGS

app = FastAPI(
    title="LensOraAI",
    description="AI-powered integration agent for Oracle ERP and JIRA.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Application startup: Creating background task for JIRA polling.")
    # Pass the deque to the polling service so it can add logs
    asyncio.create_task(polling_service.start_polling(POLLING_LOGS))

app.include_router(routes.router)

@app.get("/")
async def root():
    return {"message": "LensOraAI is running!"}

