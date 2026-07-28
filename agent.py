"""
agent.py — Groq-powered patient registration voice agent

LLM   : Groq llama-3.3-70b-versatile (free tier)
Tools : register_patient(), update_patient()

Conversation flow:
  1. Collect 9 required fields one at a time
  2. Offer optional fields (insurance, emergency contact, language)
  3. Read back all collected info → ask confirmation
  4. On confirm → call register_patient()
  5. On duplicate phone → offer to update existing record
"""

import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from database import (
    create_patient, update_patient as db_update_patient,
    get_patient_by_phone, validate_patient_data
)

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
print(f"🤖 Using Groq ({MODEL}) - free tier")


# ─────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# This is the core prompt engineering — controls the entire
# conversation behaviour. Documented per assessment requirement.
# ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a friendly, professional AI patient intake coordinator for MediBook Clinic.
Your job is to register new patients by collecting their demographic information through natural conversation.

== REQUIRED FIELDS (collect in this exact order) ==
1. first_name         — alphabetic only, hyphens/apostrophes allowed
2. last_name          — same rules as first_name
3. date_of_birth      — ask in MM/DD/YYYY format; must NOT be today or future
4. sex                — must be exactly one of: Male, Female, Other, Decline to Answer
5. phone_number       — US 10-digit number (e.g. 555-123-4567 or 5551234567)
6. address_line_1     — street address
7. city               — city name
8. state              — 2-letter US state abbreviation (e.g. NY, CA, TX)
9. zip_code           — 5-digit or ZIP+4 format (e.g. 10001 or 10001-1234)

== OPTIONAL FIELDS (offer after required fields) ==
After collecting all required fields, say:
"I can also collect your insurance information, emergency contact, and preferred language. Would you like to provide any of those?"

If yes, collect whichever ones they want:
- insurance_provider      — insurance company name
- insurance_member_id     — member/subscriber ID
- emergency_contact_name  — full name of emergency contact
- emergency_contact_phone — 10-digit US phone number
- preferred_language      — defaults to English if not provided

== CONFIRMATION STEP ==
Before saving, READ BACK all collected information clearly and ask:
"Does everything look correct, or would you like to change anything?"

If they want to correct something, collect ONLY that specific field again, then re-confirm.
If confirmed → call the register_patient function.

== VALIDATION RULES (enforce verbally) ==
- date_of_birth: If they give a future date, say:
  "That date appears to be in the future — could you please confirm your date of birth?"
- phone_number: If fewer than 10 digits, say:
  "I need a 10-digit US phone number. Could you please repeat that?"
- state: If not a valid 2-letter US state, say:
  "Could you give me the 2-letter state abbreviation? For example, NY for New York or CA for California."
- sex: If not one of the 4 options, offer the choices:
  "For sex, I can record Male, Female, Other, or Decline to Answer — which applies to you?"

== DUPLICATE HANDLING ==
If register_patient returns duplicate_found = true with an existing patient name:
Say: "It looks like we already have a record for [first_name] [last_name] with that phone number.
Would you like to update your existing information instead?"
If yes → call update_patient with the existing patient_id and any fields they want to change.
If no  → ask if they'd like to use a different phone number and restart.

