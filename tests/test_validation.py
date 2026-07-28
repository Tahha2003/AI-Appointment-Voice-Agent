"""
tests/test_validation.py
Tests all field validators in isolation.

Usage:
    cd "AI-Voice Agent"
    python tests/test_validation.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (
    validate_name, validate_dob, validate_sex,
    validate_phone, validate_email, validate_state, validate_zip,
    validate_patient_data
)

passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  ✅ {label}")
        passed += 1
    else:
        print(f"  ❌ {label}" + (f" → {detail}" if detail else ""))
        failed += 1

def ok(fn, *args):
    try: fn(*args); return True
    except Exception as e: return False

def fail(fn, *args):
    try: fn(*args); return False
    except Exception: return True

def val(fn, *args):
    try: return fn(*args)
    except: return None

def section(t): print(f"\n=== {t} ===")

# ── PHONE ─────────────────────────────────────────────
section("Phone Number")
check("555-123-4567 → 5551234567",  val(validate_phone,"555-123-4567") == "5551234567")
check("(555) 123-4567 → digits",    val(validate_phone,"(555) 123-4567") == "5551234567")
check("raw 10 digits",              val(validate_phone,"5551234567") == "5551234567")
check("3 digits → rejected",        fail(validate_phone,"123"))
check("7 digits → rejected",        fail(validate_phone,"5551234"))
check("empty → rejected",           fail(validate_phone,""))
check("letters → rejected",         fail(validate_phone,"abcdefghij"))

# ── DATE OF BIRTH ─────────────────────────────────────
section("Date of Birth")
check("03/15/1990 valid",           ok(validate_dob,"03/15/1990"))
check("01/01/2000 valid",           ok(validate_dob,"01/01/2000"))
check("future 12/31/2099 → reject", fail(validate_dob,"12/31/2099"))
check("today → reject",             fail(validate_dob, __import__("datetime").date.today().strftime("%m/%d/%Y")))
check("wrong format → reject",      fail(validate_dob,"1990-03-15"))
check("invalid date → reject",      fail(validate_dob,"13/40/2000"))

# ── SEX ───────────────────────────────────────────────
section("Sex")
check("Male valid",                 ok(validate_sex,"Male"))
check("Female valid",               ok(validate_sex,"Female"))
check("Other valid",                ok(validate_sex,"Other"))
check("Decline to Answer valid",    ok(validate_sex,"Decline to Answer"))
check("M → rejected",               fail(validate_sex,"M"))
check("male → rejected",            fail(validate_sex,"male"))
check("empty → rejected",           fail(validate_sex,""))

# ── STATE ─────────────────────────────────────────────
section("US State")
check("NY valid",   val(validate_state,"NY") == "NY")
check("ca → CA",    val(validate_state,"ca") == "CA")
check("TX valid",   val(validate_state,"TX") == "TX")
check("XX → reject",fail(validate_state,"XX"))
check("NYC → reject",fail(validate_state,"NYC"))
check("empty → reject",fail(validate_state,""))

# ── ZIP CODE ──────────────────────────────────────────
section("ZIP Code")
check("10001 valid",        ok(validate_zip,"10001"))
check("10001-1234 valid",   ok(validate_zip,"10001-1234"))
check("4 digits → reject",  fail(validate_zip,"1234"))
check("6 digits → reject",  fail(validate_zip,"123456"))
check("letters → reject",   fail(validate_zip,"abcde"))
check("empty → reject",     fail(validate_zip,""))

# ── NAME ──────────────────────────────────────────────
section("Name")
check("John valid",             ok(validate_name,"John","f"))
check("M Tahha valid (space)",  ok(validate_name,"M Tahha","f"))
check("O'Brien valid",          ok(validate_name,"O'Brien","f"))
check("Mary-Jane valid",        ok(validate_name,"Mary-Jane","f"))
check("John123 → reject",       fail(validate_name,"John123","f"))
check("51 chars → reject",      fail(validate_name,"A"*51,"f"))
check("empty → reject",         fail(validate_name,"","f"))

# ── EMAIL ─────────────────────────────────────────────
section("Email")
check("valid@email.com",        ok(validate_email,"valid@email.com"))
check("user@domain.org",        ok(validate_email,"user@domain.org"))
check("no-at-sign → reject",    fail(validate_email,"invalidemail"))
check("no-domain → reject",     fail(validate_email,"user@"))

# ── validate_patient_data FULL ────────────────────────
section("Full Patient Data Validation")
valid = {
    "first_name":"Alice","last_name":"Johnson",
    "date_of_birth":"05/20/1992","sex":"Female",
    "phone_number":"555-987-6543",
    "address_line_1":"100 Oak Lane",
    "city":"Boston","state":"ma","zip_code":"02101"
}
cleaned, errors = validate_patient_data(valid)
check("Valid data → 0 errors",          len(errors) == 0, str(errors))
check("State normalized to uppercase",  cleaned.get("state") == "MA")
check("Phone normalized to digits",     cleaned.get("phone_number") == "5559876543")

missing = {"first_name": "Alice"}
_, err2 = validate_patient_data(missing)
check("Missing required fields caught", len(err2) > 0)

# ── RESULTS ───────────────────────────────────────────
print(f"\n{'='*45}")
print(f"RESULTS: {passed} passed | {failed} failed")
if failed == 0:
    print("🎉 All validation tests passed!")
else:
    print("⚠️  Some tests failed")
    sys.exit(1)
