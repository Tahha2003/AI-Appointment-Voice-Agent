"""
agent.py — Groq-powered patient registration voice agent

LLM   : Groq llama-3.3-70b-versatile (free tier)
Tools : register_patient(), update_patient(), schedule_appointment()

Bonus features:
  - Appointment scheduling after registration
  - Multi-language: switches to Spanish if caller says "Hablo español"
  - history_additions returned so caller can track tool messages
"""
import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from database import (
    create_patient, update_patient as db_update_patient,
    get_patient_by_phone, validate_patient_data,
    create_appointment, APPOINTMENT_TYPES
)

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
_client = None  # lazy init — avoids crash on startup if key not yet loaded

def _get_client():
    """Return Groq client, initializing on first use."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Add it to your .env file or Render environment variables."
            )
        _client = Groq(api_key=api_key)
        print(f"🤖 Using Groq ({MODEL}) - free tier")
    return _client


# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPTS — English + Spanish
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT_EN = """You are a friendly, professional AI patient intake coordinator for MediBook Clinic.
Your job is to register new patients and schedule their first appointment through natural conversation.

== LANGUAGE DETECTION ==
If the caller says "Hablo español", "en español", or any Spanish phrase at ANY point,
immediately switch ALL your responses to Spanish for the rest of the conversation.

== REQUIRED FIELDS (collect in this exact order) ==
1. first_name         — alphabetic only, hyphens/apostrophes/spaces allowed
2. last_name          — same rules as first_name
3. date_of_birth      — ask in MM/DD/YYYY format; must NOT be today or future
4. sex                — must be exactly one of: Male, Female, Other, Decline to Answer
5. phone_number       — US 10-digit number (e.g. 555-123-4567 or 5551234567)
6. address_line_1     — street address
7. city               — city name
8. state              — 2-letter US state abbreviation (e.g. NY, CA, TX)
9. zip_code           — 5-digit or ZIP+4 format (e.g. 10001 or 10001-1234)

== OPTIONAL FIELDS ==
After required fields, say:
"I can also collect your insurance information, emergency contact, and preferred language. Would you like to provide any of those?"
If yes, collect whichever ones they want:
- insurance_provider, insurance_member_id
- emergency_contact_name, emergency_contact_phone
- preferred_language (default: English)

== CONFIRMATION ==
Read back ALL collected info and ask:
"Does everything look correct, or would you like to change anything?"
If corrections needed → re-collect ONLY that field, then re-confirm.
If confirmed → call register_patient().

== APPOINTMENT SCHEDULING (BONUS) ==
After successful registration, say:
"Great! Would you also like to schedule your first appointment with us today?"
If YES:
  - Ask: "What type of appointment do you need?" (General Checkup, Follow-up, Consultation, Lab Work, Vaccination, Specialist Referral, or Other)
  - Ask: "What date works for you?"
  - Ask: "And what time would you prefer?"
  - Then call schedule_appointment() with the patient_id from registration.
If NO: say goodbye warmly.

== VALIDATION RULES ==
- date_of_birth future: "That date appears to be in the future — could you confirm your date of birth?"
- phone_number < 10 digits: "I need a 10-digit US phone number. Could you repeat that?"
- state invalid: "Could you give me the 2-letter state abbreviation? For example, NY for New York."
- sex invalid: "For sex, I can record Male, Female, Other, or Decline to Answer — which applies?"

== DUPLICATE HANDLING ==
If register_patient returns duplicate_found=true:
Say: "It looks like we already have a record for [first_name] [last_name] with that phone number.
Would you like to update your existing information instead?"
If yes → call update_patient() with existing patient_id.
If no → ask if they want a different phone number.

== RULES ==
- Keep ALL responses SHORT — 1-2 sentences. This is a voice call.
- Ask ONE question at a time. Never combine questions.
- Be warm, professional, human-like.
- Call register_patient ONLY ONCE. Never call it again after success.
- After successful registration say: "You're all set, [first_name]! Your registration is complete."
- Then offer appointment scheduling.
"""

SYSTEM_PROMPT_ES = """Eres un coordinador de atención al paciente de MediBook Clinic, amable y profesional.
Tu trabajo es registrar nuevos pacientes y programar su primera cita a través de una conversación natural.
HABLA SIEMPRE EN ESPAÑOL.

