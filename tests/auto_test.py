"""
tests/auto_test.py
Automated end-to-end test with 5 demo patients.
No interactive input, no LLM calls — pure DB + handler layer tests.

Tests:
  1. Register 5 different patients (varied demographics)
  2. Schedule appointments for each
  3. Save call transcripts
  4. Duplicate phone detection
  5. Update patient record
  6. Soft delete
  7. All filters and queries

Usage:
    cd "AI-Voice Agent"
    python tests/auto_test.py
"""
import os
import sys
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DB_PATH"] = "tests/auto_test_run.db"

import database
database.DB_PATH = "tests/auto_test_run.db"

from database import (
    init_db, get_all_patients, get_patient_by_id,
    update_patient, soft_delete_patient, get_patient_by_phone,
    get_all_appointments, get_appointments_by_patient,
    get_all_transcripts, get_transcripts_by_patient,
    save_transcript
)
from agent import (
    _handle_register_patient,
    _handle_update_patient,
    _handle_schedule_appointment,
    _detect_language
)

passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label}" + (f"\n         -> {detail}" if detail else ""))
        failed += 1

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ─────────────────────────────────────────────────────────────
# 5 DEMO PATIENTS
# ─────────────────────────────────────────────────────────────
DEMO_PATIENTS = [
    {
        "first_name": "Emily",
        "last_name": "Johnson",
        "date_of_birth": "04/12/1988",
        "sex": "Female",
        "phone_number": "2125550001",
        "address_line_1": "42 Broadway",
        "address_line_2": "Apt 3C",
        "city": "New York",
        "state": "NY",
        "zip_code": "10007",
        "email": "emily.johnson@email.com",
        "insurance_provider": "BlueCross BlueShield",
        "insurance_member_id": "BCB001122",
        "preferred_language": "English",
        "emergency_contact_name": "Robert Johnson",
        "emergency_contact_phone": "2125559999",
        "_appointment": {
            "type": "General Checkup",
            "date": "08/10/2026",
            "time": "9:00 AM"
        }
    },
    {
        "first_name": "Carlos",
        "last_name": "Mendoza",
        "date_of_birth": "11/30/1975",
        "sex": "Male",
        "phone_number": "3105550002",
        "address_line_1": "789 Sunset Blvd",
        "city": "Los Angeles",
        "state": "CA",
        "zip_code": "90028",
        "email": "carlos.mendoza@email.com",
        "insurance_provider": "Aetna",
        "insurance_member_id": "AET334455",
        "preferred_language": "Spanish",
        "emergency_contact_name": "Maria Mendoza",
        "emergency_contact_phone": "3105558888",
        "_appointment": {
            "type": "Consultation",
            "date": "08/12/2026",
            "time": "2:30 PM"
        }
    },
    {
        "first_name": "Sarah",
        "last_name": "O'Brien",
        "date_of_birth": "07/04/1995",
        "sex": "Female",
        "phone_number": "7735550003",
        "address_line_1": "101 Michigan Ave",
        "city": "Chicago",
        "state": "IL",
        "zip_code": "60601",
        "insurance_provider": "United Health",
        "insurance_member_id": "UHC556677",
        "preferred_language": "English",
        "_appointment": {
            "type": "Lab Work",
            "date": "08/15/2026",
            "time": "8:00 AM"
        }
    },
    {
        "first_name": "M Tahha",
        "last_name": "Aleem",
        "date_of_birth": "10/22/2003",
        "sex": "Male",
        "phone_number": "5125550004",
        "address_line_1": "500 Congress Ave",
        "city": "Austin",
        "state": "TX",
        "zip_code": "78701",
        "email": "tahha.aleem@email.com",
        "preferred_language": "English",
        "_appointment": {
            "type": "General Checkup",
            "date": "08/20/2026",
            "time": "11:00 AM"
        }
    },
    {
        "first_name": "Priya",
        "last_name": "Sharma",
        "date_of_birth": "02/14/1982",
        "sex": "Female",
        "phone_number": "6175550005",
        "address_line_1": "777 Boylston Street",
        "address_line_2": "Suite 200",
        "city": "Boston",
        "state": "MA",
        "zip_code": "02116",
        "email": "priya.sharma@email.com",
        "insurance_provider": "Cigna",
        "insurance_member_id": "CGN778899",
        "preferred_language": "English",
        "emergency_contact_name": "Raj Sharma",
        "emergency_contact_phone": "6175557777",
        "_appointment": {
            "type": "Vaccination",
            "date": "08/25/2026",
            "time": "3:00 PM"
        }
    }
]


# ─────────────────────────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────────────────────────
section("SETUP — Fresh Database")

