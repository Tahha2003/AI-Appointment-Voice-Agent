# MediBook Voice Agent — Test Suite

This folder contains all tests for the backend. No phone or Vapi needed to run any of these.

---

## Quick Start

Make sure you are in the **project root** (`AI-Voice Agent/`) and the virtual environment is active:

```bash
cd "AI-Voice Agent"
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

Make sure `.env` has your Groq key:
```
GROQ_API_KEY=gsk_your-key-here
```

---

## Test Files

| File | Type | LLM Calls | Time | What it tests |
|------|------|-----------|------|---------------|
| `test_validation.py` | Unit | None | ~1 sec | All field validators |
| `test_imports.py` | Integration | None | ~2 sec | Imports, DB, handlers, tools |
| `auto_test.py` | Automated E2E | None | ~3 sec | 5 demo patients, full flow |
| `test_agent.py` | Interactive | Yes (Groq) | Manual | Voice simulation in terminal |

---

## 1. Validation Tests (Fastest — No API needed)

Tests all field validators: phone, DOB, state, ZIP, sex, name, email.

```bash
python tests/test_validation.py
```

**Expected output:**
```
=== Phone Number ===
  ✅ 555-123-4567 → 5551234567
  ✅ 3 digits → rejected
  ...
=== RESULTS ===
47 passed | 0 failed
🎉 All validation tests passed!
```

---

## 2. Import & Integration Tests (No API needed)

Tests all module imports, DB init, seed data, register/update/schedule handlers,
duplicate detection, soft delete, language detection, dashboard file.

```bash
python tests/test_imports.py
```

**Expected output:**
```
✅ database.py imports
✅ agent.py imports
✅ routes.py imports
✅ main.py imports
✅ DB init OK — 2 patients, 2 appointments
✅ Language detection — Spanish: es, English: en
✅ Tools defined — [register_patient, update_patient, schedule_appointment]
✅ register_patient handler — ID: xxxxxxxx...
✅ schedule_appointment handler — ID: xxxxxxxx...
...
RESULTS: 60 passed | 0 failed
🎉 All tests passed! Backend fully functional.
```

---

## 3. Automated End-to-End Test with 5 Demo Patients (No API needed)

Runs a full automated test with 5 realistic patients covering all scenarios.

```bash
python tests/auto_test.py
```

**Demo patients used:**
| Name | Phone | City | Insurance |
|------|-------|------|-----------|
| Emily Johnson | 212-555-0001 | New York, NY | BlueCross BlueShield |
| Carlos Mendoza | 310-555-0002 | Los Angeles, CA | Aetna |
| Sarah O'Brien | 773-555-0003 | Chicago, IL | United Health |
| M Tahha Aleem | 512-555-0004 | Austin, TX | — |
| Priya Sharma | 617-555-0005 | Boston, MA | Cigna |

**What it tests:**
- Register all 5 patients with full validation
- Schedule 5 different appointment types (Checkup, Consultation, Lab Work, Vaccination)
- Save call transcripts linked to patients
- Duplicate phone detection (tries to register with existing phone)
- Partial update (change city, ZIP, insurance)
- All list filters (last_name, phone, date_of_birth)
- Per-patient appointment and transcript queries
- Multi-language detection (Spanish triggers)
- Soft delete (Priya is deleted, count goes from 7 → 6)

**Expected output:**
```
TEST 1: Register 5 Demo Patients
  [PASS] Register Emily Johnson
  [PASS] Register Carlos Mendoza
  ...
TEST 2: Schedule Appointments for All 5
  [PASS] Appointment: Emily Johnson — General Checkup
  ...
TEST 9: Final State Summary
  Active patients    : 6
  Total appointments : 7
  Call transcripts   : 3
FINAL: 76 passed | 0 failed
All automated tests passed!
```

---

## 4. Interactive Voice Agent Test (Requires GROQ_API_KEY)

Simulates a real voice registration call in the terminal.
Type your responses as if you were a patient calling in.

```bash
python tests/test_agent.py
```

**Example conversation flow:**

```
🤖 AI: Hello! Welcome to MediBook Clinic. May I start with your first name?

👤 You: John

🤖 AI: What is your last name, John?

👤 You: Smith

🤖 AI: What is your date of birth in MM/DD/YYYY format?

👤 You: 01/15/1985

🤖 AI: For sex, I can record Male, Female, Other, or Decline to Answer.

👤 You: Male

🤖 AI: What is your 10-digit US phone number?

👤 You: 5551234567

🤖 AI: What is your street address?

👤 You: 789 Pine Street

🤖 AI: What city?

👤 You: Chicago

🤖 AI: What is the 2-letter state abbreviation?

👤 You: IL

🤖 AI: What is your ZIP code?

👤 You: 60601

🤖 AI: I can also collect insurance, emergency contact, and preferred language. Would you like any of those?

👤 You: No

🤖 AI: To confirm — John Smith, DOB 01/15/1985, Male, 5551234567, 789 Pine Street, Chicago IL 60601. Does everything look correct?

👤 You: Yes

✅ Patient Registered!
   Patient ID : xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   Name       : John Smith
   DOB        : 01/15/1985
   Sex        : Male
   Phone      : 5551234567
   Address    : 789 Pine Street, Chicago, IL 60601

🤖 AI: You're all set, John! Would you also like to schedule your first appointment?

👤 You: Yes

🤖 AI: What type of appointment? (General Checkup, Consultation, Lab Work...)

👤 You: General Checkup

🤖 AI: What date works for you?

👤 You: August 15

🤖 AI: What time?

👤 You: 10 AM

📅 Appointment Scheduled!
   Type : General Checkup
   Date : August 15
   Time : 10 AM

🤖 AI: Your appointment is confirmed! Goodbye!

👤 You: quit
```

**To test Spanish support**, say `Hablo español` at any point:
```
👤 You: Hablo español
🌐 [Responding in Spanish]
🤖 AI: Hola! ¿Puede decirme su primer nombre?
```

**To test duplicate detection**, use a phone number already in the DB:
```
👤 You: 5551234567   ← already registered
🤖 AI: It looks like we already have a record for Jane Doe with that number.
       Would you like to update your information instead?
```

Type `quit` or `exit` to end the test.

---

## Run All Non-LLM Tests Together

```bash
python tests/test_validation.py && python tests/test_imports.py && python tests/auto_test.py
```

Expected combined output:
```
🎉 All validation tests passed!     (47 tests)
🎉 All tests passed!                (60 tests)
All automated tests passed!         (76 tests)
```

**Total: 183 tests, 0 failures**

---

## Verify Live API (After Render Deploy)

```bash
# Health check
curl https://ai-appointment-voice-agent.onrender.com/

# List patients
curl https://ai-appointment-voice-agent.onrender.com/patients

# List appointments
curl https://ai-appointment-voice-agent.onrender.com/appointments

# List transcripts
curl https://ai-appointment-voice-agent.onrender.com/transcripts

# Dashboard (open in browser)
https://ai-appointment-voice-agent.onrender.com/dashboard
```

---

## Notes

- `test_validation.py` and `test_imports.py` create and delete their own isolated test databases
- `auto_test.py` uses `tests/auto_test_run.db` which is cleaned up after each run
- `test_agent.py` uses the main `patients.db` — data will persist after the session
- None of the test databases are committed to git (`*.db` is in `.gitignore`)
