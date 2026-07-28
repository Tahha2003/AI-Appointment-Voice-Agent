"""
database.py — SQLite patient registration database

Tables:
  patients         — full US demographic fields, UUID PK, soft delete
  appointments     — mock appointment scheduling linked to patients
  call_transcripts — call summaries linked to patients

Bonus features: appointment scheduling, call transcript storage
"""
import sqlite3
import uuid
import os
import re
from datetime import datetime, timezone, date

DB_PATH = os.getenv("DB_PATH", "patients.db")

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV",
    "NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VT","VA","WA","WV","WI","WY","DC"
}

APPOINTMENT_TYPES = [
    "General Checkup", "Follow-up", "Consultation",
    "Lab Work", "X-Ray", "Vaccination", "Specialist Referral", "Other"
]

# ─────────────────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────────────────
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ── patients ──────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id              TEXT PRIMARY KEY,
            first_name              TEXT NOT NULL,
            last_name               TEXT NOT NULL,
            date_of_birth           TEXT NOT NULL,
            sex                     TEXT NOT NULL,
            phone_number            TEXT NOT NULL,
            email                   TEXT,
            address_line_1          TEXT NOT NULL,
            address_line_2          TEXT,
            city                    TEXT NOT NULL,
            state                   TEXT NOT NULL,
            zip_code                TEXT NOT NULL,
            insurance_provider      TEXT,
            insurance_member_id     TEXT,
            preferred_language      TEXT DEFAULT 'English',
            emergency_contact_name  TEXT,
            emergency_contact_phone TEXT,
            created_at              TEXT NOT NULL,
            updated_at              TEXT NOT NULL,
            deleted_at              TEXT
        )
    """)

    # ── appointments (bonus) ──────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id   TEXT PRIMARY KEY,
            patient_id       TEXT NOT NULL,
            appointment_type TEXT NOT NULL DEFAULT 'General Checkup',
            preferred_date   TEXT,
            preferred_time   TEXT,
            doctor           TEXT DEFAULT 'To be assigned',
            notes            TEXT,
            status           TEXT DEFAULT 'scheduled',
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    # ── call_transcripts (bonus) ──────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_transcripts (
            transcript_id  TEXT PRIMARY KEY,
            patient_id     TEXT,
            call_id        TEXT,
            summary        TEXT,
            full_transcript TEXT,
            language       TEXT DEFAULT 'English',
            duration_secs  INTEGER,
            outcome        TEXT,
            created_at     TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Patients table ready")
    print("✅ Appointments table ready")
    print("✅ Call transcripts table ready")
    _seed_data()


# ─────────────────────────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────────────────────────
def _seed_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM patients WHERE deleted_at IS NULL")
    count = cursor.fetchone()[0]
    conn.close()
    if count > 0:
        return

    now = _utc_now()
    seed_patients = [
        {
            "patient_id": str(uuid.uuid4()),
            "first_name": "Jane",
            "last_name": "Doe",
            "date_of_birth": "03/15/1990",
            "sex": "Female",
            "phone_number": "5551234567",
            "email": "jane.doe@email.com",
            "address_line_1": "123 Main Street",
            "address_line_2": "Apt 4B",
            "city": "New York",
            "state": "NY",
            "zip_code": "10001",
            "insurance_provider": "BlueCross BlueShield",
            "insurance_member_id": "BCB123456",
            "preferred_language": "English",
            "emergency_contact_name": "John Doe",
            "emergency_contact_phone": "5559876543",
            "created_at": now,
            "updated_at": now,
            "deleted_at": None
        },
        {
            "patient_id": str(uuid.uuid4()),
            "first_name": "Carlos",
            "last_name": "Rivera",
            "date_of_birth": "07/22/1985",
            "sex": "Male",
            "phone_number": "5559876543",
            "email": "carlos.rivera@email.com",
            "address_line_1": "456 Oak Avenue",
            "address_line_2": None,
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90001",
            "insurance_provider": "Aetna",
            "insurance_member_id": "AET789012",
            "preferred_language": "Spanish",
            "emergency_contact_name": "Maria Rivera",
            "emergency_contact_phone": "5554561234",
            "created_at": now,
            "updated_at": now,
            "deleted_at": None
        }
    ]

    conn = get_connection()
    cursor = conn.cursor()
    jane_id = seed_patients[0]["patient_id"]
    carlos_id = seed_patients[1]["patient_id"]

    for p in seed_patients:
        cursor.execute("""
            INSERT INTO patients VALUES (
                :patient_id,:first_name,:last_name,:date_of_birth,:sex,
                :phone_number,:email,:address_line_1,:address_line_2,
                :city,:state,:zip_code,:insurance_provider,
                :insurance_member_id,:preferred_language,
                :emergency_contact_name,:emergency_contact_phone,
                :created_at,:updated_at,:deleted_at
            )
        """, p)

    # Seed appointments for demo
    seed_appointments = [
        {
            "appointment_id": str(uuid.uuid4()),
            "patient_id": jane_id,
            "appointment_type": "General Checkup",
            "preferred_date": "08/05/2026",
            "preferred_time": "10:00 AM",
            "doctor": "Dr. Smith",
            "notes": "Annual physical",
            "status": "scheduled",
            "created_at": now,
            "updated_at": now
        },
        {
            "appointment_id": str(uuid.uuid4()),
            "patient_id": carlos_id,
            "appointment_type": "Consultation",
            "preferred_date": "08/10/2026",
            "preferred_time": "2:00 PM",
            "doctor": "Dr. Johnson",
            "notes": "Follow-up on previous visit",
            "status": "scheduled",
            "created_at": now,
            "updated_at": now
        }
    ]
    for a in seed_appointments:
        cursor.execute("""
            INSERT INTO appointments VALUES (
                :appointment_id,:patient_id,:appointment_type,
                :preferred_date,:preferred_time,:doctor,:notes,
                :status,:created_at,:updated_at
            )
        """, a)

    conn.commit()
    conn.close()
    print("✅ Seed data inserted (2 patients + 2 appointments)")


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────
def validate_name(value: str, field: str) -> str:
    value = value.strip()
    if not value or len(value) > 50:
        raise ValueError(f"{field} must be 1-50 characters")
    if not re.match(r"^[A-Za-z\-' ]+$", value):
        raise ValueError(f"{field} can only contain letters, hyphens, apostrophes, and spaces")
    return value

def validate_dob(value: str) -> str:
    value = value.strip()
    try:
        dob = datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError:
        raise ValueError("date_of_birth must be in MM/DD/YYYY format")
    if dob >= date.today():
        raise ValueError("date_of_birth cannot be today or in the future")
    return value

def validate_sex(value: str) -> str:
    allowed = {"Male", "Female", "Other", "Decline to Answer"}
    value = value.strip()
    if value not in allowed:
        raise ValueError(f"sex must be one of: {', '.join(allowed)}")
    return value

def validate_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 10:
        raise ValueError("phone_number must be exactly 10 US digits")
    return digits

def validate_email(value: str) -> str:
    value = value.strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise ValueError("email format is invalid")
    return value

def validate_state(value: str) -> str:
    value = value.strip().upper()
    if value not in US_STATES:
        raise ValueError("state must be a valid 2-letter US state abbreviation")
    return value

def validate_zip(value: str) -> str:
    value = value.strip()
    if not re.match(r"^\d{5}(-\d{4})?$", value):
        raise ValueError("zip_code must be 5-digit or ZIP+4 format (e.g. 10001 or 10001-1234)")
    return value

def validate_patient_data(data: dict, required_only: bool = False) -> tuple[dict, list]:
    cleaned = {}
    errors = []
    required_fields = [
        "first_name", "last_name", "date_of_birth", "sex",
        "phone_number", "address_line_1", "city", "state", "zip_code"
    ]
    if not required_only:
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"{field} is required")

    validators = {
        "first_name":    lambda v: validate_name(v, "first_name"),
        "last_name":     lambda v: validate_name(v, "last_name"),
        "date_of_birth": validate_dob,
        "sex":           validate_sex,
        "phone_number":  validate_phone,
        "email":         validate_email,
        "state":         validate_state,
        "zip_code":      validate_zip,
    }
    for field, value in data.items():
        if value is None or value == "":
            cleaned[field] = value
            continue
        if field in validators:
            try:
                cleaned[field] = validators[field](str(value))
            except ValueError as e:
                errors.append(str(e))
        else:
            cleaned[field] = value
    return cleaned, errors


# ─────────────────────────────────────────────────────────────
# PATIENTS CRUD
# ─────────────────────────────────────────────────────────────
def get_patient_by_phone(phone_number: str) -> dict | None:
    digits = re.sub(r"\D", "", phone_number)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM patients WHERE phone_number = ? AND deleted_at IS NULL",
        (digits,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_patient(data: dict) -> dict:
    now = _utc_now()
    patient_id = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO patients (
            patient_id, first_name, last_name, date_of_birth, sex,
            phone_number, email, address_line_1, address_line_2,
            city, state, zip_code, insurance_provider, insurance_member_id,
            preferred_language, emergency_contact_name, emergency_contact_phone,
            created_at, updated_at, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
    """, (
        patient_id,
        data["first_name"], data["last_name"], data["date_of_birth"],
        data["sex"], data["phone_number"],
        data.get("email"), data["address_line_1"], data.get("address_line_2"),
        data["city"], data["state"], data["zip_code"],
        data.get("insurance_provider"), data.get("insurance_member_id"),
        data.get("preferred_language", "English"),
        data.get("emergency_contact_name"), data.get("emergency_contact_phone"),
        now, now
    ))
    conn.commit()
    conn.close()
    print(f"✅ Patient registered: {data['first_name']} {data['last_name']} | ID: {patient_id}")
    print(f"   Payload: {data}")
    return get_patient_by_id(patient_id)