# Remove old test DB if exists to ensure clean state
db_file = "tests/auto_test_run.db"
if os.path.exists(db_file):
    os.remove(db_file)

init_db()
check("DB initialized", True)

# ─────────────────────────────────────────────────────────────
# TEST 1 — Register all 5 patients
# ─────────────────────────────────────────────────────────────
section("TEST 1: Register 5 Demo Patients")

patient_ids = {}

for p in DEMO_PATIENTS:
    # Strip internal _appointment key before passing to handler
    data = {k: v for k, v in p.items() if not k.startswith("_")}
    name = f"{p['first_name']} {p['last_name']}"

    result = _handle_register_patient(data)
    check(f"Register {name}",              result["success"] == True, str(result))
    check(f"{name} — UUID returned",       len(result.get("patient_id", "")) == 36)
    check(f"{name} — no duplicate",        result.get("duplicate_found") == False)

    if result.get("patient_id"):
        patient_ids[name] = result["patient_id"]
        # Verify in DB
        saved = get_patient_by_id(result["patient_id"])
        check(f"{name} — saved in DB",       saved is not None)
        check(f"{name} — phone as digits",   saved["phone_number"] == re.sub(r"\D","",p["phone_number"]) if saved else False)
        check(f"{name} — state uppercase",   saved["state"] == p["state"].upper() if saved else False)

import re
total_patients = get_all_patients()
check("Total active patients = 7 (2 seed + 5 new)", len(total_patients) == 7,
      f"Got {len(total_patients)}")


# ─────────────────────────────────────────────────────────────
# TEST 2 — Schedule appointments for all 5
# ─────────────────────────────────────────────────────────────
section("TEST 2: Schedule Appointments for All 5")

for p in DEMO_PATIENTS:
    name = f"{p['first_name']} {p['last_name']}"
    patient_id = patient_ids.get(name)
    appt = p.get("_appointment", {})

    if not patient_id:
        check(f"Appointment for {name}", False, "patient_id not found")
        continue

    result = _handle_schedule_appointment({
        "patient_id":       patient_id,
        "appointment_type": appt.get("type", "General Checkup"),
        "preferred_date":   appt.get("date"),
        "preferred_time":   appt.get("time")
    })
    check(f"Appointment: {name} — {appt.get('type')}", result["success"] == True, str(result))
    check(f"  appointment_id returned", len(result.get("appointment_id","")) == 36)

all_appts = get_all_appointments()
registered_count = len(patient_ids)
expected_appts = 2 + registered_count  # 2 seed + however many registered
check(f"Total appointments = {expected_appts} (2 seed + {registered_count} new)",
      len(all_appts) == expected_appts, f"Got {len(all_appts)}")


# ─────────────────────────────────────────────────────────────
# TEST 3 — Save call transcripts for 3 patients
# ─────────────────────────────────────────────────────────────
section("TEST 3: Save Call Transcripts")

transcript_patients = list(patient_ids.items())[:3]
for name, pid in transcript_patients:
    lang = "Spanish" if "Carlos" in name else "English"
    t = save_transcript(
        patient_id=pid,
        call_id=f"call_{pid[:8]}",
        summary=f"New patient registration for {name}. All required fields collected.",
        full_transcript=f"Agent: Hello, welcome to MediBook.\nPatient: I'd like to register.\n...\nAgent: You're all set, registration complete.",
        language=lang,
        duration_secs=95,
        outcome="registration_completed"
    )
    check(f"Transcript saved: {name}", bool(t.get("transcript_id")))

all_transcripts = get_all_transcripts()
check("3 transcripts saved", len(all_transcripts) == 3, f"Got {len(all_transcripts)}")

# per-patient
first_name, first_pid = transcript_patients[0]
pt = get_transcripts_by_patient(first_pid)
check(f"Transcript retrievable by patient_id", len(pt) == 1)


# ─────────────────────────────────────────────────────────────
# TEST 4 — Duplicate phone detection
# ─────────────────────────────────────────────────────────────
section("TEST 4: Duplicate Phone Detection")

dup_result = _handle_register_patient({
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "01/01/1990",
    "sex": "Male",
    "phone_number": "2125550001",   # Emily Johnson's phone
    "address_line_1": "1 Test St",
    "city": "NYC",
    "state": "NY",
    "zip_code": "10001"
})
check("Duplicate phone → success=False",     dup_result["success"] == False)
check("duplicate_found=True",                dup_result["duplicate_found"] == True)
check("Returns existing patient first_name", dup_result.get("existing_first_name") == "Emily")
check("Patient count unchanged (still 7)",   len(get_all_patients()) == 7)


# ─────────────────────────────────────────────────────────────
# TEST 5 — Partial update
# ─────────────────────────────────────────────────────────────
section("TEST 5: Partial Update")

