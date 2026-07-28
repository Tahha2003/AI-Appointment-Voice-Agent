"""
routes.py — All API endpoints

/patients          → Full CRUD
/appointments      → Schedule + list appointments (bonus)
/transcripts       → Call transcripts (bonus)
/webhook           → Vapi call events
/vapi-function     → Vapi tool execution
/chat              → Text testing
"""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
import json

from agent import chat
from database import (
    get_all_patients, get_patient_by_id, create_patient,
    update_patient, soft_delete_patient, get_patient_by_phone,
    validate_patient_data,
    create_appointment, get_appointment_by_id,
    get_appointments_by_patient, get_all_appointments,
    save_transcript, get_transcripts_by_patient, get_all_transcripts
)

router = APIRouter()
sessions: dict = {}

BACKEND_URL = "https://ai-appointment-voice-agent.onrender.com"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def ok(data, status_code: int = 200):
    return JSONResponse({"data": data, "error": None}, status_code=status_code)

def err(message: str, status_code: int = 400):
    return JSONResponse({"data": None, "error": message}, status_code=status_code)


# ═══════════════════════════════════════════════════════════════
# PATIENTS — REST API
# ═══════════════════════════════════════════════════════════════

@router.get("/patients")
def list_patients(
    last_name:     Optional[str] = Query(None),
    date_of_birth: Optional[str] = Query(None),
    phone_number:  Optional[str] = Query(None)
):
    """List all active patients with optional filters."""
    patients = get_all_patients(
        last_name=last_name,
        date_of_birth=date_of_birth,
        phone_number=phone_number
    )
    return ok({"total": len(patients), "patients": patients})


@router.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    """Get single patient by UUID."""
    patient = get_patient_by_id(patient_id)
    if not patient:
        return err("Patient not found", 404)
    return ok(patient)


@router.post("/patients")
async def create_patient_endpoint(request: Request):
    """
    Create new patient.
    Returns 409 on duplicate phone, 422 on validation error.
    """
    try:
        body = await request.json()
    except Exception:
        return err("Invalid JSON body", 400)

    import re
    phone_raw = body.get("phone_number", "")
    if phone_raw:
        phone_digits = re.sub(r"\D", "", str(phone_raw))
        existing = get_patient_by_phone(phone_digits)
        if existing:
            return JSONResponse(
                {"data": existing, "error": "A patient with this phone number already exists", "duplicate": True},
                status_code=409
            )

    cleaned, errors = validate_patient_data(body)
    if errors:
        return JSONResponse(
            {"data": None, "error": "; ".join(errors), "fields": errors},
            status_code=422
        )

    try:
        patient = create_patient(cleaned)
        return ok(patient, 201)
    except Exception as e:
        return err(f"Database error: {str(e)}", 500)


@router.put("/patients/{patient_id}")
async def update_patient_endpoint(patient_id: str, request: Request):
    """Partial update — only provided fields updated."""
    try:
        body = await request.json()
    except Exception:
        return err("Invalid JSON body", 400)

    existing = get_patient_by_id(patient_id)
    if not existing:
        return err("Patient not found", 404)

    cleaned, errors = validate_patient_data(body, required_only=True)
    if errors:
        return JSONResponse(
            {"data": None, "error": "; ".join(errors), "fields": errors},
            status_code=422
        )

    try:
        updated = update_patient(patient_id, cleaned)
        return ok(updated)
    except Exception as e:
        return err(f"Database error: {str(e)}", 500)


@router.delete("/patients/{patient_id}")
def delete_patient_endpoint(patient_id: str):
    """Soft-delete — sets deleted_at, does NOT remove row."""
    if not get_patient_by_id(patient_id):
        return err("Patient not found", 404)
    if not soft_delete_patient(patient_id):
        return err("Could not delete patient", 500)
    return ok({"message": f"Patient {patient_id} deleted successfully"})


# ═══════════════════════════════════════════════════════════════
# APPOINTMENTS — REST API (bonus)
# ═══════════════════════════════════════════════════════════════

@router.get("/appointments")
def list_all_appointments():
    """List all appointments (with patient name joined)."""
    appointments = get_all_appointments()
    return ok({"total": len(appointments), "appointments": appointments})


@router.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: str):
    """Get single appointment by UUID."""
    appt = get_appointment_by_id(appointment_id)
    if not appt:
        return err("Appointment not found", 404)
    return ok(appt)


