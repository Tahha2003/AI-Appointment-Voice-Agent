# MediBook Voice Agent
### An AI-powered voice receptionist that books medical appointments through natural phone conversations.

---

## 🚀 Features

- **Voice Appointment Booking** — Patients call in and the AI collects all required information conversationally
- **Natural Language Understanding** — Powered by Groq's Llama 3.3-70b for human-like responses
- **Function Calling** — AI automatically triggers `book_appointment` when all data is collected
- **Persistent Storage** — All appointments saved to SQLite database
- **REST API** — View, manage, and cancel appointments via API endpoints
- **Text-based Testing** — Built-in terminal chat to test AI without a phone call
- **Fast & Free** — Groq free tier, no credit card needed for the AI layer

---

## 🛠️ Tech Stack

**Voice & Telephony**
- [Vapi](https://vapi.ai) — Inbound call handling, STT, TTS
- Soniox — Speech-to-text transcription
- Vapi TTS — Text-to-speech voice output

**AI / LLM**
- [Groq](https://console.groq.com) — Ultra-fast inference
- Llama 3.3-70b-versatile — Conversation + function calling

**Backend**
- Python 3.11
- FastAPI — REST API framework
- SQLite — Lightweight database
- Uvicorn — ASGI server

**Deployment**
- [Render](https://render.com) — Cloud hosting

---

## 📦 Project Structure

```
AI-Voice Agent/
├── main.py          # FastAPI app entry point, lifespan, DB init
├── routes.py        # All API endpoints
│   ├── POST /webhook          # Vapi call events
│   ├── POST /vapi-function    # Vapi function execution
│   ├── POST /chat             # Text chat for testing
│   ├── GET  /appointments     # List appointments
│   └── DELETE /appointments/{id}
├── agent.py         # Groq LLM + function calling logic
├── database.py      # SQLite connection + CRUD operations
├── test_agent.py    # Local terminal test (no phone needed)
├── requirements.txt
├── render.yaml      # Render deployment config
├── .python-version  # Python 3.11.9
└── .env.example     # Environment variable template
```

---

## 🏃‍♂️ Quick Start

### Prerequisites
- Python 3.11+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Setup

```bash
# Clone the repository
git clone https://github.com/Tahha2003/AI-Appointment-Voice-Agent.git
cd AI-Appointment-Voice-Agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
copy .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### Run the server

```bash
python main.py
```

Server starts at: `http://localhost:8000`

### Test in terminal (no phone needed)

```bash
python test_agent.py
```

```
🤖 AI: Hello! Welcome to MediBook Clinic. How can I help you?
👤 You: I want to book an appointment
🤖 AI: Sure! May I know your full name?
👤 You: John Smith
...
✅ Appointment Booked!
   Patient : John Smith
   Phone   : 0300-1234567
   Reason  : Fever and headache
   Date    : Tomorrow
   Time    : 3:00 PM
   Doctor  : Dr. Smith
```

---

## 📋 API Endpoints

### General
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |

### Voice (Vapi)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook` | Vapi webhook — receives all call events |
| POST | `/vapi-function` | Executes `book_appointment` function |

### Testing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Text-based AI chat (no phone needed) |
| DELETE | `/chat/{session_id}` | Clear a conversation session |

### Appointments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/appointments` | List all booked appointments |
| DELETE | `/appointments/{id}` | Cancel an appointment |

---

## 🔧 Environment Variables

**`.env`**
```env
# Groq API Key (free at https://console.groq.com)
GROQ_API_KEY=gsk_your-key-here

# Vapi API Key (from https://vapi.ai)
VAPI_API_KEY=your-vapi-key-here

# Database path (/tmp/appointments.db on Render)
DB_PATH=appointments.db

# Your deployed backend URL
BACKEND_URL=https://ai-appointment-voice-agent.onrender.com
```

---

## 🔁 How It Works

```
Patient calls number
        ↓
   Vapi receives call
   (STT converts voice → text)
        ↓
   POST /webhook
   (FastAPI backend)
        ↓
   Groq LLM processes message
   (Llama 3.3-70b-versatile)
        ↓
   AI collects: name → phone → reason → date → time
        ↓
   AI triggers book_appointment()
        ↓
   POST /vapi-function
        ↓
   Saved to SQLite database
        ↓
   Confirmation spoken to patient
   (TTS converts text → voice)
```

---

## 🚢 Deployment

### Render (Recommended)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables:
   - `GROQ_API_KEY` → your Groq key
   - `DB_PATH` → `/tmp/appointments.db`
6. Click **Deploy**

Live URL format: `https://your-service-name.onrender.com`

---

## 📞 Vapi Configuration

1. Sign up at [vapi.ai](https://vapi.ai)
2. **Create Assistant:**
   - First Message: `Hello! Welcome to MediBook Clinic. How can I help you?`
   - Model: Groq → `llama-3.3-70b-versatile`
   - Advanced → Server URL: `https://your-url.onrender.com/webhook`
3. **Create Tool** (`book_appointment`):
   - Server URL: `https://your-url.onrender.com/vapi-function`
   - Parameters: `patient_name`, `phone`, `reason`, `date`, `time`
4. Attach tool to assistant → **Publish**
5. Use browser **Talk** button or assign a phone number to test

---

## 🔐 Security

- API keys stored in environment variables (never in code)
- `.env` file excluded from git via `.gitignore`
- Input validation before saving to database
- HTTPS enforced on Render deployment

---

## 📱 Testing the Live API

```bash
# Health check
curl https://ai-appointment-voice-agent.onrender.com/

# View all appointments
curl https://ai-appointment-voice-agent.onrender.com/appointments

# Text chat test
curl -X POST https://ai-appointment-voice-agent.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test1", "message": "Hello, I need an appointment"}'
```

---

## 📄 License

MIT License — feel free to use this project for your own purposes.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
