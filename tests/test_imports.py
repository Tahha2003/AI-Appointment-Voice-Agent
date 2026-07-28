"""
tests/test_imports.py
Validates all module imports, DB initialization, and core functionality.
No LLM API calls made — pure local tests.

Usage:
    cd "AI-Voice Agent"
    python tests/test_imports.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = "tests/test_imports_run.db"

import database
database.DB_PATH = "tests/test_imports_run.db"

errors = []
passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {label}")
        passed += 1
    else:
        print(f"  ❌ {label}" + (f"\n     → {detail}" if detail else ""))
        failed += 1
        errors.append(label)

def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")

# ── 1. IMPORTS ────────────────────────────────────────
section("1. Module Imports")

try:
    from database import (
        init_db, create_patient, get_all_patients, get_patient_by_id,
        update_patient, soft_delete_patient, get_patient_by_phone,
        validate_patient_data, create_appointment, get_all_appointments,
        get_appointments_by_patient, save_transcript, get_all_transcripts,
        get_transcripts_by_patient, APPOINTMENT_TYPES
    )
    check("database.py imports", True)
except Exception as e:
    check("database.py imports", False, str(e))

try:
    from agent import (
        chat, _detect_language, _handle_register_patient,
        _handle_update_patient, _handle_schedule_appointment,
        _dispatch_tool, TOOLS
    )
    check("agent.py imports", True)
except Exception as e:
    check("agent.py imports", False, str(e))

try:
    from routes import router
    check("routes.py imports", True)
except Exception as e:
    check("routes.py imports", False, str(e))

try:
    from main import app
    check("main.py imports", True)
except Exception as e:
    check("main.py imports", False, str(e))

# ── 2. DB INIT ────────────────────────────────────────
section("2. Database Init & Seed Data")

init_db()
patients = get_all_patients()
appointments = get_all_appointments()

check("Patients table created",         len(patients) >= 2)
check("2 seed patients loaded",         len(patients) == 2)
check("Appointments table created",     len(appointments) >= 2)
check("2 seed appointments loaded",     len(appointments) == 2)
check("Seed: Jane Doe (NY)",            any(p["first_name"]=="Jane" and p["state"]=="NY" for p in patients))
check("Seed: Carlos Rivera (CA)",       any(p["first_name"]=="Carlos" and p["state"]=="CA" for p in patients))
check("UUIDs generated",                all(len(p["patient_id"])==36 for p in patients))
check("deleted_at=None (active)",       all(p["deleted_at"] is None for p in patients))

# ── 3. TOOLS ─────────────────────────────────────────
section("3. Agent Tools")

tool_names = [t["function"]["name"] for t in TOOLS]
check("3 tools defined",                    len(TOOLS) == 3)
check("register_patient tool exists",       "register_patient" in tool_names)
check("update_patient tool exists",         "update_patient" in tool_names)
check("schedule_appointment tool exists",   "schedule_appointment" in tool_names)
check("APPOINTMENT_TYPES >= 6",             len(APPOINTMENT_TYPES) >= 6)

# ── 4. LANGUAGE DETECTION ────────────────────────────
section("4. Multi-language Detection")

check("Spanish trigger detected",   _detect_language([{"role":"user","content":"Hablo español"}]) == "es")
check("espanol (no accent) works",  _detect_language([{"role":"user","content":"hablo espanol"}]) == "es")
check("English default",            _detect_language([{"role":"user","content":"Hello"}]) == "en")
check("Empty history = English",    _detect_language([]) == "en")

# ── 5. REGISTER_PATIENT HANDLER ──────────────────────
section("5. register_patient Handler")

reg_result = _handle_register_patient({
    "first_name": "Alice",
    "last_name": "Johnson",
    "date_of_birth": "05/20/1992",
    "sex": "Female",
    "phone_number": "5551112222",
    "address_line_1": "100 Oak Lane",
    "city": "Boston",
    "state": "MA",
    "zip_code": "02101"
})
check("Registration success",           reg_result["success"] == True, str(reg_result))
check("patient_id returned (UUID)",     len(reg_result.get("patient_id","")) == 36)
check("duplicate_found=False",          reg_result["duplicate_found"] == False)
patient_id = reg_result.get("patient_id")

# verify in DB
p = get_patient_by_id(patient_id) if patient_id else None
check("Patient saved in DB",            p is not None)
if p:
    check("first_name correct",         p["first_name"] == "Alice")
    check("phone as digits only",       p["phone_number"] == "5551112222")
    check("state uppercase",            p["state"] == "MA")
    check("deleted_at=None",            p["deleted_at"] is None)

# duplicate detection
dup = _handle_register_patient({
    "first_name": "Sara", "last_name": "Khan",
    "date_of_birth": "01/01/1990", "sex": "Female",
    "phone_number": "5551112222",  # same phone
    "address_line_1": "1 St", "city": "NYC", "state": "NY", "zip_code": "10001"
})
check("Duplicate phone → success=False",    dup["success"] == False)
check("duplicate_found=True",               dup["duplicate_found"] == True)
check("Existing patient name returned",     dup.get("existing_first_name") == "Alice")

# ── 6. SCHEDULE_APPOINTMENT HANDLER ─────────────────
section("6. schedule_appointment Handler")

if patient_id:
    appt_result = _handle_schedule_appointment({
        "patient_id": patient_id,
        "appointment_type": "General Checkup",
        "preferred_date": "08/15/2026",
        "preferred_time": "10:00 AM"
    })
    check("Appointment scheduled",          appt_result["success"] == True, str(appt_result))
    check("appointment_id returned",        len(appt_result.get("appointment_id","")) == 36)
    check("appointment_type correct",       appt_result.get("appointment_type") == "General Checkup")

    appts = get_appointments_by_patient(patient_id)
    check("Appointment in DB",              len(appts) == 1)

# ── 7. VALIDATION ────────────────────────────────────
section("7. Field Validation")

from database import validate_phone, validate_dob, validate_state, validate_zip, validate_sex, validate_name

def ok(fn, *args):
    try: fn(*args); return True
    except: return False

def fail(fn, *args):
    try: fn(*args); return False
    except: return True

check("Phone 555-123-4567 → digits",    validate_phone("555-123-4567") == "5551234567")
check("Phone 3 digits → rejected",      fail(validate_phone, "123"))
check("DOB valid 03/15/1990",           ok(validate_dob, "03/15/1990"))
check("DOB future → rejected",          fail(validate_dob, "12/31/2099"))
check("DOB wrong format → rejected",    fail(validate_dob, "1990-03-15"))
check("State NY valid",                 validate_state("NY") == "NY")
check("State ca → CA",                  validate_state("ca") == "CA")
check("State XX → rejected",            fail(validate_state, "XX"))
check("ZIP 10001 valid",                ok(validate_zip, "10001"))
check("ZIP 10001-1234 valid",           ok(validate_zip, "10001-1234"))
check("ZIP 1234 → rejected",            fail(validate_zip, "1234"))
check("Sex Male valid",                 ok(validate_sex, "Male"))
check("Sex 'M' → rejected",             fail(validate_sex, "M"))
check("Name 'M Tahha' valid (space)",   ok(validate_name, "M Tahha", "first_name"))
check("Name 'O-Brien' valid (hyphen)",  ok(validate_name, "O-Brien", "last_name"))
check("Name 'John123' → rejected",      fail(validate_name, "John123", "first_name"))

# ── 8. SOFT DELETE ───────────────────────────────────
section("8. Soft Delete")

if patient_id:
    del_ok = soft_delete_patient(patient_id)
    check("Soft delete returns True",           del_ok == True)
    check("Patient not in active list",         get_patient_by_id(patient_id) is None)
    check("Fake UUID → False",                  soft_delete_patient("00000000-0000-0000-0000-000000000000") == False)

# ── 9. DASHBOARD FILE ────────────────────────────────
section("9. Dashboard File")

dash_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard.html")
check("dashboard.html exists",              os.path.exists(dash_path))
if os.path.exists(dash_path):
    size = os.path.getsize(dash_path)
    check("dashboard.html > 1KB",           size > 1000, f"{size} bytes")
    content = open(dash_path, encoding="utf-8").read()
    check("Dashboard has patients tab",     "patients" in content.lower())
    check("Dashboard has appointments tab", "appointments" in content.lower())
    check("Dashboard has transcripts tab",  "transcripts" in content.lower())

# ── CLEANUP ───────────────────────────────────────────
db_file = "tests/test_imports_run.db"
if os.path.exists(db_file):
    os.remove(db_file)

# ── RESULTS ───────────────────────────────────────────
print(f"\n{'='*50}")
print(f"  RESULTS: {passed} passed  |  {failed} failed")
print(f"{'='*50}")
if failed:
    print("❌ Failed tests:")
    for e in errors:
        print(f"   • {e}")
    sys.exit(1)
else:
    print("🎉 All tests passed! Backend fully functional.")
