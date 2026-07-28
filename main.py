"""
main.py — FastAPI entry point
MediBook Clinic — Voice AI Patient Registration System
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

from database import init_db
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    print("✅ Database initialized")
    print("🚀 MediBook Voice Agent is ready")
    yield
    # Shutdown
    print("👋 Server shutting down")


app = FastAPI(
    title="MediBook Voice Agent — Patient Registration",
    description=(
        "AI-powered voice agent that registers patients via natural phone conversation. "
        "Built with Vapi (telephony), Groq Llama 3.3 (LLM), FastAPI (backend), SQLite (database)."
    ),
    version="2.0.0",
    lifespan=lifespan
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "MediBook Voice Agent — Patient Registration",
        "version": "2.0.0",
        "endpoints": {
            "GET  /patients":             "List all patients (filter by last_name, date_of_birth, phone_number)",
            "GET  /patients/{id}":        "Get patient by UUID",
            "POST /patients":             "Create new patient",
            "PUT  /patients/{id}":        "Update patient (partial)",
            "DELETE /patients/{id}":      "Soft-delete patient",
            "POST /webhook":              "Vapi call events",
            "POST /vapi-function":        "Vapi tool execution",
            "POST /chat":                 "Text-based testing (no phone needed)",
        }
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
