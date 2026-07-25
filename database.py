import sqlite3
import os

# On Render, use /tmp for writable storage
# Locally, use current directory
DB_PATH = os.getenv("DB_PATH", "appointments.db")

def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # allows dict-like access
    return conn

def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            phone        TEXT,
            reason       TEXT,
            date         TEXT NOT NULL,
            time         TEXT NOT NULL,
            doctor       TEXT DEFAULT 'Dr. Smith',
            status       TEXT DEFAULT 'confirmed',
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Appointments table ready")

def save_appointment(patient_name: str, phone: str, reason: str,
                     date: str, time: str, doctor: str = "Dr. Smith") -> int:
    """Save a new appointment and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO appointments (patient_name, phone, reason, date, time, doctor)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (patient_name, phone, reason, date, time, doctor))
    
    appointment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    print(f"✅ Appointment saved: ID={appointment_id}, Patient={patient_name}, {date} at {time}")
    return appointment_id

def get_all_appointments() -> list:
    """Retrieve all appointments."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM appointments ORDER BY created_at DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def cancel_appointment(appointment_id: int) -> bool:
    """Cancel an appointment by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE appointments SET status = 'cancelled' WHERE id = ?
    """, (appointment_id,))
    
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated
