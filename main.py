"""
main.py — FastAPI entry point
MediBook Clinic — Voice AI Patient Registration System
"""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import uvicorn
import os

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
        "dashboard": "/dashboard",
        "endpoints": {
            "GET  /dashboard":            "Web UI — patient dashboard",
            "GET  /patients":             "List all patients",
            "GET  /patients/{id}":        "Get patient by UUID",
            "POST /patients":             "Create new patient",
            "PUT  /patients/{id}":        "Update patient (partial)",
            "DELETE /patients/{id}":      "Soft-delete patient",
            "GET  /appointments":         "List all appointments",
            "GET  /transcripts":          "List all call transcripts",
            "POST /webhook":              "Vapi call events",
            "POST /vapi-function":        "Vapi tool execution",
            "POST /chat":                 "Text-based testing",
        }
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """Serve the patient management dashboard."""
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
