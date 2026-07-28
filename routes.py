"""
routes.py — All API endpoints

/patients          → Full CRUD (GET, POST, PUT, DELETE/soft)
/webhook           → Vapi call events
/vapi-function     → Vapi tool execution (register_patient, update_patient)
/chat              → Text-based testing (no phone needed)
"""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import json

from agent import chat
from database import (
    get_all_patients, get_patient_by_id, create_patient,
    update_patient, soft_delete_patient, get_patient_by_phone,
    validate_patient_data
)

router = APIRouter()

# In-memory sessions: call_id → conversation history
sessions: dict = {}

BACKEND_URL = "https://ai-appointment-voice-agent.onrender.com"


# ═══════════════════════════════════════════════════════════════
# HELPER — consistent response envelope
# ═══════════════════════════════════════════════════════════════
def ok(data, status_code: int = 200):
    return JSONResponse({"data": data, "error": None}, status_code=status_code)


def err(message: str, status_code: int = 400):
    return JSONResponse({"data": None, "error": message}, status_code=status_code)


# ═══════════════════════════════════════════════════════════════
# PATIENTS — REST API
# ═══════════════════════════════════════════════════════════════

@router.get("/patients")
def list_patients(
    last_name:      Optional[str] = Query(None),
    date_of_birth:  Optional[str] = Query(None),
    phone_number:   Optional[str] = Query(None)
):
    """
    GET /patients
    List all active patients.
    Optional filters: ?last_name= ?date_of_birth= ?phone_number=
    """
    patients = get_all_patients(
        last_name=last_name,
        date_of_birth=date_of_birth,
        phone_number=phone_number
    )
    return ok({"total": len(patients), "patients": patients})


@router.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    """
    GET /patients/:id
    Retrieve a single patient by UUID.
    Returns 404 if not found or soft-deleted.
    """
    patient = get_patient_by_id(patient_id)
    if not patient:
        return err("Patient not found", 404)
    return ok(patient)


@router.post("/patients")
async def create_patient_endpoint(request: Request):
    """
    POST /patients
    Create a new patient record.
    Returns 201 on success, 409 on duplicate phone, 422 on validation error.
    """
    try:
        body = await request.json()
    except Exception:
        return err("Invalid JSON body", 400)

    # Check for duplicate phone number
    phone_raw = body.get("phone_number", "")
    if phone_raw:
        import re
        phone_digits = re.sub(r"\D", "", str(phone_raw))
        existing = get_patient_by_phone(phone_digits)
        if existing:
            return JSONResponse(
                {
                    "data": existing,
                    "error": "A patient with this phone number already exists",
                    "duplicate": True
                },
                status_code=409
            )

    # Validate all required fields
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
    """
    PUT /patients/:id
    Partial update — only provided fields are updated.
    Returns 404 if patient not found.
    """
    try:
        body = await request.json()
    except Exception:
        return err("Invalid JSON body", 400)

    existing = get_patient_by_id(patient_id)
    if not existing:
        return err("Patient not found", 404)

    # Validate only the fields being updated (required_only=True)
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
    """
    DELETE /patients/:id
    Soft-delete — sets deleted_at timestamp, does NOT remove row.
    Returns 404 if not found.
    """
    existing = get_patient_by_id(patient_id)
    if not existing:
        return err("Patient not found", 404)

    success = soft_delete_patient(patient_id)
    if not success:
        return err("Could not delete patient", 500)

    return ok({"message": f"Patient {patient_id} deleted successfully"})


# ═══════════════════════════════════════════════════════════════
# VAPI WEBHOOK
# Receives all call lifecycle events from Vapi.
# ═══════════════════════════════════════════════════════════════

@router.post("/webhook")
async def vapi_webhook(request: Request):
    """
    POST /webhook
    Vapi sends all call events here.
    Events handled:
      - assistant-request  → return assistant config
      - function-call      → legacy function call handling
      - end-of-call-report → cleanup session
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message = body.get("message", {})
    event_type = message.get("type", "")
    call_id = message.get("call", {}).get("id", "default")

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
                "voice": {
                    "provider": "vapi",
                    "voiceId": "Elliot"
                }
            }
        })

    # ── function-call (legacy Vapi format) ────────────────
    if event_type == "function-call":
        func = message.get("functionCall", {})
        func_name = func.get("name", "")
        parameters = func.get("parameters", {})
        print(f"🔧 Legacy function call: {func_name} | params: {parameters}")
        result = _execute_vapi_function(func_name, parameters)
        return JSONResponse({"result": result})

    # ── end-of-call-report ────────────────────────────────
    if event_type == "end-of-call-report":
        duration = message.get("durationSeconds", 0)
        print(f"📴 Call ended. Duration: {duration}s | Call: {call_id}")
        sessions.pop(call_id, None)
        return JSONResponse({"status": "ok"})

    return JSONResponse({"status": "received", "type": event_type})


# ═══════════════════════════════════════════════════════════════
# VAPI FUNCTION SERVER
# Vapi calls this URL when the AI triggers a tool.
# Handles all Vapi request formats.
# ═══════════════════════════════════════════════════════════════

@router.post("/vapi-function")
async def vapi_function_server(request: Request):
    """
    POST /vapi-function
    Vapi sends tool call data here.
    Supports multiple Vapi request formats for compatibility.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    print(f"📥 Vapi function body: {json.dumps(body)[:600]}")

    func_name, parameters = _extract_vapi_function(body)

    if not func_name:
        print("⚠️  Could not extract function name from Vapi payload")
        return JSONResponse({"result": "Could not process the request"})

    print(f"🔧 Executing: {func_name}")
    print(f"   Parameters: {json.dumps(parameters, indent=2)}")

    result = _execute_vapi_function(func_name, parameters)
    return JSONResponse({"result": result})


