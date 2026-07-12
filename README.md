# JARVIS API

Secure FastAPI service with single-owner JWT authentication.

## 1) Activate the virtual environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 2) Create owner password hash

```powershell
python .\scripts\generate_password_hash.py
```

Copy the generated hash and put it in `.env`.

## 3) Create environment file

```powershell
Copy-Item .env.example .env
```

Set:
- `JWT_SECRET_KEY` to a strong random secret.
- `JARVIS_OWNER_USERNAME` to your username.
- `JARVIS_OWNER_PASSWORD_HASH` to the generated password hash.
- `GEMINI_API_KEY` for Gemini access.

## 4) Run the server

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 5) Get token and call the protected entry point

Get token:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/auth/token" `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=<your-username>&password=<your-password>"
```

Use token:

```powershell
curl.exe "http://127.0.0.1:8000/" -H "Authorization: Bearer <access_token>"
```

Call Jarvis chat endpoint:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/chat" `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d "{\"text\":\"Hello Jarvis, introduce yourself.\"}"
```

Continue the same conversation by reusing returned `session_id`:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/chat" `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d "{\"session_id\":\"<session_id>\",\"text\":\"Remember what I said earlier?\"}"
```

## Async LLM Service (abstracted)

The codebase includes an async provider-agnostic LLM layer in `app/services/llm.py`.

- `AsyncLLMService` defines the interface.
- Implementations included: `GeminiService`, `OpenAIService`, `AnthropicService`, `GroqService`, `OllamaService`.
- `get_llm_service(settings)` returns a provider instance based on `LLM_PROVIDER`.

This keeps model integrations out of routes and allows swapping providers later.

Supported `LLM_PROVIDER` values:
- `gemini`
- `openai`
- `anthropic`
- `groq`
- `ollama`

Conversation memory settings:
- `DATABASE_URL` (default `sqlite:///./jarvis.db`)
- `MEMORY_WINDOW_MESSAGES` controls how many recent messages are used as context.

## Supabase Setup (Postgres)

1. Create a free project in [Supabase](https://supabase.com/dashboard/projects).
2. In your project, go to **Settings -> Database** and copy the pooler connection string.
3. Put that value into `DATABASE_URL` in `.env` using `postgresql+psycopg://...&sslmode=require`.
4. Add project API values from **Settings -> API**:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
5. Restart the API. Tables are auto-created by SQLModel on startup.

## Data Schema

SQLModel entities are defined in `app/models/entities.py`:
- `User`
- `ChatSession`
- `Message`

## Chat History Endpoints

All endpoints require bearer auth.

- `POST /chat` saves new turns to `Message` and updates `ChatSession`.
- `GET /chat/sessions` returns all sessions for owner.
- `GET /chat/sessions/{session_id}/messages` returns message history for that session.
