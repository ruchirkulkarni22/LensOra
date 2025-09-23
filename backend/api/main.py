# File: backend/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from . import routes
# --- FEATURE 1.1.5 ENHANCEMENT ---
from backend.services.polling_service import polling_service

app = FastAPI(
    title="LensOraAI",
    description="AI-powered integration agent for Oracle ERP and JIRA.",
    version="0.1.0",
)

# Add CORS middleware to allow frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Application startup: Creating background task for JIRA polling.")
    asyncio.create_task(polling_service.start_polling())

app.include_router(routes.router)

@app.get("/")
async def root():
    return {"message": "LensOraAI is running!"}
