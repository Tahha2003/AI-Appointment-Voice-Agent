"""
AI conversation logic.
Supports both OpenAI and Google Gemini (free).
Set AI_PROVIDER=gemini in .env to use Gemini for free.
"""
import os
import json
from database import save_appointment
from dotenv import load_dotenv
load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq").lower()

if AI_PROVIDER == "gemini":
    from google import genai as google_genai
    gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    GEMINI_MODEL = "gemini-2.0-flash"
    print(f"🤖 Using Google Gemini ({GEMINI_MODEL}) - free tier")
elif AI_PROVIDER == "groq":
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    GROQ_MODEL = "llama-3.3-70b-versatile"
    print(f"🤖 Using Groq ({GROQ_MODEL}) - free tier")
else:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    print("🤖 Using OpenAI GPT-4o-mini")

# ─────────────────────────────────────────
# SYSTEM PROMPT  (the personality / rules)
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
- If the patient is unclear, politely ask again.
- Never make up information.
- Always confirm before booking.
- IMPORTANT: Call book_appointment ONLY ONCE. After it is called, never call it again even if the patient says "thank you" or anything else.
- After booking is confirmed, only say goodbye. Do not book again.
"""

# ─────────────────────────────────────────
# FUNCTION / TOOL DEFINITION
# This tells OpenAI what function it can call
# ─────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a medical appointment for the patient after collecting all required information.",
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
                    },
                    "doctor": {
                        "type": "string",
                        "description": "Doctor name, default is Dr. Smith"
                    }
                },
                "required": ["patient_name", "phone", "reason", "date", "time"]
            }
        }
    }
]


def handle_function_call(function_name: str, arguments: dict) -> str:
    """Execute a function called by the AI and return the result."""
    if function_name == "book_appointment":
        appointment_id = save_appointment(
            patient_name=arguments.get("patient_name", "Unknown"),
            phone=arguments.get("phone", ""),
            reason=arguments.get("reason", ""),
            date=arguments.get("date", ""),
            time=arguments.get("time", ""),
            doctor=arguments.get("doctor", "Dr. Smith")
        )
        return json.dumps({
            "success": True,
            "appointment_id": appointment_id,
            "message": f"Appointment booked successfully with ID {appointment_id}"
        })
    return json.dumps({"success": False, "message": "Unknown function"})


# ─────────────────────────────────────────
# GEMINI CHAT (free tier)
# Gemini doesn't support function calling the same way,
# so we use a smart prompt trick: ask it to output JSON
# when it wants to book, then we parse and execute it.
# ─────────────────────────────────────────
def _chat_gemini(conversation_history: list) -> dict:
    """
    Gemini-based conversation using the new google-genai SDK.
    Uses a JSON trigger trick since we handle function calling manually.
    """
    GEMINI_SYSTEM = SYSTEM_PROMPT + """

IMPORTANT: When you have collected ALL of the following from the patient:
  - patient_name
  - phone
  - reason
  - date
  - time

Output EXACTLY this JSON block and nothing else on that turn:
<BOOK>
{
  "patient_name": "...",
  "phone": "...",
  "reason": "...",
  "date": "...",
  "time": "...",
  "doctor": "Dr. Smith"
}
</BOOK>

Otherwise just reply normally as a friendly voice receptionist (short sentences).
"""

    # Build the full prompt by combining system instructions + history + latest message
    conversation_text = GEMINI_SYSTEM + "\n\n"
    for msg in conversation_history[:-1]:
        role_label = "Patient" if msg["role"] == "user" else "Receptionist"
        conversation_text += f"{role_label}: {msg['content']}\n"

    last_user_msg = conversation_history[-1]["content"]
    conversation_text += f"Patient: {last_user_msg}\nReceptionist:"

    # Call Gemini using new SDK
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=conversation_text,
    )
    reply_text = response.text.strip()

    # Check if Gemini wants to book (JSON trigger pattern)
    if "<BOOK>" in reply_text and "</BOOK>" in reply_text:
        try:
            json_str = reply_text.split("<BOOK>")[1].split("</BOOK>")[0].strip()
            arguments = json.loads(json_str)
            print(f"🔧 Gemini triggered: book_appointment")
            print(f"   Arguments: {json.dumps(arguments, indent=2)}")

            handle_function_call("book_appointment", arguments)

            # Ask Gemini for a warm confirmation message
            confirm_prompt = (
                conversation_text
                + " <appointment successfully saved in system>\n"
                + "Now tell the patient their appointment is confirmed and say a warm goodbye. Keep it short."
            )
            confirm_response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=confirm_prompt,
            )
            return {
                "reply": confirm_response.text.strip(),
                "function_called": True,
                "function_name": "book_appointment",
                "function_args": arguments
            }
        except (json.JSONDecodeError, IndexError) as e:
            print(f"⚠️ Failed to parse Gemini booking JSON: {e}")
            print(f"   Raw reply: {reply_text}")

    return {
        "reply": reply_text,
        "function_called": False,
        "function_name": None,
        "function_args": None
    }


# ─────────────────────────────────────────
# OPENAI CHAT
# ─────────────────────────────────────────
def _chat_openai(conversation_history: list) -> dict:
    """OpenAI GPT-4o-mini with native function/tool calling."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=300
    )

    message = response.choices[0].message

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        print(f"🔧 Function called: {function_name}")
        print(f"   Arguments: {json.dumps(arguments, indent=2)}")

        function_result = handle_function_call(function_name, arguments)

        messages.append(message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": function_result
        })

        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
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

    return {
        "reply": message.content,
        "function_called": False,
        "function_name": None,
        "function_args": None
    }


# ─────────────────────────────────────────
# UNIFIED ENTRY POINT
# ─────────────────────────────────────────
def _chat_groq(conversation_history: list) -> dict:
    """
    Groq-based conversation — uses OpenAI-compatible API with
    native function/tool calling. Fast, free, no credit card needed.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    # If booking already happened in this session, disable tool calling
    already_booked = any(
        msg.get("role") == "tool" for msg in conversation_history
    )
    tool_choice = "none" if already_booked else "auto"

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice=tool_choice,
        temperature=0.7,
        max_tokens=300
    )

    message = response.choices[0].message

    # Check if AI wants to call a function
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        print(f"🔧 Function called: {function_name}")
        print(f"   Arguments: {json.dumps(arguments, indent=2)}")

        function_result = handle_function_call(function_name, arguments)

        # Send function result back so Groq gives a final confirmation reply
        messages.append({"role": "assistant", "content": None, "tool_calls": message.tool_calls})
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": function_result
        })

        final_response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
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

    return {
        "reply": message.content,
        "function_called": False,
        "function_name": None,
        "function_args": None
    }


def chat(conversation_history: list) -> dict:
    """
    Route to the correct AI provider based on AI_PROVIDER env var.
    AI_PROVIDER=groq    → Groq Llama 3.3 (free, default)
    AI_PROVIDER=gemini  → Google Gemini 2.0 Flash (free)
    AI_PROVIDER=openai  → OpenAI GPT-4o-mini
    """
    if AI_PROVIDER == "groq":
        return _chat_groq(conversation_history)
    if AI_PROVIDER == "gemini":
        return _chat_gemini(conversation_history)
    return _chat_openai(conversation_history)
