# MediBook Voice Agent
### AI-powered voice receptionist that registers patients through natural phone conversations.

---

## Live Demo

| Resource | URL |
|----------|-----|
| API Base URL | https://ai-appointment-voice-agent.onrender.com |
| Patients API | https://ai-appointment-voice-agent.onrender.com/patients |
| Appointments | https://ai-appointment-voice-agent.onrender.com/appointments |
| Transcripts | https://ai-appointment-voice-agent.onrender.com/transcripts |
| Dashboard | https://ai-appointment-voice-agent.onrender.com/dashboard |
| Voice Agent | Vapi browser Talk button (see Vapi Setup below) |

> **Note:** Hosted on Render free tier — first request may take ~50 seconds to wake up.

---

## Features

### Core Requirements
- **Voice Patient Registration** — AI collects all 18 US demographic fields conversationally
- **Natural Conversation** — Powered by Groq Llama 3.3-70b, feels like a human intake coordinator
- **Persistent Database** — SQLite with full CRUD, UUID primary keys, soft delete
- **REST API** — Full `/patients` CRUD with filters, proper HTTP codes, consistent JSON envelope
- **Input Validation** — Server-side validation for all fields (phone, DOB, state, ZIP, sex, name)
- **Confirmation** — Agent reads back all info before saving
- **Error Handling** — Invalid DOB, short phone, invalid state re-prompted specifically

