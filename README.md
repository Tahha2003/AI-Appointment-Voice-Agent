# MediBook Voice Agent
### AI-powered voice receptionist that registers patients through natural phone conversations.

---

## 🚀 Features

- **Voice Patient Registration** — Patients call in, AI collects full demographic info conversationally
- **18-Field Data Model** — Covers all standard US healthcare patient demographics
- **Input Validation** — Server-side validation for every field (phone, DOB, state, ZIP, etc.)
- **Duplicate Detection** — Recognizes returning callers by phone number, offers to update record
- **Soft Delete** — Patient records are never hard-deleted, only marked with `deleted_at`
- **Full REST API** — CRUD endpoints with consistent JSON envelope and proper HTTP codes
- **LLM-Powered** — Groq Llama 3.3-70b for fast, natural conversation (free tier)
- **Text Testing** — Built-in `/chat` endpoint to test AI without a phone call

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice / Telephony | [Vapi](https://vapi.ai) |
| Speech to Text | Soniox (via Vapi) |
| LLM | Groq — Llama 3.3-70b-versatile (free) |
| Text to Speech | Vapi built-in |
| Backend | FastAPI (Python 3.11) |
| Database | SQLite |
| Hosting | Render |

---

## 📦 Project Structure

```
AI-Voice Agent/
├── main.py          # FastAPI entry point, DB init, lifespan
├── routes.py        # All API endpoints
│   ├── GET/POST/PUT/DELETE /patients
│   ├── POST /webhook          (Vapi call events)
│   ├── POST /vapi-function    (Vapi tool execution)
│   └── POST /chat             (text testing)
├── agent.py         # Groq LLM + function calling logic
│   ├── register_patient() tool
│   └── update_patient() tool
├── database.py      # SQLite schema, validation, CRUD
├── test_agent.py    # Terminal chat test (no phone needed)
├── requirements.txt
├── render.yaml      # Render deployment config
├── .python-version  # 3.11.9
└── .env.example
```

---

## 🗂️ Patient Data Model

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| patient_id | UUID | Auto | Auto-generated |
| first_name | String | ✅ | 1-50 chars, alpha + hyphens/apostrophes |
| last_name | String | ✅ | Same as first_name |
| date_of_birth | String | ✅ | MM/DD/YYYY, not in future |
| sex | Enum | ✅ | Male / Female / Other / Decline to Answer |
| phone_number | String | ✅ | US 10-digit (formatted or raw) |
| email | String | — | Valid email format |
| address_line_1 | String | ✅ | Street address |
| address_line_2 | String | — | Apt/Suite |
| city | String | ✅ | 1-100 chars |
| state | String | ✅ | Valid 2-letter US abbreviation |
| zip_code | String | ✅ | 5-digit or ZIP+4 |
| insurance_provider | String | — | Company name |
| insurance_member_id | String | — | Alphanumeric ID |
| preferred_language | String | — | Default: English |
| emergency_contact_name | String | — | Full name |
| emergency_contact_phone | String | — | US 10-digit |
| created_at | Timestamp | Auto | UTC |
| updated_at | Timestamp | Auto | UTC |
| deleted_at | Timestamp | Auto | NULL = active (soft delete) |

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
| POST | `/patients` | Create patient (returns 409 on duplicate phone) |
| PUT | `/patients/{id}` | Partial update |
| DELETE | `/patients/{id}` | Soft delete |

### Voice
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook` | Vapi call lifecycle events |
| POST | `/vapi-function` | Vapi tool execution |

### Testing
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check + endpoint map |
| POST | `/chat` | Text-based AI chat (no phone needed) |
| DELETE | `/chat/{session_id}` | Clear session |

### Response Format
All endpoints return:
```json
{ "data": {...}, "error": null }
```

HTTP codes: `200`, `201`, `400`, `404`, `409`, `422`, `500`

---

## 🏃‍♂️ Quick Start

### 1. Clone & setup
```bash
git clone https://github.com/Tahha2003/AI-Appointment-Voice-Agent.git
cd AI-Appointment-Voice-Agent

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt

copy .env.example .env
# Add your GROQ_API_KEY to .env
```

### 2. Run server
```bash
python main.py
# → http://localhost:8000
```

### 3. Test in terminal (no phone needed)
```bash
python test_agent.py
```

### 4. Test API
```bash
# Health check
curl http://localhost:8000/

# List patients (2 seed records included)
curl http://localhost:8000/patients

# Text chat test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test1", "message": "Hello"}'

# Create patient
curl -X POST http://localhost:8000/patients \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "date_of_birth": "01/15/1985",
    "sex": "Male",
    "phone_number": "5550001234",
    "address_line_1": "789 Pine Street",
    "city": "Chicago",
    "state": "IL",
    "zip_code": "60601"
  }'
```

---

## 🔧 Environment Variables

```env
# Required
GROQ_API_KEY=gsk_your-groq-key-here   # free at console.groq.com

# Optional
VAPI_API_KEY=your-vapi-key-here
DB_PATH=/tmp/patients.db               # use /tmp on Render
BACKEND_URL=https://your-app.onrender.com
```

---

## 🚢 Deployment (Render)

1. Push to GitHub
2. [render.com](https://render.com) → New Web Service → connect repo
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Env vars: `GROQ_API_KEY`, `DB_PATH=/tmp/patients.db`

Live URL: `https://ai-appointment-voice-agent.onrender.com`

---

## 📞 Vapi Configuration

1. [vapi.ai](https://vapi.ai) → Create Assistant
2. **First Message:** `Hello! Thank you for calling MediBook Clinic. I'm here to help register you as a new patient. May I start with your first name?`
3. **Model:** Groq → `llama-3.3-70b-versatile`
4. **Advanced → Server URL:** `https://your-url.onrender.com/webhook`
5. **Tools:** Create `register_patient` and `update_patient` tools
   - Server URL: `https://your-url.onrender.com/vapi-function`
6. **Publish** → use browser **Talk** button to test

> Note: Vapi US phone number provisioning is not available for all regions.
> The browser-based Talk button is fully functional for testing and demo purposes.

---

## 🔁 How It Works

```
Patient calls → Vapi (STT: voice → text)
                    ↓
              POST /webhook
                    ↓
          Groq Llama 3.3 (LLM)
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
```

---

## 🔐 Security

- API keys in environment variables only — never in source code
- `.env` excluded from git via `.gitignore`
- Server-side input validation on all endpoints
- Soft delete — records preserved, never hard-deleted
- HTTPS enforced on Render

---

## ⚠️ Known Limitations & Trade-offs

- **SQLite on Render** — data persists across requests but resets on redeploy (use `DB_PATH=/tmp/patients.db`)
- **No authentication** — API endpoints are open; production would require API key or JWT
- **No HIPAA compliance** — this is a technical demo, not a production healthcare system
- **Phone number not provisioned** — Vapi US numbers not available in all regions; browser Talk button used for demo

---

## 🔮 Next Steps

- Add JWT authentication to REST API
- Migrate to PostgreSQL (Supabase) for persistent cloud storage
- Add call transcript storage linked to patient record
- Implement appointment scheduling after registration
- Add multi-language support (Spanish via `Hablo español` trigger)
- Dashboard UI to view registered patients

---

## 📄 License

MIT License

## 🤝 Contributing

Pull requests welcome.
