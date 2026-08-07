import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    owner_username: str
    owner_password_hash: str
    llm_provider: str
    gemini_api_key: str
    gemini_model: str
    openai_api_key: str
    openai_model: str
    anthropic_api_key: str
    anthropic_model: str
    groq_api_key: str
    groq_model: str
    ollama_base_url: str
    ollama_model: str
    llm_timeout_seconds: float
    database_url: str
    memory_window_messages: int
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    jarvis_data_dir: str
    jarvis_log_dir: str
    jarvis_screenshot_dir: str


def get_settings() -> Settings:
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
    owner_username = os.getenv("JARVIS_OWNER_USERNAME", "")
    owner_password_hash = os.getenv("JARVIS_OWNER_PASSWORD_HASH", "")

    if not jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is required in environment.")
    if not owner_username:
        raise RuntimeError("JARVIS_OWNER_USERNAME is required in environment.")
    if not owner_password_hash:
        raise RuntimeError("JARVIS_OWNER_PASSWORD_HASH is required in environment.")

    return Settings(
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        owner_username=owner_username,
        owner_password_hash=owner_password_hash,
        llm_provider=os.getenv("LLM_PROVIDER", "gemini"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./jarvis.db"),
        memory_window_messages=int(os.getenv("MEMORY_WINDOW_MESSAGES", "12")),
        supabase_url=os.getenv("SUPABASE_URL", ""),
        supabase_anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        jarvis_data_dir=os.getenv("JARVIS_DATA_DIR", "./data"),
        jarvis_log_dir=os.getenv("JARVIS_LOG_DIR", "./data/logs"),
        jarvis_screenshot_dir=os.getenv("JARVIS_SCREENSHOT_DIR", "./data/screenshots"),
    )
