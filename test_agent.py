"""
Local test script — test the AI in terminal without Vapi or phone calls.
Usage:  python test_agent.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from database import init_db
from agent import chat

init_db()

def simulate_call():
    print("=" * 50)
    print("🧪 AI Voice Agent — Local Test (Groq + MediBook Clinic)")
    print("   Type your message. Type 'quit' to exit.")
    print("=" * 50)

    history = []
    booking_done = False

    # AI greeting
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
            args = result["function_args"]
            print(f"\n✅ Appointment Booked!")
            print(f"   Patient : {args.get('patient_name')}")
            print(f"   Phone   : {args.get('phone')}")
            print(f"   Reason  : {args.get('reason')}")
            print(f"   Date    : {args.get('date')}")
            print(f"   Time    : {args.get('time')}")
            print(f"   Doctor  : Dr. Smith")

        history.append({"role": "assistant", "content": result["reply"]})

if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set in .env")
        exit(1)
    simulate_call()
