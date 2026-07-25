from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from database import init_db
from routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Server shutting down")

app = FastAPI(
    title="AI Voice Agent - Appointment Booking",
    description="MediBook Clinic AI receptionist that books appointments via voice",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router)

@app.get("/")
def root():
    return {
        "status": "running",
        "message": "AI Voice Agent is live",
        "endpoints": {
            "POST /webhook": "Vapi sends conversation events here",
            "GET /appointments": "View all booked appointments",
            "DELETE /appointments/{id}": "Cancel an appointment"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