@router.get("/patients/{patient_id}/appointments")
def list_patient_appointments(patient_id: str):
    """List all appointments for a specific patient."""
    if not get_patient_by_id(patient_id):
        return err("Patient not found", 404)
    appointments = get_appointments_by_patient(patient_id)
    return ok({"total": len(appointments), "appointments": appointments})


@router.post("/patients/{patient_id}/appointments")
async def create_appointment_endpoint(patient_id: str, request: Request):
    """Schedule a new appointment for a patient."""
    if not get_patient_by_id(patient_id):
        return err("Patient not found", 404)

    try:
        body = await request.json()
    except Exception:
        return err("Invalid JSON body", 400)

    try:
        appt = create_appointment(
            patient_id=patient_id,
            appointment_type=body.get("appointment_type", "General Checkup"),
            preferred_date=body.get("preferred_date"),
            preferred_time=body.get("preferred_time"),
            doctor=body.get("doctor", "To be assigned"),
            notes=body.get("notes")
        )
        return ok(appt, 201)
    except Exception as e:
        return err(f"Database error: {str(e)}", 500)


# ═══════════════════════════════════════════════════════════════
# CALL TRANSCRIPTS — REST API (bonus)
# ═══════════════════════════════════════════════════════════════

@router.get("/transcripts")
def list_all_transcripts():
    """List all call transcripts (with patient name joined)."""
    transcripts = get_all_transcripts()
    return ok({"total": len(transcripts), "transcripts": transcripts})


@router.get("/patients/{patient_id}/transcripts")
def list_patient_transcripts(patient_id: str):
    """List all transcripts for a specific patient."""
    if not get_patient_by_id(patient_id):
        return err("Patient not found", 404)
    transcripts = get_transcripts_by_patient(patient_id)
    return ok({"total": len(transcripts), "transcripts": transcripts})


@router.post("/transcripts")
async def create_transcript_endpoint(request: Request):
    """Manually save a call transcript."""
    try:
        body = await request.json()
    except Exception:
        return err("Invalid JSON body", 400)

    try:
        result = save_transcript(
            patient_id=body.get("patient_id"),
            call_id=body.get("call_id"),
            summary=body.get("summary"),
            full_transcript=body.get("full_transcript"),
            language=body.get("language", "English"),
            duration_secs=body.get("duration_secs"),
            outcome=body.get("outcome")
        )
        return ok(result, 201)
    except Exception as e:
        return err(f"Database error: {str(e)}", 500)


# ═══════════════════════════════════════════════════════════════
# VAPI WEBHOOK
# ═══════════════════════════════════════════════════════════════

@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    Receives all Vapi call lifecycle events.
    On end-of-call: saves transcript automatically.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message  = body.get("message", {})
    event_type = message.get("type", "")
    call_id  = message.get("call", {}).get("id", "default")

    print(f"\n📞 Vapi Event: {event_type} | Call: {call_id}")

    # ── assistant-request ──────────────────────────────────
    if event_type == "assistant-request":
        return JSONResponse({
            "assistant": {
                "firstMessage": "Hello! Thank you for calling MediBook Clinic. I'm here to help register you as a new patient. May I start with your first name?",
                "model": {
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "systemPrompt": _vapi_system_prompt(),
                    "tools": _vapi_tools()
                },
                "voice": {"provider": "vapi", "voiceId": "Elliot"}
            }
        })

    # ── function-call (legacy) ─────────────────────────────
    if event_type == "function-call":
        func = message.get("functionCall", {})
        result = _execute_vapi_function(func.get("name",""), func.get("parameters",{}))
        return JSONResponse({"result": result})

    # ── end-of-call — auto-save transcript ─────────────────
    if event_type == "end-of-call-report":
        duration    = message.get("durationSeconds", 0)
        transcript  = message.get("transcript", "")
        summary     = message.get("summary", "")
        ended_reason = message.get("endedReason", "")

        # Try to find patient from session
        session_data = sessions.get(call_id, {})
        patient_id   = session_data.get("patient_id")
        language     = session_data.get("language", "English")

        if transcript or summary:
            save_transcript(
                patient_id=patient_id,
                call_id=call_id,
                summary=summary or f"Call ended: {ended_reason}",
                full_transcript=transcript,
                language=language,
                duration_secs=int(duration),
                outcome=ended_reason
            )
            print(f"📝 Auto-saved transcript for call {call_id}")

        sessions.pop(call_id, None)
        return JSONResponse({"status": "ok"})

    return JSONResponse({"status": "received", "type": event_type})


# ═══════════════════════════════════════════════════════════════
# VAPI FUNCTION SERVER
# ═══════════════════════════════════════════════════════════════