### Bonus Features
- **Duplicate Detection** — Recognizes returning callers by phone, offers to update instead of create
- **Appointment Scheduling** — After registration, offers to book first appointment
- **Multi-language** — Say "Hablo español" to switch to Spanish
- **Call Transcripts** — Auto-saved on call end, linked to patient record
- **Dashboard** — Web UI showing patients, appointments, transcripts
- **Automated Tests** — 183 tests across 3 test files (no LLM calls needed)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice / Telephony | [Vapi](https://vapi.ai) |
| Speech to Text | Soniox (via Vapi) |
| LLM | Groq — Llama 3.3-70b-versatile (free) |
| Text to Speech | Vapi built-in |
| Backend | FastAPI (Python 3.11) |
| Database | SQLite |
| Hosting | Render |

**Why this stack:**
- Vapi abstracts all telephony/STT/TTS complexity, letting focus stay on LLM prompt and data layer
- Groq provides ultra-fast free inference with native function/tool calling support
- FastAPI + SQLite = minimal setup, zero external dependencies, deployable in minutes
- Render = straightforward Python deployment with environment variable management

---

## Patient Data Model

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| patient_id | UUID | Auto | Auto-generated |
| first_name | String | Yes | 1-50 chars, alpha + hyphens/apostrophes/spaces |
| last_name | String | Yes | Same as first_name |
| date_of_birth | String | Yes | MM/DD/YYYY, not in future |
| sex | Enum | Yes | Male / Female / Other / Decline to Answer |
| phone_number | String | Yes | US 10-digit (formatted or raw) |
| email | String | No | Valid email format |
| address_line_1 | String | Yes | Street address |
| address_line_2 | String | No | Apt/Suite |
| city | String | Yes | City name |
| state | String | Yes | Valid 2-letter US abbreviation |
| zip_code | String | Yes | 5-digit or ZIP+4 |
| insurance_provider | String | No | Company name |
| insurance_member_id | String | No | Alphanumeric ID |
| preferred_language | String | No | Default: English |
| emergency_contact_name | String | No | Full name |
| emergency_contact_phone | String | No | US 10-digit |
| created_at | Timestamp | Auto | UTC |
| updated_at | Timestamp | Auto | UTC |
| deleted_at | Timestamp | Auto | NULL = active (soft delete) |

---

## System Architecture

```
Patient calls → Vapi (STT: voice → text)
                    ↓
              POST /webhook
                    ↓
         Groq Llama 3.3-70b (LLM)
         Collects 9 required fields
         + optional fields
                    ↓
         Reads back info → confirms
                    ↓
    register_patient() tool call
                    ↓
          POST /vapi-function
                    ↓
   Duplicate check → Validation → SQLite
                    ↓
    "You're all set, [Name]!" (TTS → voice)
                    ↓
    Offer appointment scheduling
                    ↓
    schedule_appointment() tool call
                    ↓
    Appointment saved → Goodbye
```

---

## API Endpoints

### Patients
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/patients` | List all active patients |
| GET | `/patients?last_name=Smith` | Filter by last name |
| GET | `/patients?phone_number=5551234567` | Filter by phone |
| GET | `/patients?date_of_birth=03/15/1990` | Filter by DOB |
| GET | `/patients/{id}` | Get patient by UUID |
| POST | `/patients` | Create (409 on duplicate phone) |
| PUT | `/patients/{id}` | Partial update |
| DELETE | `/patients/{id}` | Soft delete |

### Appointments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/appointments` | All appointments |
| GET | `/patients/{id}/appointments` | By patient |
| POST | `/patients/{id}/appointments` | Create |

### Transcripts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/transcripts` | All transcripts |
| GET | `/patients/{id}/transcripts` | By patient |

### Voice
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook` | Vapi call events |
| POST | `/vapi-function` | Tool execution |
| POST | `/chat` | Text testing (no phone) |

### Response Format
```json
{ "data": {...}, "error": null }
```
HTTP codes: `200`, `201`, `400`, `404`, `409`, `422`, `500`

---

## Project Structure

```
AI-Voice Agent/
├── main.py            # FastAPI entry point, /dashboard route
├── routes.py          # All API endpoints + Vapi webhook handlers
├── agent.py           # Groq LLM + 3 tools (register, update, schedule)
├── database.py        # SQLite schema, validation, CRUD
├── dashboard.html     # Web UI (patients, appointments, transcripts)
├── requirements.txt   # 5 packages only
├── render.yaml        # Render deployment config
├── .python-version    # 3.11.9
├── .env.example       # Environment variable template
└── tests/
    ├── README.md          # Full testing guide for evaluators
    ├── test_validation.py # 47 validation tests (no LLM)
    ├── test_imports.py    # 60 integration tests (no LLM)
    ├── auto_test.py       # 76 automated E2E tests, 5 demo patients (no LLM)
    └── test_agent.py      # Interactive terminal chat (uses Groq)
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/Tahha2003/AI-Appointment-Voice-Agent.git
cd AI-Appointment-Voice-Agent

# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Configure
copy .env.example .env
# Add GROQ_API_KEY (free at console.groq.com)

# Run
python main.py
# → http://localhost:8000

# Test (no phone needed)
python tests/test_agent.py        # interactive chat
python tests/test_validation.py   # 47 validation tests
python tests/test_imports.py      # 60 integration tests
python tests/auto_test.py         # 76 automated E2E tests
```

---

## Environment Variables

```env
GROQ_API_KEY=gsk_your-key-here        # free at console.groq.com
VAPI_API_KEY=your-vapi-key-here       # from vapi.ai
DB_PATH=/opt/render/project/src/patients.db  # Render persistent path
```

---

## Phone Number Note

Vapi US phone number provisioning is **not available for all regions** (including Pakistan-based accounts). This is a Vapi platform restriction, not a code issue.

**All testing was done using Vapi's browser-based Talk button** — which is fully functional and demonstrates the complete end-to-end voice agent experience:
- Real-time Speech-to-Text (Soniox)
- Natural LLM conversation (Groq Llama 3.3-70b)
- Function calling (register_patient, update_patient, schedule_appointment)
- Database persistence (SQLite)
- Call transcript auto-save

**How to test:** Vapi Dashboard → Assistants → **Talk** button (top right of assistant page)

---

## Vapi Configuration

1. Sign up at [vapi.ai](https://vapi.ai)
2. **Create Assistant:**
   - First Message: `Hello! Thank you for calling MediBook Clinic. I'm here to help register you. May I start with your first name?`
   - Model: Groq → `llama-3.3-70b-versatile`
   - Advanced → Server URL: `https://ai-appointment-voice-agent.onrender.com/webhook`
3. **Create 3 Tools** (each with Server URL `https://ai-appointment-voice-agent.onrender.com/vapi-function`):
   - `register_patient` — all 9 required fields
   - `update_patient` — requires patient_id
   - `schedule_appointment` — requires patient_id, type, date, time
4. **Attach tools to assistant → Publish**
5. Use browser **Talk** button to test (US phone provisioning not available in all regions)

---

## Running Tests

```bash
# All non-LLM tests (instant, no API key needed)
python tests/test_validation.py && python tests/test_imports.py && python tests/auto_test.py

# Expected: 183 passed, 0 failed

# Interactive voice simulation (requires GROQ_API_KEY)
python tests/test_agent.py
```

See `tests/README.md` for full evaluator guide with expected outputs.

---

## Known Limitations & Trade-offs

- **SQLite on Render free tier** — data resets on redeploy (acceptable for demo; production would use PostgreSQL/Supabase)
- **No US phone number** — Vapi phone provisioning is not available for non-US/Pakistan-based accounts. This is a Vapi platform restriction. All testing and demo was done using **Vapi's browser-based Talk button** which provides the same full voice experience (STT + LLM + TTS + function calling). The system works end-to-end — only the phone number provisioning step is blocked by region.
- **No authentication** — API endpoints are open; production would add JWT/API key auth
- **No HIPAA compliance** — demo only, not a production healthcare system; no real patient data stored

---

## Next Steps (if given more time)

- Migrate to PostgreSQL (Supabase) for persistent cloud storage
- Add JWT authentication to REST API
- Store full call transcripts linked to patient records
- Add appointment reminder system (SMS via Twilio)
- Multi-language support expansion (French, Arabic)
- HIPAA-compliant data handling for production

---

## License

MIT License
