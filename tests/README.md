# Tests

All test files for the MediBook Voice Agent backend.

## Files

| File | What it tests |
|------|--------------|
| `test_imports.py` | All imports, DB init, seed data, core handlers, language detection |
| `test_validation.py` | All field validators (phone, DOB, state, ZIP, sex, name, email) |
| `test_agent.py` | Interactive terminal chat — simulates a full voice call |

## How to Run

From the project root (`AI-Voice Agent/`):

```bash
# Run all import + integration tests (no LLM calls)
python tests/test_imports.py

# Run validation tests only (fastest, no LLM calls)
python tests/test_validation.py

# Run interactive voice simulation (requires GROQ_API_KEY)
python tests/test_agent.py
```

## Notes

- `test_imports.py` and `test_validation.py` make **no API calls** — they run instantly
- `test_agent.py` uses Groq API — requires `GROQ_API_KEY` in `.env`
- All tests create and clean up their own isolated test databases
