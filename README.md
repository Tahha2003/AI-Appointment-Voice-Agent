# AI Voice Agent — Appointment Booking
### CareCloud-Style Medical Receptionist

---

## Architecture

```
Phone Call → Vapi → POST /webhook → FastAPI → OpenAI GPT-4o-mini
                                       ↓
                                   book_appointment()
                                       ↓
                                   SQLite (appointments.db)
```

## Project Structure

```
AI-Voice Agent/
├── main.py          # FastAPI app entry point
├── routes.py        # All API endpoints (/webhook, /chat, /appointments)
├── agent.py         # OpenAI integration + function calling logic
├── database.py      # SQLite setup + CRUD functions
├── test_agent.py    # Local terminal test (no Vapi needed)
├── requirements.txt
├── render.yaml      # Render deployment config
└── .env.example     # Copy to .env and fill keys
```

## Quick Start

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Set up environment variables
```bash
copy .env.example .env
# Now open .env and add your OPENAI_API_KEY
```

### Step 3 — Run locally
```bash
python main.py
```
Server runs at: http://localhost:8000

### Step 4 — Test without phone call
```bash
python test_agent.py
```

### Step 5 — Test API manually
```bash
# Text chat test
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test1", "message": "Hello"}'

# View appointments
curl http://localhost:8000/appointments
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Health check |
| POST | /webhook | Vapi webhook (voice events) |
| POST | /vapi-function | Vapi function server |
| POST | /chat | Text-based AI chat (testing) |
| GET | /appointments | List all appointments |
| DELETE | /appointments/{id} | Cancel appointment |

---

## Deployment (Render)

1. Push code to GitHub
2. Go to render.com → New Web Service
3. Connect GitHub repo
4. Add environment variables: `OPENAI_API_KEY`, `VAPI_API_KEY`
5. Deploy → Copy your URL (e.g. `https://ai-voice-agent.onrender.com`)

---

## Vapi Setup

1. Go to vapi.ai → Sign up
2. Create a new Assistant
3. Set Server URL to: `https://your-url.onrender.com/webhook`
4. Get a phone number from Vapi dashboard
5. Call the number and talk to your AI!
