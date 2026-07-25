# AI Voice Agent — MediBook Clinic

An AI-powered voice receptionist that handles inbound calls, collects patient information, and books medical appointments — all through natural voice conversation.

Built as a demonstration of a production-ready Voice AI Agent using Vapi, Groq (Llama 3.3), FastAPI, and SQLite.

---

## Demo

**Live Backend:** https://ai-appointment-voice-agent.onrender.com  
**Appointments API:** https://ai-appointment-voice-agent.onrender.com/appointments

---

## How It Works

```
Patient calls → Vapi (telephony + STT + TTS)
                     ↓
             FastAPI Backend (webhook)
                     ↓
         Groq LLM (Llama 3.3-70b-versatile)
                     ↓
         book_appointment() function call
                     ↓
            SQLite Database (saved)
```

### Conversation Flow

1. AI greets the patient
2. Collects full name
3. Collects phone number
4. Asks for reason / symptoms
5. Asks for preferred date
6. Asks for preferred time
7. Confirms all details
8. Books the appointment (saves to DB)
9. Says goodbye

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Voice / Telephony | [Vapi](https://vapi.ai) |
| Speech to Text | Soniox (via Vapi) |
| LLM | Groq — Llama 3.3-70b-versatile |
| Text to Speech | Vapi built-in |
| Backend | FastAPI (Python) |
| Database | SQLite |
| Hosting | Render |

---

## Project Structure

```
AI-Voice Agent/
├── main.py          # FastAPI app entry point, DB init
├── routes.py        # API endpoints (/webhook, /vapi-function, /chat, /appointments)
├── agent.py         # Groq LLM integration + function calling logic
├── database.py      # SQLite setup + CRUD operations
├── test_agent.py    # Local terminal test (no Vapi needed)
├── requirements.txt # Python dependencies
├── render.yaml      # Render deployment config
├── .python-version  # Python 3.11.9
└── .env.example     # Environment variable template
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| POST | `/webhook` | Vapi webhook — receives call events |
| POST | `/vapi-function` | Vapi function server — executes `book_appointment` |
| POST | `/chat` | Text-based chat for testing (no phone needed) |
| GET | `/appointments` | List all booked appointments |
| DELETE | `/appointments/{id}` | Cancel an appointment |

---

## Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/Tahha2003/AI-Appointment-Voice-Agent.git
cd AI-Appointment-Voice-Agent
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
copy .env.example .env
```
Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=gsk_your-key-here
```
Get a free key at: https://console.groq.com

### 5. Run the server
```bash
python main.py
```
Server starts at: http://localhost:8000

### 6. Test in terminal (no phone needed)
```bash
python test_agent.py
```

### 7. Test via API
```bash
# Text chat test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test1", "message": "Hello, I want an appointment"}'

# View all appointments
curl http://localhost:8000/appointments
```

---

## Deployment (Render)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New Web Service
3. Connect your GitHub repo
4. Set environment variables:
   - `GROQ_API_KEY` = your Groq key
   - `DB_PATH` = `/tmp/appointments.db`
5. Build command: `pip install -r requirements.txt`
6. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Deploy → get your live URL

---

## Vapi Setup

1. Sign up at [vapi.ai](https://vapi.ai)
2. Create an Assistant:
   - First Message: `Hello! Welcome to MediBook Clinic. How can I help you?`
   - Model: Groq → llama-3.3-70b-versatile
   - Server URL (Advanced tab): `https://your-url.onrender.com/webhook`
3. Create a Tool named `book_appointment`:
   - Server URL: `https://your-url.onrender.com/vapi-function`
   - Add the parameters (patient_name, phone, reason, date, time)
4. Attach the tool to your assistant
5. Get a phone number or use the browser Talk button to test

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GROQ_API_KEY` | Groq API key (free at console.groq.com) | ✅ |
| `VAPI_API_KEY` | Vapi API key | Optional |
| `DB_PATH` | SQLite database path | Optional (default: `appointments.db`) |
| `BACKEND_URL` | Your deployed backend URL | Optional |