update_name = "M Tahha Aleem"
update_id = patient_ids.get("M Tahha Aleem")
if update_id:
    upd = _handle_update_patient({
        "patient_id": update_id,
        "city": "Houston",
        "zip_code": "77001",
        "insurance_provider": "Medicare"
    })
    check("Update success",              upd["success"] == True, str(upd))
    after = get_patient_by_id(update_id)
    check("City updated to Houston",     after["city"] == "Houston")
    check("ZIP updated",                 after["zip_code"] == "77001")
    check("Insurance updated",           after["insurance_provider"] == "Medicare")
    check("Name unchanged after update", after["first_name"] == "M Tahha")
else:
    check("Update test — patient found", False, "patient_id missing")


# ─────────────────────────────────────────────────────────────
# TEST 6 — Filters & Queries
# ─────────────────────────────────────────────────────────────
section("TEST 6: Filters & Queries")

by_last = get_all_patients(last_name="Johnson")
check("Filter last_name=Johnson → 1",        len(by_last) == 1)
check("Johnson is Emily",                    by_last[0]["first_name"] == "Emily" if by_last else False)

by_phone = get_all_patients(phone_number="3105550002")
check("Filter phone → 1 (Carlos)",           len(by_phone) == 1)

by_dob = get_all_patients(date_of_birth="07/04/1995")
check("Filter DOB → 1 (Sarah)",              len(by_dob) == 1)

no_match = get_all_patients(last_name="ZZZNOTEXIST")
check("Filter no match → 0",                 len(no_match) == 0)

# by patient appointments
emily_id = patient_ids.get("Emily Johnson")
if emily_id:
    emily_appts = get_appointments_by_patient(emily_id)
    check("Emily has 1 appointment",         len(emily_appts) == 1)
    check("Emily's appt type correct",       emily_appts[0]["appointment_type"] == "General Checkup")


# ─────────────────────────────────────────────────────────────
# TEST 7 — Language detection
# ─────────────────────────────────────────────────────────────
section("TEST 7: Multi-language Detection")

check("Spanish 'Hablo español'",     _detect_language([{"role":"user","content":"Hablo español"}]) == "es")
check("Spanish 'hablo espanol'",     _detect_language([{"role":"user","content":"hablo espanol"}]) == "es")
check("English 'Hello'",             _detect_language([{"role":"user","content":"Hello"}]) == "en")
check("English — empty history",     _detect_language([]) == "en")
check("Spanish in mid-conversation", _detect_language([
    {"role":"user","content":"Hello"},
    {"role":"assistant","content":"What is your name?"},
    {"role":"user","content":"Hablo español"},
]) == "es")


# ─────────────────────────────────────────────────────────────
# TEST 8 — Soft delete
# ─────────────────────────────────────────────────────────────
section("TEST 8: Soft Delete")

priya_id = patient_ids.get("Priya Sharma")
if priya_id:
    del_ok = soft_delete_patient(priya_id)
    check("Soft delete returns True",              del_ok == True)
    check("Priya not in active list",              get_patient_by_id(priya_id) is None)
    check("Active patients = 6 after delete",      len(get_all_patients()) == 6,
          f"Got {len(get_all_patients())}")
    check("Fake UUID → False",                     soft_delete_patient("00000000-0000-0000-0000-000000000000") == False)


# ─────────────────────────────────────────────────────────────
# TEST 9 — Final DB state summary
# ─────────────────────────────────────────────────────────────
section("TEST 9: Final State Summary")

final_patients     = get_all_patients()
final_appointments = get_all_appointments()
final_transcripts  = get_all_transcripts()

print(f"\n  Active patients    : {len(final_patients)}")
print(f"  Total appointments : {len(final_appointments)}")
print(f"  Call transcripts   : {len(final_transcripts)}")
print()
for p in final_patients:
    print(f"  • {p['first_name']} {p['last_name']} | {p['city']}, {p['state']} | {p['phone_number']}")

check("Final patients >= 6",      len(final_patients) >= 6)
check("Final appointments >= 6",  len(final_appointments) >= 6)
check("Final transcripts = 3",    len(final_transcripts) == 3)


# ─────────────────────────────────────────────────────────────
# CLEANUP & RESULTS
# ─────────────────────────────────────────────────────────────
db_file = "tests/auto_test_run.db"
if os.path.exists(db_file):
    os.remove(db_file)

print(f"\n{'='*55}")
print(f"  FINAL: {passed} passed  |  {failed} failed")
print(f"{'='*55}")

if failed > 0:
    print(f"  Some tests failed — check above")
    sys.exit(1)
else:
    print(f"  All automated tests passed!")
