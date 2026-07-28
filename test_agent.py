"""
Local test script — test patient registration AI in terminal.
No phone call or Vapi needed.

Usage:  python test_agent.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from database import init_db
from agent import chat

init_db()


def simulate_call():
    print("=" * 55)
    print("🧪 MediBook Voice Agent — Patient Registration Test")
    print("   Type your message. Type 'quit' to exit.")
    print("=" * 55)

    history = []
    registration_done = False

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

        if result["function_called"] and not registration_done:
            fn = result["function_name"]
            fn_result = result.get("function_result", {})

            if fn == "register_patient" and fn_result.get("success"):
                registration_done = True
                args = result["function_args"]
                print(f"\n✅ Patient Registered!")
                print(f"   Patient ID : {fn_result.get('patient_id', 'N/A')}")
                print(f"   Name       : {args.get('first_name')} {args.get('last_name')}")
                print(f"   DOB        : {args.get('date_of_birth')}")
                print(f"   Sex        : {args.get('sex')}")
                print(f"   Phone      : {args.get('phone_number')}")
                print(f"   Address    : {args.get('address_line_1')}, {args.get('city')}, {args.get('state')} {args.get('zip_code')}")

            elif fn == "register_patient" and fn_result.get("duplicate_found"):
                print(f"\n⚠️  Duplicate: {fn_result.get('message')}")

            elif fn == "update_patient" and fn_result.get("success"):
                print(f"\n✅ Patient Updated! ID: {fn_result.get('patient_id')}")

        history.append({"role": "assistant", "content": result["reply"]})


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set in .env")
        exit(1)
    simulate_call()
