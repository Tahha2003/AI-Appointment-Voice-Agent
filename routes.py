"""
FastAPI Routes

POST /webhook      ← Vapi calls this on every conversation event
GET  /appointments ← View all booked appointments
DELETE /appointments/{id} ← Cancel an appointment
POST /chat         ← Manual testing without Vapi (text-based)
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json

from agent import chat
from database import get_all_appointments, cancel_appointment

router = APIRouter()

# In-memory session store: call_id → conversation history
# In production you'd use Redis or a DB table
sessions: dict = {}


# ─────────────────────────────────────────────
# VAPI WEBHOOK ENDPOINT
# Vapi sends events here during a phone call.
# Event types we care about:
#   - assistant-request  → Vapi asking for assistant config
#   - function-call      → (handled inside agent.py via OpenAI tool calling)
#   - end-of-call-report → call finished
# ─────────────────────────────────────────────
@router.post("/webhook")
async def vapi_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    message = body.get("message", {})
    event_type = message.get("type", "")
    call_id = message.get("call", {}).get("id", "default")
    
    print(f"\n📞 Vapi Event: {event_type} | Call: {call_id}")
    
    # ── 1. assistant-request ──────────────────
    # Vapi asks: "Who is this assistant? What should it say first?"
    if event_type == "assistant-request":
        return JSONResponse({
            "assistant": {
                "firstMessage": "Hello! Welcome to CareCloud Medical Clinic. I'm your AI receptionist. How can I help you today?",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "systemPrompt": (
                        "You are a friendly AI receptionist for CareCloud Medical Clinic. "
                        "Help patients book appointments. Keep responses under 2 sentences. "
                        "Ask: name, phone, reason, date, time. Confirm then book."
                    ),
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "book_appointment",
                                "description": "Book appointment after collecting all info",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "patient_name": {"type": "string"},
                                        "phone": {"type": "string"},
                                        "reason": {"type": "string"},
                                        "date": {"type": "string"},
                                        "time": {"type": "string"}
                                    },
                                    "required": ["patient_name", "phone", "reason", "date", "time"]
                                }
                            },
                            "server": {
                                "url": "https://ai-appointment-voice-agent.onrender.com/vapi-function"
                            }
                        }
                    ]
                },
                "voice": {
                    "provider": "11labs",
                    "voiceId": "paula"
                }
            }
        })
    
    # ── 2. function-call ──────────────────────
    # Vapi sends this when the AI decided to call book_appointment
    if event_type == "function-call":
        func = message.get("functionCall", {})
        func_name = func.get("name", "")
        parameters = func.get("parameters", {})
        
        print(f"🔧 Function call from Vapi: {func_name}")
        print(f"   Params: {json.dumps(parameters, indent=2)}")
        
        if func_name == "book_appointment":
            from database import save_appointment
            appointment_id = save_appointment(
                patient_name=parameters.get("patient_name", "Unknown"),
                phone=parameters.get("phone", ""),
                reason=parameters.get("reason", ""),
                date=parameters.get("date", ""),
                time=parameters.get("time", ""),
                doctor="Dr. Smith"
            )
            return JSONResponse({
                "result": f"Appointment booked! Your confirmation ID is {appointment_id}. We look forward to seeing you."
            })
        
        return JSONResponse({"result": "Function not recognized."})
    
    # ── 3. end-of-call-report ─────────────────
    if event_type == "end-of-call-report":
        duration = message.get("durationSeconds", 0)
        print(f"📴 Call ended. Duration: {duration}s")
        # Clean up session
        sessions.pop(call_id, None)
        return JSONResponse({"status": "ok"})
    
    # ── Default: acknowledge ──────────────────
    return JSONResponse({"status": "received", "type": event_type})


# ─────────────────────────────────────────────
# VAPI FUNCTION SERVER ENDPOINT
# When Vapi's model calls book_appointment, 
# it posts to this URL (configured in assistant tools above)
# ─────────────────────────────────────────────
@router.post("/vapi-debug")
async def vapi_debug(request: Request):
    """Temporary debug endpoint — logs exactly what Vapi sends."""
    body = await request.json()
    print(f"🔍 VAPI DEBUG BODY: {json.dumps(body, indent=2)}")
    return JSONResponse({"received": body})


async def vapi_function_server(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    print(f"📥 Vapi-function raw body: {json.dumps(body)[:500]}")

    # Vapi sends tool calls in different formats — handle all of them
    func_name = ""
    parameters = {}

    # Format 1: {"message": {"type": "function-call", "functionCall": {...}}}
    message = body.get("message", {})
    if message:
        func = message.get("functionCall", {})
        func_name = func.get("name", "")
        parameters = func.get("parameters", {})

    # Format 2: {"toolCallList": [{"function": {"name": ..., "arguments": ...}}]}
    if not func_name:
        tool_calls = body.get("toolCallList", [])
        if tool_calls:
            fn = tool_calls[0].get("function", {})
            func_name = fn.get("name", "")
            args = fn.get("arguments", {})
            parameters = json.loads(args) if isinstance(args, str) else args

    # Format 3: direct {"name": ..., "parameters": ...}
    if not func_name:
        func_name = body.get("name", "")
        parameters = body.get("parameters", body.get("arguments", {}))
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except Exception:
                parameters = {}

    # Format 4: Vapi new format {"type":"tool-calls","toolCallList":[...]}
    if not func_name:
        tool_call_list = body.get("toolCallList", [])
        if not tool_call_list:
            tool_call_list = body.get("tool_call_list", [])
        for tc in tool_call_list:
            fn = tc.get("function", {})
            if fn.get("name") == "book_appointment":
                func_name = fn.get("name", "")
                args = fn.get("arguments", {})
                parameters = json.loads(args) if isinstance(args, str) else args
                break

    print(f"🔧 Function: {func_name}")
    print(f"   Parameters: {json.dumps(parameters, indent=2)}")

    if func_name == "book_appointment":
        from database import save_appointment

        # Validate all required fields are present and non-empty
        required = ["patient_name", "phone", "reason", "date", "time"]
        missing = [f for f in required if not parameters.get(f, "").strip()]

        if missing:
            print(f"⚠️ Missing fields: {missing} — not saving")
            return JSONResponse({
                "result": f"Please collect the following information first: {', '.join(missing)}"
            })

        appointment_id = save_appointment(
            patient_name=parameters.get("patient_name", "Unknown"),
            phone=parameters.get("phone", ""),
            reason=parameters.get("reason", ""),
            date=parameters.get("date", ""),
            time=parameters.get("time", ""),
            doctor="Dr. Smith"
        )
        return JSONResponse({
            "result": f"Your appointment has been confirmed! Booking ID: {appointment_id}. See you soon."
        })

    return JSONResponse({"result": "Unknown function"})


# ─────────────────────────────────────────────
# TEXT CHAT ENDPOINT (Testing without Vapi)
# Use this to test the AI locally via curl or Postman
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str = "test-session"
    message: str

@router.post("/chat")
async def text_chat(req: ChatRequest):
    """
    Test the AI brain without making a real phone call.
    Send messages here and see how the AI responds.
    """
    session_id = req.session_id
    
    # Get or create session history
    if session_id not in sessions:
        sessions[session_id] = []
    
    history = sessions[session_id]
    
    # Add user message to history
    history.append({"role": "user", "content": req.message})
    
    # Get AI response
    result = chat(history)
    
    # Add AI response to history
    history.append({"role": "assistant", "content": result["reply"]})
    
    # Keep history in sessions
    sessions[session_id] = history
    
    return {
        "session_id": session_id,
        "user_message": req.message,
        "ai_reply": result["reply"],
        "function_called": result["function_called"],
        "function_name": result["function_name"],
        "function_args": result["function_args"],
        "conversation_turns": len(history) // 2
    }


@router.delete("/chat/{session_id}")
def clear_session(session_id: str):
    """Clear a conversation session (start fresh)."""
    sessions.pop(session_id, None)
    return {"message": f"Session '{session_id}' cleared"}


# ─────────────────────────────────────────────
# APPOINTMENTS ENDPOINTS
# ─────────────────────────────────────────────
@router.get("/appointments")
def list_appointments():
    """View all booked appointments."""
    appointments = get_all_appointments()
    return {
        "total": len(appointments),
        "appointments": appointments
    }

@router.delete("/appointments/{appointment_id}")
def cancel(appointment_id: int):
    """Cancel an appointment."""
    success = cancel_appointment(appointment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": f"Appointment {appointment_id} cancelled successfully"}
