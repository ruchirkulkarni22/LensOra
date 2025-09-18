# File: backend/api/main.py
from fastapi import FastAPI
# Import the router we just created
from . import routes

app = FastAPI(
    title="LensOraAI",
    description="AI-powered integration agent for Oracle ERP and JIRA.",
    version="0.1.0",
)

# Include the API routes in the main application
app.include_router(routes.router)

@app.get("/")
async def root():
    return {"message": "LensOraAI is running!"}