== CAMPOS REQUERIDOS (recopilar en este orden exacto) ==
1. first_name         — solo letras, guiones, apóstrofes y espacios permitidos
2. last_name          — mismas reglas que first_name
3. date_of_birth      — formato MM/DD/AAAA; NO debe ser hoy ni en el futuro
4. sex                — exactamente uno de: Male, Female, Other, Decline to Answer
5. phone_number       — número de 10 dígitos de EE.UU.
6. address_line_1     — dirección de la calle
7. city               — nombre de la ciudad
8. state              — abreviatura de 2 letras del estado (ej: NY, CA, TX)
9. zip_code           — 5 dígitos o formato ZIP+4

== CAMPOS OPCIONALES ==
Después de los campos requeridos, di:
"También puedo recopilar su información de seguro, contacto de emergencia e idioma preferido. ¿Le gustaría proporcionar alguno de esos?"

== CONFIRMACIÓN ==
Lee toda la información recopilada y pregunta:
"¿Todo está correcto o le gustaría cambiar algo?"
Si está correcto → llama a register_patient().

== PROGRAMACIÓN DE CITAS (después del registro) ==
Di: "¡Excelente! ¿Le gustaría programar su primera cita hoy?"
Si SÍ: pregunta tipo, fecha y hora → llama a schedule_appointment().