== CONVERSATION RULES ==
- Keep ALL responses SHORT — 1-2 sentences max. This is a voice call.
- Ask ONE question at a time. Never ask multiple questions in one response.
- Be warm and professional, like a human intake coordinator.
- If the caller says something unclear, politely ask for clarification.
- Never make up or assume information — always ask.
- Do NOT call register_patient or update_patient until the caller explicitly confirms.
- After successful registration say: "You're all set, [first_name]! Your registration is complete. Goodbye!"
"""

# ─────────────────────────────────────────────────────────────
# TOOL DEFINITIONS
# These are the functions the LLM can call.
# ─────────────────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "register_patient",
            "description": (
                "Register a new patient after collecting and confirming all required information. "
                "Call ONLY after the caller has explicitly confirmed their information is correct. "
                "Required: first_name, last_name, date_of_birth, sex, phone_number, "
                "address_line_1, city, state, zip_code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name":               {"type": "string", "description": "Patient first name"},
                    "last_name":                {"type": "string", "description": "Patient last name"},
                    "date_of_birth":            {"type": "string", "description": "DOB in MM/DD/YYYY format"},
                    "sex":                      {"type": "string", "description": "Male, Female, Other, or Decline to Answer"},
                    "phone_number":             {"type": "string", "description": "10-digit US phone number"},
                    "address_line_1":           {"type": "string", "description": "Street address"},
                    "address_line_2":           {"type": "string", "description": "Apt/Suite (optional)"},
                    "city":                     {"type": "string", "description": "City"},
                    "state":                    {"type": "string", "description": "2-letter US state"},
                    "zip_code":                 {"type": "string", "description": "5-digit or ZIP+4"},
                    "email":                    {"type": "string", "description": "Email address (optional)"},
                    "insurance_provider":       {"type": "string", "description": "Insurance company (optional)"},
                    "insurance_member_id":      {"type": "string", "description": "Member ID (optional)"},
                    "preferred_language":       {"type": "string", "description": "Preferred language (optional, default English)"},
                    "emergency_contact_name":   {"type": "string", "description": "Emergency contact full name (optional)"},
                    "emergency_contact_phone":  {"type": "string", "description": "Emergency contact phone (optional)"}
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
            "description": (
                "Update an existing patient record. Use when a returning caller wants to update "
                "their information. Requires patient_id of the existing record."
            ),
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
    }
]


# ─────────────────────────────────────────────────────────────
# FUNCTION HANDLERS
# ─────────────────────────────────────────────────────────────
def _handle_register_patient(args: dict) -> dict:
    """
    Validate args, check for duplicates, then save to DB.
    Returns a dict that the LLM reads to decide what to say next.
    """
    # Check for duplicate phone number first
    phone_raw = args.get("phone_number", "")
    phone_digits = re.sub(r"\D", "", phone_raw)
    existing = get_patient_by_phone(phone_digits)

    if existing:
        print(f"⚠️  Duplicate phone detected: {phone_digits} → {existing['first_name']} {existing['last_name']}")
        return {
            "success": False,
            "duplicate_found": True,
            "existing_patient_id": existing["patient_id"],
            "existing_first_name": existing["first_name"],
            "existing_last_name": existing["last_name"],
            "message": (
                f"A patient named {existing['first_name']} {existing['last_name']} "
                f"already exists with this phone number."
            )
        }

    # Validate all fields
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
            "message": f"Patient registered successfully with ID {patient['patient_id']}"
        }
    except Exception as e:
        print(f"❌ DB error: {e}")
        return {
            "success": False,
            "duplicate_found": False,
            "message": "There was an error saving the registration. Please try again."
        }


def _handle_update_patient(args: dict) -> dict:
    """Validate and apply partial update to existing patient."""
    patient_id = args.pop("patient_id", None)
    if not patient_id:
        return {"success": False, "message": "patient_id is required for updates"}

    # Validate only the fields being updated
    cleaned, errors = validate_patient_data(args, required_only=True)
    if errors:
        return {
            "success": False,
            "validation_errors": errors,
            "message": f"Validation failed: {'; '.join(errors)}"
        }

    try:
        patient = db_update_patient(patient_id, cleaned)
        if not patient:
            return {"success": False, "message": "Patient not found"}
        return {
            "success": True,
            "patient_id": patient["patient_id"],
            "message": f"Patient record updated successfully"
        }
    except Exception as e:
        print(f"❌ DB error during update: {e}")
        return {"success": False, "message": "There was an error updating the record."}


def _dispatch_tool(name: str, args: dict) -> str:
    """Route tool call to the correct handler, return JSON string."""
    if name == "register_patient":
        result = _handle_register_patient(args)
    elif name == "update_patient":
        result = _handle_update_patient(args)
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
        conversation_history: List of {"role": ..., "content": ...} dicts

    Returns:
        dict:
            reply          — str, what the AI said
            function_called — bool
            function_name  — str | None
            function_args  — dict | None
            function_result — dict | None
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    # Disable tool calling if a successful registration already happened
    already_registered = any(
        msg.get("role") == "tool" and
        '"success": true' in msg.get("content", "")
        for msg in conversation_history
    )
    tool_choice = "none" if already_registered else "auto"

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice=tool_choice,
        temperature=0.4,   # lower = more consistent for data collection
        max_tokens=300
    )

    message = response.choices[0].message

    # ── Tool call requested ──────────────────────────────────
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        print(f"\n🔧 Tool called: {function_name}")
        print(f"   Args: {json.dumps(arguments, indent=2)}")

        tool_result_str = _dispatch_tool(function_name, arguments)
        tool_result = json.loads(tool_result_str)

        print(f"   Result: {tool_result_str}")

        # Send result back to Groq for natural language response
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": message.tool_calls
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result_str
        })

        final = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=200
        )

        return {
            "reply": final.choices[0].message.content,
            "function_called": True,
            "function_name": function_name,
            "function_args": arguments,
            "function_result": tool_result
        }

    # ── Normal text reply ────────────────────────────────────
    return {
        "reply": message.content,
        "function_called": False,
        "function_name": None,
        "function_args": None,
        "function_result": None
    }
