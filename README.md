# MediBook Voice Agent
### AI-powered Voice Patient Registration System

A fully functional voice AI agent that registers patients through natural phone conversations, persists data to a database, and exposes a complete REST API — built for the Voice AI Engineer technical assessment.

---

## Live Demo

| Resource | URL |
|----------|-----|
| **API Base** | https://ai-appointment-voice-agent.onrender.com |
| **Dashboard** | https://ai-appointment-voice-agent.onrender.com/dashboard |
| **Patients API** | https://ai-appointment-voice-agent.onrender.com/patients |
| **Appointments API** | https://ai-appointment-voice-agent.onrender.com/appointments |
| **Transcripts API** | https://ai-appointment-voice-agent.onrender.com/transcripts |
| **GitHub** | https://github.com/Tahha2003/AI-Appointment-Voice-Agent |

> **Phone Number Note:** Vapi US phone number provisioning is not available for Pakistan-based accounts (Vapi platform restriction). All testing was done using **Vapi's browser-based Talk button** which provides the full voice experience — STT, LLM conversation, function calling, and DB persistence all confirmed working end-to-end.

---

## How to Test (Live)

1. Go to [vapi.ai](https://vapi.ai) → **Assistants** → **Ai-Voice Assistant**
2. Click the **Talk** button (top right)
3. Say: *"I want to register as a new patient"*
4. The AI will collect: name → DOB → sex → phone → address → state → ZIP
5. After registration, it offers to schedule an appointment
6. Check saved data: https://ai-appointment-voice-agent.onrender.com/patients

---

## 🚀 Features

### Core Requirements
- **Voice Patient Registration** — natural conversational flow, not a rigid IVR menu
- **18-Field Data Model** — full US healthcare demographic dataset
- **Persistent Database** — SQLite with UUID primary keys, soft delete
- **REST API** — full CRUD with proper HTTP codes and JSON envelope
- **Input Validation** — server-side validation for all fields

### Bonus Features
- **Duplicate Detection** — recognizes returning callers by phone number, offers to update instead of create
- **Appointment Scheduling** — after registration, AI offers to schedule first appointment
- **Multi-language Support** — say "Hablo español" to switch to Spanish mid-conversation
- **Call Transcript Storage** — auto-saved on call end, linked to patient record
- **Dashboard** — web UI showing patients, appointments, and transcripts
- **Automated Tests** — 183 tests across 3 test files (0 failures)

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Voice / Telephony | [Vapi](https://vapi.ai) | Handles STT, TTS, call lifecycle — fastest path to working voice agent |
| Speech to Text | Soniox (via Vapi) | Low latency, high accuracy |
| LLM | Groq — Llama 3.3-70b-versatile | Free tier, ultra-fast inference, native function calling |
| Text to Speech | Vapi built-in | Natural voice, no extra setup |
| Backend | FastAPI (Python 3.11) | Fast, async, excellent for APIs |
| Database | SQLite | Zero config, sufficient for demo; easily swappable to PostgreSQL |
| Hosting | Render | Simple deployment from GitHub |

---

## 📦 Project Structure

```
AI-Voice Agent/
├── main.py            # FastAPI entry point, DB init, /dashboard route
├── routes.py          # All API endpoints
├── agent.py           # Groq LLM + 3 tools (register, update, schedule)
├── database.py        # SQLite schema, validation, CRUD
├── dashboard.html     # Web UI (patients, appointments, transcripts)
├── requirements.txt   # 5 packages only
├── render.yaml        # Render deployment config
├── .python-version    # Python 3.11.9
├── .env.example       # Environment variable template
└── tests/
    ├── README.md          # How to run tests
    ├── test_validation.py # 47 field validator tests
    ├── test_imports.py    # 60 integration tests
    ├── auto_test.py       # 76 automated E2E tests (5 demo patients)
    └── test_agent.py      # Interactive terminal chat simulation
```

---

## 🗂️ Patient Data Model

| Field | Required | Validation |
|-------|----------|------------|
| patient_id | Auto | UUID v4 |
| first_name | ✅ | 1-50 chars, alpha + hyphens/apostrophes/spaces |
| last_name | ✅ | Same as first_name |
| date_of_birth | ✅ | MM/DD/YYYY, not in future |
| sex | ✅ | Male / Female / Other / Decline to Answer |
| phone_number | ✅ | US 10-digit (strips formatting) |
| email | — | Valid email format |
| address_line_1 | ✅ | Street address |
| address_line_2 | — | Apt/Suite |
| city | ✅ | 1-100 chars |
| state | ✅ | Valid 2-letter US abbreviation |
| zip_code | ✅ | 5-digit or ZIP+4 |
| insurance_provider | — | Company name |
| insurance_member_id | — | Alphanumeric ID |
| preferred_language | — | Default: English |
| emergency_contact_name | — | Full name |
| emergency_contact_phone | — | US 10-digit |
| created_at | Auto | UTC timestamp |
| updated_at | Auto | UTC timestamp |
| deleted_at | Auto | NULL = active (soft delete) |

---

## 📋 API Endpoints

### Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/patients` | List all active patients |
| GET | `/patients?last_name=Smith` | Filter by last name |
| GET | `/patients?phone_number=5551234567` | Filter by phone |
| GET | `/patients?date_of_birth=03/15/1990` | Filter by DOB |
| GET | `/patients/{id}` | Get patient by UUID |
| POST | `/patients` | Create patient (409 on duplicate phone) |
| PUT | `/patients/{id}` | Partial update |
| DELETE | `/patients/{id}` | Soft delete |

### Appointments (Bonus)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/appointments` | List all appointments |
| GET | `/patients/{id}/appointments` | Patient's appointments |
| POST | `/patients/{id}/appointments` | Schedule appointment |

### Transcripts (Bonus)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/transcripts` | List all call transcripts |
| GET | `/patients/{id}/transcripts` | Patient's transcripts |

### Voice & Testing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook` | Vapi call lifecycle events |
| POST | `/vapi-function` | Vapi tool execution |
| POST | `/chat` | Text-based testing (no phone needed) |
| GET | `/dashboard` | Web UI |

**Response format:** `{ "data": {...}, "error": null }`
**HTTP codes:** 200, 201, 400, 404, 409, 422, 500

---

## 🏃‍♂️ Local Setup

```bash
git clone https://github.com/Tahha2003/AI-Appointment-Voice-Agent.git
cd AI-Appointment-Voice-Agent

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env
# Add GROQ_API_KEY (free at https://console.groq.com)

python main.py
# → http://localhost:8000
```

### Run Tests (no API calls needed)
```bash
python tests/test_validation.py  # 47 tests
python tests/test_imports.py     # 60 tests
python tests/auto_test.py        # 76 tests — 5 demo patients
```

### Interactive Voice Simulation
```bash
python tests/test_agent.py       # requires GROQ_API_KEY
```

---

## 🔧 Environment Variables

```env
GROQ_API_KEY=gsk_...         # Required — free at console.groq.com
VAPI_API_KEY=...             # Optional — from vapi.ai
DB_PATH=patients.db          # Local: patients.db | Render: /opt/render/project/src/patients.db
```

---

## 🔁 Architecture

```
Caller speaks
     ↓
Vapi (STT: voice → text)
     ↓
POST /webhook  →  FastAPI Backend
     ↓
Groq Llama 3.3-70b (LLM)
Collects: name → DOB → sex → phone → address → state → ZIP
     ↓
Confirms all info with caller
     ↓
register_patient() tool call
     ↓
POST /vapi-function
     ↓
Validation → Duplicate check → SQLite save
     ↓
"You're all set, [Name]!" (TTS → voice)
     ↓
Offer appointment scheduling
     ↓
schedule_appointment() → saved to DB
     ↓
Call ends → transcript auto-saved
```

---

## 🔐 Security

- API keys in environment variables only — never in source code
- `.env` excluded from git
- Server-side input validation on all endpoints
- Soft delete — records never hard-deleted
- HTTPS on Render

---

## ⚠️ Known Limitations & Trade-offs

- **SQLite on Render free tier** — data resets on redeploy. Use `DB_PATH=/opt/render/project/src/patients.db` for persistence between restarts. Production would use PostgreSQL.
- **No US phone number** — Vapi phone provisioning not available for Pakistan-based accounts (platform restriction). Browser Talk button used for all testing — full voice functionality confirmed working.
- **No authentication** — API endpoints are open. Production would add JWT/API key auth.
- **No HIPAA compliance** — demo only, not a production healthcare system. No real patient data stored.

---

## 🔮 Next Steps

- Migrate to PostgreSQL (Supabase) for persistent cloud storage
- Add JWT authentication to REST API
- Appointment reminder system (SMS via Twilio)
- HIPAA-compliant data handling for production
- Multi-language expansion (French, Arabic)
- Call recording storage linked to patient records