def _extract_vapi_function(body: dict) -> tuple[str, dict]:
    """
    Extract function name and parameters from any Vapi payload format.
    Vapi has changed its format across versions — handle all of them.
    """
    func_name = ""
    parameters = {}

    # Format 1: {"message": {"functionCall": {"name": ..., "parameters": {...}}}}
    message = body.get("message", {})
    if message:
        fc = message.get("functionCall", {})
        if fc.get("name"):
            func_name = fc["name"]
            parameters = fc.get("parameters", {})
            return func_name, parameters

    # Format 2: {"toolCallList": [{"function": {"name": ..., "arguments": ...}}]}
    tool_calls = body.get("toolCallList", [])
    if tool_calls:
        fn = tool_calls[0].get("function", {})
        if fn.get("name"):
            func_name = fn["name"]
            args = fn.get("arguments", {})
            parameters = json.loads(args) if isinstance(args, str) else args
            return func_name, parameters

    # Format 3: direct {"name": ..., "parameters": {...}}
    if body.get("name"):
        func_name = body["name"]
        parameters = body.get("parameters", body.get("arguments", {}))
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except Exception:
                parameters = {}
        return func_name, parameters

    return func_name, parameters


def _execute_vapi_function(func_name: str, parameters: dict) -> str:
    """
    Execute the requested function and return a string result
    that Vapi will speak back to the caller.
    """
    if func_name == "register_patient":
        # Duplicate check
        import re
        phone_raw = parameters.get("phone_number", "")
        phone_digits = re.sub(r"\D", "", str(phone_raw))
        existing = get_patient_by_phone(phone_digits)

        if existing:
            return (
                f"It looks like we already have a record for "
                f"{existing['first_name']} {existing['last_name']} with that phone number. "
                f"Would you like to update your existing information instead? "
                f"If yes, I'll need your patient ID: {existing['patient_id']}"
            )

        cleaned, errors = validate_patient_data(parameters)
        if errors:
            return f"I need to correct some information: {'; '.join(errors)}"

        try:
            patient = create_patient(cleaned)
            return (
                f"You're all set, {patient['first_name']}! "
                f"Your registration is complete. Your patient ID is "
                f"{patient['patient_id'][:8]}. Have a great day!"
            )
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return "I'm sorry, there was an error saving your registration. Please call back and try again."

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

    return "I'm sorry, I didn't understand that request."


# ═══════════════════════════════════════════════════════════════
# TEXT CHAT (local testing without phone)
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    session_id: str = "test-session"
    message: str


@router.post("/chat")
async def text_chat(req: ChatRequest):
    """
    POST /chat
    Test the AI agent via text — no phone call needed.
    Maintains conversation history per session_id.
    """
    session_id = req.session_id
    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]
    history.append({"role": "user", "content": req.message})

    result = chat(history)
    history.append({"role": "assistant", "content": result["reply"]})
    sessions[session_id] = history

    return ok({
        "session_id": session_id,
        "user_message": req.message,
        "ai_reply": result["reply"],
        "function_called": result["function_called"],
        "function_name": result["function_name"],
        "function_result": result["function_result"],
        "conversation_turns": len([m for m in history if m["role"] == "user"])
    })


@router.delete("/chat/{session_id}")
def clear_session(session_id: str):
    """DELETE /chat/:id — clear a conversation session."""
    sessions.pop(session_id, None)
    return ok({"message": f"Session '{session_id}' cleared"})


# ═══════════════════════════════════════════════════════════════
# VAPI ASSISTANT CONFIG HELPERS
# These are used when Vapi sends an assistant-request event.
# The system prompt and tools are defined here so they stay
# in sync with agent.py definitions.
# ═══════════════════════════════════════════════════════════════

def _vapi_system_prompt() -> str:
    """System prompt for Vapi-managed assistant."""
    return (
        "You are a professional AI patient intake coordinator for MediBook Clinic. "
        "Register new patients by collecting their information conversationally. "
        "Required fields in order: first name, last name, date of birth (MM/DD/YYYY), "
        "sex (Male/Female/Other/Decline to Answer), phone number (10-digit US), "
        "street address, city, state (2-letter), ZIP code. "
        "Then offer optional: insurance info, emergency contact, preferred language. "
        "Always read back all information and confirm before calling register_patient. "
        "Keep responses to 1-2 sentences. Ask ONE question at a time. "
        "If phone number matches existing patient, offer to update their record instead."
    )


def _vapi_tools() -> list:
    """Tool definitions for Vapi-managed assistant."""
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
                        "sex":                     {"type": "string", "description": "Male, Female, Other, or Decline to Answer"},
                        "phone_number":            {"type": "string", "description": "10-digit US phone"},
                        "address_line_1":          {"type": "string"},
                        "address_line_2":          {"type": "string"},
                        "city":                    {"type": "string"},
                        "state":                   {"type": "string", "description": "2-letter US state"},
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
            "server": {"url": f"{BACKEND_URL}/vapi-function"}
        },
        {
            "type": "function",
            "function": {
                "name": "update_patient",
                "description": "Update an existing patient record. Requires patient_id.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "patient_id":              {"type": "string", "description": "UUID of existing patient"},
                        "first_name":              {"type": "string"},
                        "last_name":               {"type": "string"},
                        "date_of_birth":           {"type": "string"},
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
                    "required": ["patient_id"]
                }
            },
            "server": {"url": f"{BACKEND_URL}/vapi-function"}
        }
    ]