@router.post("/vapi-function")
async def vapi_function_server(request: Request):
    """Executes tools called by Vapi. Handles all Vapi payload formats."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    print(f"📥 Vapi function body: {json.dumps(body)[:600]}")

    func_name, parameters = _extract_vapi_function(body)

    if not func_name:
        return JSONResponse({"result": "Could not process the request"})

    print(f"🔧 Executing: {func_name} | params: {json.dumps(parameters)[:200]}")

    # Track patient_id in session for transcript saving
    call_id = body.get("message", {}).get("call", {}).get("id", "default")
    result_str = _execute_vapi_function(func_name, parameters)
    try:
        result_obj = json.loads(result_str) if isinstance(result_str, str) else {}
        if result_obj.get("patient_id"):
            if call_id not in sessions:
                sessions[call_id] = {}
            sessions[call_id]["patient_id"] = result_obj["patient_id"]
    except Exception:
        pass

    return JSONResponse({"result": result_str})


def _extract_vapi_function(body: dict) -> tuple[str, dict]:
    """Extract function name + params from any Vapi payload format."""
    # Format 1: message.functionCall
    message = body.get("message", {})
    if message:
        fc = message.get("functionCall", {})
        if fc.get("name"):
            return fc["name"], fc.get("parameters", {})

    # Format 2: toolCallList
    tool_calls = body.get("toolCallList", [])
    if tool_calls:
        fn = tool_calls[0].get("function", {})
        if fn.get("name"):
            args = fn.get("arguments", {})
            return fn["name"], json.loads(args) if isinstance(args, str) else args

    # Format 3: direct name/parameters
    if body.get("name"):
        params = body.get("parameters", body.get("arguments", {}))
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = {}
        return body["name"], params

    return "", {}


def _execute_vapi_function(func_name: str, parameters: dict) -> str:
    """Execute function and return spoken string result."""
    import re

    if func_name == "register_patient":
        phone_raw = parameters.get("phone_number", "")
        phone_digits = re.sub(r"\D", "", str(phone_raw))
        existing = get_patient_by_phone(phone_digits)

        if existing:
            return (
                f"It looks like we already have a record for "
                f"{existing['first_name']} {existing['last_name']} with that phone number. "
                f"Would you like to update your existing information instead?"
            )

        cleaned, errors = validate_patient_data(parameters)
        if errors:
            return f"I need to correct some information: {'; '.join(errors)}"

        try:
            patient = create_patient(cleaned)
            return (
                f"You're all set, {patient['first_name']}! "
                f"Your registration is complete. "
                f"Would you also like to schedule your first appointment today?"
            )
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return "I'm sorry, there was a system error. Please call back and try again."

    elif func_name == "update_patient":
        patient_id = parameters.pop("patient_id", None)
        if not patient_id:
            return "I need your patient ID to update your record."
        existing = get_patient_by_id(patient_id)
        if not existing:
            return "I couldn't find a record with that patient ID."
        cleaned, errors = validate_patient_data(parameters, required_only=True)
        if errors:
            return f"There was an issue with the data: {'; '.join(errors)}"
        try:
            updated = update_patient(patient_id, cleaned)
            return f"Your record has been updated successfully, {updated['first_name']}. Is there anything else I can help you with?"
        except Exception as e:
            print(f"❌ Update error: {e}")
            return "I'm sorry, there was an error updating your record."

    elif func_name == "schedule_appointment":
        patient_id = parameters.get("patient_id")
        if not patient_id:
            return "I need your patient ID to schedule an appointment."
        try:
            appt = create_appointment(
                patient_id=patient_id,
                appointment_type=parameters.get("appointment_type", "General Checkup"),
                preferred_date=parameters.get("preferred_date"),
                preferred_time=parameters.get("preferred_time"),
                notes=parameters.get("notes")
            )
            return (
                f"Your appointment has been scheduled! "
                f"{appt['appointment_type']} on {appt['preferred_date']} "
                f"at {appt['preferred_time']}. We look forward to seeing you. Goodbye!"
            )
        except Exception as e:
            print(f"❌ Appointment error: {e}")
            return "I'm sorry, I couldn't schedule the appointment. Please call back."

    return "I'm sorry, I didn't understand that request."


# ═══════════════════════════════════════════════════════════════
# TEXT CHAT (testing)
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: str = "test-session"
    message: str


@router.post("/chat")
async def text_chat(req: ChatRequest):
    """Text-based AI chat — no phone needed."""
    session_id = req.session_id
    if session_id not in sessions:
        sessions[session_id] = {"history": []}

    # Support both old format (list) and new (dict with history key)
    session = sessions[session_id]
    history = session.get("history", session) if isinstance(session, dict) else session

    history.append({"role": "user", "content": req.message})
    result = chat(history)

    # Add tool messages so registration guard works
    for extra_msg in result.get("history_additions", []):
        history.append(extra_msg)

    history.append({"role": "assistant", "content": result["reply"]})

    if isinstance(sessions[session_id], dict):
        sessions[session_id]["history"] = history
    else:
        sessions[session_id] = history

    return ok({
        "session_id":      session_id,
        "user_message":    req.message,
        "ai_reply":        result["reply"],
        "language":        result.get("language", "en"),
        "function_called": result["function_called"],
        "function_name":   result["function_name"],
        "function_result": result["function_result"],
        "conversation_turns": len([m for m in history if m["role"] == "user"])
    })


@router.delete("/chat/{session_id}")
def clear_session(session_id: str):
    sessions.pop(session_id, None)
    return ok({"message": f"Session '{session_id}' cleared"})


# ═══════════════════════════════════════════════════════════════
# VAPI ASSISTANT CONFIG
# ═══════════════════════════════════════════════════════════════

def _vapi_system_prompt() -> str:
    return (
        "You are a professional AI patient intake coordinator for MediBook Clinic. "
        "Register new patients conversationally. "
        "If caller says 'Hablo español', switch to Spanish immediately. "
        "Required fields in order: first name, last name, date of birth (MM/DD/YYYY), "
        "sex (Male/Female/Other/Decline to Answer), phone (10-digit US), "
        "street address, city, state (2-letter), ZIP. "
        "Offer optional: insurance, emergency contact, preferred language. "
        "Confirm all info before calling register_patient. "
        "After registration, offer to schedule first appointment. "
        "Keep responses 1-2 sentences. One question at a time."
    )


def _vapi_tools() -> list:
    base_url = f"{BACKEND_URL}/vapi-function"
    return [
        {
            "type": "function",
            "function": {
                "name": "register_patient",
                "description": "Register a new patient after collecting and confirming all required fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "first_name":              {"type": "string"},
                        "last_name":               {"type": "string"},
                        "date_of_birth":           {"type": "string", "description": "MM/DD/YYYY"},
                        "sex":                     {"type": "string"},
                        "phone_number":            {"type": "string"},
                        "address_line_1":          {"type": "string"},
                        "address_line_2":          {"type": "string"},
                        "city":                    {"type": "string"},
                        "state":                   {"type": "string"},
                        "zip_code":                {"type": "string"},
                        "email":                   {"type": "string"},
                        "insurance_provider":      {"type": "string"},
                        "insurance_member_id":     {"type": "string"},
                        "preferred_language":      {"type": "string"},
                        "emergency_contact_name":  {"type": "string"},
                        "emergency_contact_phone": {"type": "string"}
                    },
                    "required": [
                        "first_name", "last_name", "date_of_birth", "sex",
                        "phone_number", "address_line_1", "city", "state", "zip_code"
                    ]
                }
            },
            "server": {"url": base_url}
        },
        {
            "type": "function",
            "function": {
                "name": "update_patient",
                "description": "Update existing patient record. Requires patient_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id":              {"type": "string"},
                        "first_name":              {"type": "string"},
                        "last_name":               {"type": "string"},
                        "date_of_birth":           {"type": "string"},
                        "sex":                     {"type": "string"},
                        "phone_number":            {"type": "string"},
                        "address_line_1":          {"type": "string"},
                        "city":                    {"type": "string"},
                        "state":                   {"type": "string"},
                        "zip_code":                {"type": "string"},
                        "email":                   {"type": "string"},
                        "preferred_language":      {"type": "string"},
                        "emergency_contact_name":  {"type": "string"},
                        "emergency_contact_phone": {"type": "string"}
                    },
                    "required": ["patient_id"]
                }
            },
            "server": {"url": base_url}
        },
        {
            "type": "function",
            "function": {
                "name": "schedule_appointment",
                "description": "Schedule first appointment after successful registration.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id":       {"type": "string"},
                        "appointment_type": {"type": "string",
                                            "description": "General Checkup, Follow-up, Consultation, Lab Work, Vaccination, Specialist Referral, Other"},
                        "preferred_date":   {"type": "string"},
                        "preferred_time":   {"type": "string"},
                        "notes":            {"type": "string"}
                    },
                    "required": ["patient_id", "appointment_type", "preferred_date", "preferred_time"]
                }
            },
            "server": {"url": base_url}
        }
    ]
