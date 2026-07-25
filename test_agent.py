"""
Local test script — run this to test the AI without Vapi or phone calls.
Usage:  python test_agent.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from database import init_db
from agent import chat

init_db()  # create tables if they don't exist

def simulate_call():
    print("=" * 50)
    print("🧪 AI Voice Agent — Local Test")
    print("   Type your message. Type 'quit' to exit.")
    print("=" * 50)

    history = []
    booking_done = False   # track if appointment was already booked

    # First message — trigger AI greeting
    first_result = chat([{"role": "user", "content": "Hello"}])
    print(f"\n🤖 AI: {first_result['reply']}")
    history.append({"role": "user", "content": "Hello"})
    history.append({"role": "assistant", "content": first_result['reply']})

    while True:
        user_input = input("\n👤 You: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n👋 Test ended.")
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})
        result = chat(history)

        print(f"\n🤖 AI: {result['reply']}")

        if result["function_called"] and not booking_done:
            booking_done = True
            print(f"\n✅ [Appointment Booked!]")
            print(f"   Patient : {result['function_args'].get('patient_name')}")
            print(f"   Phone   : {result['function_args'].get('phone')}")
            print(f"   Reason  : {result['function_args'].get('reason')}")
            print(f"   Date    : {result['function_args'].get('date')}")
            print(f"   Time    : {result['function_args'].get('time')}")
            print(f"   Doctor  : {result['function_args'].get('doctor', 'Dr. Smith')}")

        history.append({"role": "assistant", "content": result["reply"]})

if __name__ == "__main__":
    provider = os.getenv("AI_PROVIDER", "groq").lower()
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set in .env")
        exit(1)
    if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not set in .env")
        exit(1)
    if provider == "groq" and not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set in .env")
        exit(1)

    simulate_call()
