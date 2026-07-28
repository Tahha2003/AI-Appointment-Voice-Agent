"""
tests/test_agent.py
Interactive terminal test — simulates a patient registration voice call.
No phone or Vapi needed. Type responses as if you are the patient.

Usage:
    cd "AI-Voice Agent"
    python tests/test_agent.py

Tips:
    - Type 'quit' or 'exit' to end
    - Say 'Hablo español' to test Spanish support
    - Use an existing phone number to test duplicate detection
    - Existing demo phones: 5551234567 (Jane Doe), 5559876543 (Carlos Rivera)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from database import init_db, get_all_patients
from agent import chat

init_db()


def print_header():
    print()
    print("=" * 60)
    print("  MediBook Voice Agent — Interactive Registration Test")
    print("=" * 60)
    print("  Type your responses as if you are calling the clinic.")
    print("  Commands: 'quit' to exit | 'db' to view saved patients")
    print()
    print("  Tips:")
    print("    - Say 'Hablo español' to switch to Spanish")
    print("    - Use phone 5551234567 to test duplicate detection")
    print("    - After registration, AI will offer to schedule appointment")
    print("=" * 60)
    print()


def print_db_status():
    """Show current patients in DB."""
    patients = get_all_patients()
    print(f"\n  --- DB Status: {len(patients)} active patient(s) ---")
    for p in patients:
        print(f"  • {p['first_name']} {p['last_name']} | {p['phone_number']} | {p['city']}, {p['state']}")
    print()


def simulate_call():
    print_header()
    print_db_status()

    history = []
    registration_done = False
    appointment_done = False
    turn = 0

    # AI greeting
    first_result = chat([{"role": "user", "content": "Hello"}])
    print(f"🤖 AI: {first_result['reply']}")
    if first_result.get("language") == "es":
        print("   🌐 [Spanish mode active]")

    history.append({"role": "user", "content": "Hello"})
    history.append({"role": "assistant", "content": first_result['reply']})

    while True:
        user_input = input("\n👤 You: ").strip()

        # Commands
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n👋 Test ended.")
            print_db_status()
            break

        if user_input.lower() == "db":
            print_db_status()
            continue

        if not user_input:
            continue

        turn += 1
        history.append({"role": "user", "content": user_input})
        result = chat(history)

        print(f"\n🤖 AI: {result['reply']}")

        # Language indicator
        if result.get("language") == "es":
            print("   🌐 [Spanish mode]")

        # Add tool messages to history (critical — prevents double registration)
        for extra_msg in result.get("history_additions", []):
            history.append(extra_msg)

        # Handle function results
        if result["function_called"]:
            fn        = result["function_name"]
            fn_result = result.get("function_result", {})
            fn_args   = result.get("function_args", {})

            # ── Successful registration ───────────────────────
            if fn == "register_patient" and fn_result.get("success") and not registration_done:
                registration_done = True
                print()
                print("  ┌─────────────────────────────────────────┐")
                print("  │  ✅  PATIENT REGISTERED SUCCESSFULLY    │")
                print("  ├─────────────────────────────────────────┤")
                print(f"  │  ID      : {fn_result.get('patient_id','')[:36]}")
                print(f"  │  Name    : {fn_args.get('first_name','')} {fn_args.get('last_name','')}")
                print(f"  │  DOB     : {fn_args.get('date_of_birth','')}")
                print(f"  │  Sex     : {fn_args.get('sex','')}")
                print(f"  │  Phone   : {fn_args.get('phone_number','')}")
                print(f"  │  Address : {fn_args.get('address_line_1','')}")
                print(f"  │            {fn_args.get('city','')}, {fn_args.get('state','')} {fn_args.get('zip_code','')}")
                if fn_args.get("insurance_provider"):
                    print(f"  │  Insur.  : {fn_args.get('insurance_provider')}")
                if fn_args.get("preferred_language") and fn_args.get("preferred_language") != "English":
                    print(f"  │  Lang    : {fn_args.get('preferred_language')}")
                print("  └─────────────────────────────────────────┘")
                print()

            # ── Duplicate phone ───────────────────────────────
            elif fn == "register_patient" and fn_result.get("duplicate_found"):
                print()
                print(f"  ⚠️  DUPLICATE DETECTED")
                print(f"     Existing: {fn_result.get('existing_first_name')} {fn_result.get('existing_last_name')}")
                print(f"     ID: {fn_result.get('existing_patient_id','')[:36]}")
                print()

            # ── Validation failed ─────────────────────────────
            elif fn == "register_patient" and not fn_result.get("success") and not fn_result.get("duplicate_found"):
                errs = fn_result.get("validation_errors", [])
                if errs:
                    print()
                    print(f"  ⚠️  VALIDATION ERRORS: {'; '.join(errs)}")
                    print()

            # ── Patient updated ───────────────────────────────
            elif fn == "update_patient" and fn_result.get("success"):
                print()
                print(f"  ✅  PATIENT UPDATED | ID: {fn_result.get('patient_id','')[:36]}")
                print()

            # ── Appointment scheduled ─────────────────────────
            elif fn == "schedule_appointment" and fn_result.get("success") and not appointment_done:
                appointment_done = True
                print()
                print("  ┌─────────────────────────────────────────┐")
                print("  │  📅  APPOINTMENT SCHEDULED              │")
                print("  ├─────────────────────────────────────────┤")
                print(f"  │  Type : {fn_result.get('appointment_type','')}")
                print(f"  │  Date : {fn_result.get('preferred_date','')}")
                print(f"  │  Time : {fn_result.get('preferred_time','')}")
                print("  └─────────────────────────────────────────┘")
                print()

        history.append({"role": "assistant", "content": result["reply"]})


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        print()
        print("  ❌ GROQ_API_KEY not set in .env")
        print("     Get a free key at: https://console.groq.com")
        print()
        sys.exit(1)
    simulate_call()