== REGLAS ==
- Respuestas CORTAS — 1-2 oraciones. Esta es una llamada de voz.
- Una pregunta a la vez.
- Llama a register_patient UNA SOLA VEZ.
"""


# ─────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# ─────────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "register_patient",
            "description": (
                "Register a new patient after collecting and confirming all required info. "
                "Call ONLY after explicit confirmation. "
                "Required: first_name, last_name, date_of_birth, sex, phone_number, "
                "address_line_1, city, state, zip_code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name":               {"type": "string"},
                    "last_name":                {"type": "string"},
                    "date_of_birth":            {"type": "string", "description": "MM/DD/YYYY"},
                    "sex":                      {"type": "string", "description": "Male, Female, Other, or Decline to Answer"},
                    "phone_number":             {"type": "string", "description": "10-digit US phone"},
                    "address_line_1":           {"type": "string"},
                    "address_line_2":           {"type": "string"},
                    "city":                     {"type": "string"},
                    "state":                    {"type": "string", "description": "2-letter US state"},
                    "zip_code":                 {"type": "string"},
                    "email":                    {"type": "string"},
                    "insurance_provider":       {"type": "string"},
                    "insurance_member_id":      {"type": "string"},
                    "preferred_language":       {"type": "string"},
                    "emergency_contact_name":   {"type": "string"},
                    "emergency_contact_phone":  {"type": "string"}
                },
                "required": [
                    "first_name", "last_name", "date_of_birth", "sex",
                    "phone_number", "address_line_1", "city", "state", "zip_code"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_patient",
            "description": "Update an existing patient record. Requires patient_id of existing record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id":               {"type": "string", "description": "UUID of existing patient"},
                    "first_name":               {"type": "string"},
                    "last_name":                {"type": "string"},
                    "date_of_birth":            {"type": "string"},
                    "sex":                      {"type": "string"},
                    "phone_number":             {"type": "string"},
                    "address_line_1":           {"type": "string"},
                    "address_line_2":           {"type": "string"},
                    "city":                     {"type": "string"},
                    "state":                    {"type": "string"},
                    "zip_code":                 {"type": "string"},
                    "email":                    {"type": "string"},
                    "insurance_provider":       {"type": "string"},
                    "insurance_member_id":      {"type": "string"},
                    "preferred_language":       {"type": "string"},
                    "emergency_contact_name":   {"type": "string"},
                    "emergency_contact_phone":  {"type": "string"}
                },
                "required": ["patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_appointment",
            "description": (
                "Schedule a first appointment for a patient after successful registration. "
                "Call ONLY after register_patient has succeeded."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id":        {"type": "string", "description": "UUID from successful registration"},
                    "appointment_type":  {
                        "type": "string",
                        "description": "Type: General Checkup, Follow-up, Consultation, Lab Work, Vaccination, Specialist Referral, Other"
                    },
                    "preferred_date":    {"type": "string", "description": "Preferred appointment date"},
                    "preferred_time":    {"type": "string", "description": "Preferred appointment time"},
                    "notes":             {"type": "string", "description": "Any additional notes (optional)"}
                },
                "required": ["patient_id", "appointment_type", "preferred_date", "preferred_time"]
            }
        }
    }
]


# ─────────────────────────────────────────────────────────────
# LANGUAGE DETECTION
# ─────────────────────────────────────────────────────────────
_SPANISH_TRIGGERS = [
    "hablo español", "en español", "habla español", "español",
    "hablar español", "hablo espanol", "espanol"
]

def _detect_language(conversation_history: list) -> str:
    """
    Scan conversation history for Spanish trigger phrases.
    Returns 'es' if Spanish detected, 'en' otherwise.
    """
    for msg in conversation_history:
        content = msg.get("content") or ""
        if isinstance(content, str):
            content_lower = content.lower()
            if any(trigger in content_lower for trigger in _SPANISH_TRIGGERS):
                return "es"
    return "en"


# ─────────────────────────────────────────────────────────────
# FUNCTION HANDLERS
# ─────────────────────────────────────────────────────────────
def _handle_register_patient(args: dict) -> dict:
    """Validate, check duplicate, save patient."""
    phone_raw = args.get("phone_number", "")
    phone_digits = re.sub(r"\D", "", phone_raw)
    existing = get_patient_by_phone(phone_digits)

    if existing:
        print(f"⚠️  Duplicate phone: {phone_digits} → {existing['first_name']} {existing['last_name']}")
        return {
            "success": False,
            "duplicate_found": True,
            "existing_patient_id": existing["patient_id"],
            "existing_first_name": existing["first_name"],
            "existing_last_name":  existing["last_name"],
            "message": (
                f"A patient named {existing['first_name']} {existing['last_name']} "
                "already exists with this phone number."
            )
        }

    cleaned, errors = validate_patient_data(args)
    if errors:
        print(f"⚠️  Validation errors: {errors}")
        return {
            "success": False,
            "duplicate_found": False,
            "validation_errors": errors,
            "message": f"Validation failed: {'; '.join(errors)}"
        }

    try:
        patient = create_patient(cleaned)
        return {
            "success": True,
            "duplicate_found": False,
            "patient_id": patient["patient_id"],
            "first_name": patient["first_name"],
            "message": f"Patient registered successfully. ID: {patient['patient_id']}"
        }
    except Exception as e:
        print(f"❌ DB error: {e}")
        return {"success": False, "duplicate_found": False,
                "message": "Database error saving registration."}


def _handle_update_patient(args: dict) -> dict:
    """Partial update on existing patient."""
    patient_id = args.pop("patient_id", None)
    if not patient_id:
        return {"success": False, "message": "patient_id is required for updates"}

    cleaned, errors = validate_patient_data(args, required_only=True)
    if errors:
        return {"success": False, "validation_errors": errors,
                "message": f"Validation failed: {'; '.join(errors)}"}

    try:
        patient = db_update_patient(patient_id, cleaned)
        if not patient:
            return {"success": False, "message": "Patient not found"}
        return {"success": True, "patient_id": patient["patient_id"],
                "message": "Patient record updated successfully"}
    except Exception as e:
        print(f"❌ DB update error: {e}")
        return {"success": False, "message": "Database error updating record."}


def _handle_schedule_appointment(args: dict) -> dict:
    """Schedule appointment after registration."""
    patient_id = args.get("patient_id")
    if not patient_id:
        return {"success": False, "message": "patient_id is required"}

    appt_type = args.get("appointment_type", "General Checkup")
    # Normalize appointment type
    if appt_type not in APPOINTMENT_TYPES:
        appt_type = "General Checkup"

    try:
        appt = create_appointment(
            patient_id=patient_id,
            appointment_type=appt_type,
            preferred_date=args.get("preferred_date"),
            preferred_time=args.get("preferred_time"),
            notes=args.get("notes")
        )
        return {
            "success": True,
            "appointment_id": appt["appointment_id"],
            "appointment_type": appt_type,
            "preferred_date": args.get("preferred_date"),
            "preferred_time": args.get("preferred_time"),
            "message": f"Appointment scheduled: {appt_type} on {args.get('preferred_date')} at {args.get('preferred_time')}"
        }
    except Exception as e:
        print(f"❌ Appointment error: {e}")
        return {"success": False, "message": "Could not schedule appointment."}


def _dispatch_tool(name: str, args: dict) -> str:
    """Route tool call to correct handler."""
    if name == "register_patient":
        result = _handle_register_patient(args)
    elif name == "update_patient":
        result = _handle_update_patient(args)
    elif name == "schedule_appointment":
        result = _handle_schedule_appointment(args)
    else:
        result = {"success": False, "message": f"Unknown function: {name}"}
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────
# MAIN CHAT FUNCTION
# ─────────────────────────────────────────────────────────────
def chat(conversation_history: list) -> dict:
    """
    Send conversation history to Groq and get AI response.

    Args:
        conversation_history: list of {"role": ..., "content": ...}

    Returns:
        dict:
            reply           — str
            function_called — bool
            function_name   — str | None
            function_args   — dict | None
            function_result — dict | None
            language        — "en" | "es"
            history_additions — list of messages to add to history
    """
    # Detect language from history
    lang = _detect_language(conversation_history)
    system_prompt = SYSTEM_PROMPT_ES if lang == "es" else SYSTEM_PROMPT_EN

    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    # Disable tools once a successful registration is done
    # (appointment scheduling is still allowed after registration)
    registration_done = any(
        msg.get("role") == "tool" and
        '"success": true' in msg.get("content", "") and
        "patient_id" in msg.get("content", "")
        for msg in conversation_history
    )

    # Also disable register_patient if already registered
    # but keep schedule_appointment available
    if registration_done:
        active_tools = [t for t in TOOLS if t["function"]["name"] != "register_patient"]
    else:
        active_tools = TOOLS

    tool_choice = "auto" if active_tools else "none"

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=active_tools,
        tool_choice=tool_choice,
        temperature=0.4,
        max_tokens=300
    )

    message = response.choices[0].message

    # ── Tool call ────────────────────────────────────────────
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        print(f"\n🔧 Tool called: {function_name}")
        print(f"   Args: {json.dumps(arguments, indent=2)}")

        tool_result_str = _dispatch_tool(function_name, arguments)
        tool_result = json.loads(tool_result_str)
        print(f"   Result: {tool_result_str}")

        # Messages to add to history (CRITICAL for preventing double registration)
        assistant_tool_msg = {
            "role": "assistant",
            "content": None,
            "tool_calls": message.tool_calls
        }
        tool_result_msg = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result_str
        }

        messages.append(assistant_tool_msg)
        messages.append(tool_result_msg)

        final = _get_client().chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=200
        )

        return {
            "reply":             final.choices[0].message.content,
            "function_called":   True,
            "function_name":     function_name,
            "function_args":     arguments,
            "function_result":   tool_result,
            "language":          lang,
            "history_additions": [assistant_tool_msg, tool_result_msg]
        }

    # ── Normal reply ─────────────────────────────────────────
    return {
        "reply":             message.content,
        "function_called":   False,
        "function_name":     None,
        "function_args":     None,
        "function_result":   None,
        "language":          lang,
        "history_additions": []
    }