def get_all_patients(last_name: str = None, date_of_birth: str = None,
                     phone_number: str = None) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM patients WHERE deleted_at IS NULL"
    params = []
    if last_name:
        query += " AND LOWER(last_name) = LOWER(?)"
        params.append(last_name)
    if date_of_birth:
        query += " AND date_of_birth = ?"
        params.append(date_of_birth)
    if phone_number:
        digits = re.sub(r"\D", "", phone_number)
        query += " AND phone_number = ?"
        params.append(digits)
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_patient_by_id(patient_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM patients WHERE patient_id = ? AND deleted_at IS NULL",
        (patient_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_patient(patient_id: str, data: dict) -> dict | None:
    existing = get_patient_by_id(patient_id)
    if not existing:
        return None
    now = _utc_now()
    updatable = [
        "first_name", "last_name", "date_of_birth", "sex", "phone_number",
        "email", "address_line_1", "address_line_2", "city", "state",
        "zip_code", "insurance_provider", "insurance_member_id",
        "preferred_language", "emergency_contact_name", "emergency_contact_phone"
    ]
    set_clauses = []
    params = []
    for field in updatable:
        if field in data and data[field] is not None:
            set_clauses.append(f"{field} = ?")
            params.append(data[field])
    if not set_clauses:
        return existing
    set_clauses.append("updated_at = ?")
    params.append(now)
    params.append(patient_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE patients SET {', '.join(set_clauses)} WHERE patient_id = ? AND deleted_at IS NULL",
        params
    )
    conn.commit()
    conn.close()
    print(f"✅ Patient updated: ID={patient_id}")
    return get_patient_by_id(patient_id)

def soft_delete_patient(patient_id: str) -> bool:
    existing = get_patient_by_id(patient_id)
    if not existing:
        return False
    now = _utc_now()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE patients SET deleted_at = ?, updated_at = ? WHERE patient_id = ?",
        (now, now, patient_id)
    )
    conn.commit()
    conn.close()
    print(f"🗑️ Patient soft-deleted: ID={patient_id}")
    return True


# ─────────────────────────────────────────────────────────────
# APPOINTMENTS CRUD  (bonus feature)
# ─────────────────────────────────────────────────────────────
def create_appointment(patient_id: str, appointment_type: str = "General Checkup",
                       preferred_date: str = None, preferred_time: str = None,
                       doctor: str = "To be assigned", notes: str = None) -> dict:
    """Schedule a new appointment for a patient."""
    now = _utc_now()
    appointment_id = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO appointments (
            appointment_id, patient_id, appointment_type,
            preferred_date, preferred_time, doctor, notes,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?)
    """, (appointment_id, patient_id, appointment_type,
          preferred_date, preferred_time, doctor, notes, now, now))
    conn.commit()
    conn.close()
    print(f"📅 Appointment scheduled: {appointment_type} for patient {patient_id}")
    return get_appointment_by_id(appointment_id)

def get_appointment_by_id(appointment_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_appointments_by_patient(patient_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM appointments WHERE patient_id = ? ORDER BY created_at DESC",
        (patient_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_appointments() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, p.first_name, p.last_name, p.phone_number
        FROM appointments a
        LEFT JOIN patients p ON a.patient_id = p.patient_id
        ORDER BY a.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ─────────────────────────────────────────────────────────────
# CALL TRANSCRIPTS  (bonus feature)
# ─────────────────────────────────────────────────────────────
def save_transcript(patient_id: str = None, call_id: str = None,
                    summary: str = None, full_transcript: str = None,
                    language: str = "English", duration_secs: int = None,
                    outcome: str = None) -> dict:
    """Save a call transcript/summary linked to a patient."""
    now = _utc_now()
    transcript_id = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO call_transcripts (
            transcript_id, patient_id, call_id, summary,
            full_transcript, language, duration_secs, outcome, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (transcript_id, patient_id, call_id, summary,
          full_transcript, language, duration_secs, outcome, now))
    conn.commit()
    conn.close()
    print(f"📝 Transcript saved: ID={transcript_id} | Patient={patient_id}")
    return {"transcript_id": transcript_id, "patient_id": patient_id, "created_at": now}

def get_transcripts_by_patient(patient_id: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM call_transcripts WHERE patient_id = ? ORDER BY created_at DESC",
        (patient_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_transcripts() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, p.first_name, p.last_name
        FROM call_transcripts t
        LEFT JOIN patients p ON t.patient_id = p.patient_id
        ORDER BY t.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
