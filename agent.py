"""
AI conversation logic — Groq (Llama 3.3) powered.
Free tier, no credit card needed.
"""
import os
import json
from groq import Groq
from database import save_appointment
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
print(f"🤖 Using Groq ({MODEL}) - free tier")

# ─────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────
SYSTEM_PROMPT = """You are a friendly AI receptionist for CareCloud Medical Clinic.
Your job is to help patients book appointments.

Follow this exact conversation flow:
1. Greet the patient warmly.
2. Ask for their full name.
3. Ask for their phone number.
4. Ask for the reason / symptoms.
5. Ask for preferred date (e.g. "tomorrow", "July 28").
6. Ask for preferred time (e.g. "10 AM", "2 PM").
7. Confirm all details back to the patient.
8. Call the 'book_appointment' function ONCE to save the booking.
9. Tell the patient their appointment is confirmed and say goodbye.

Rules:
- Keep responses SHORT (2-3 sentences max) — this is a voice call.
- Be warm and professional.
- Ask ONE question at a time.
- If the patient is unclear, politely ask again.
- Never make up information.
- Always confirm before booking.
- Call book_appointment ONLY ONCE. After it is called, never call it again.
- Do NOT transfer calls or mention other clinics.
"""

# ─────────────────────────────────────────
# FUNCTION / TOOL DEFINITION
# ─────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a medical appointment ONLY after collecting all 5 required fields: patient_name, phone, reason, date, and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {
                        "type": "string",
                        "description": "Full name of the patient"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Patient phone number"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for visit or symptoms"
                    },
                    "date": {
                        "type": "string",
                        "description": "Appointment date (e.g. 'July 28, 2026')"
                    },
                    "time": {
                        "type": "string",
                        "description": "Appointment time (e.g. '10:00 AM')"
                    }
                },
                "required": ["patient_name", "phone", "reason", "date", "time"]
            }
        }
    }
]


def handle_function_call(function_name: str, arguments: dict) -> str:
    """Execute the function called by AI and return result."""
    if function_name == "book_appointment":
        appointment_id = save_appointment(
            patient_name=arguments.get("patient_name", "Unknown"),
            phone=arguments.get("phone", ""),
            reason=arguments.get("reason", ""),
            date=arguments.get("date", ""),
            time=arguments.get("time", ""),
            doctor="Dr. Smith"
        )
        return json.dumps({
            "success": True,
            "appointment_id": appointment_id,
            "message": f"Appointment booked successfully with ID {appointment_id}"
        })
    return json.dumps({"success": False, "message": "Unknown function"})


def chat(conversation_history: list) -> dict:
    """
    Send conversation history to Groq and get AI response.

    Args:
        conversation_history: List of {"role": ..., "content": ...} dicts

    Returns:
        dict with keys: reply, function_called, function_name, function_args
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    # Disable tool calling if booking already done in this session
    already_booked = any(msg.get("role") == "tool" for msg in conversation_history)
    tool_choice = "none" if already_booked else "auto"

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice=tool_choice,
        temperature=0.7,
        max_tokens=300
    )

    message = response.choices[0].message

    # AI wants to call a function
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        print(f"🔧 Function called: {function_name}")
        print(f"   Arguments: {json.dumps(arguments, indent=2)}")

        function_result = handle_function_call(function_name, arguments)

        # Send result back to Groq for final confirmation reply
        messages.append({"role": "assistant", "content": None, "tool_calls": message.tool_calls})
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": function_result
        })

        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )

        return {
            "reply": final_response.choices[0].message.content,
            "function_called": True,
            "function_name": function_name,
            "function_args": arguments
        }

    # Normal text reply
    return {
        "reply": message.content,
        "function_called": False,
        "function_name": None,
        "function_args": None
    }
