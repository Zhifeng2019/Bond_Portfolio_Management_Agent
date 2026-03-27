"""Configuration — all toggles and secrets in one place."""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Mock toggle: True = mock data, False = call real backend APIs ──
USE_MOCK: bool = os.getenv("USE_MOCK", "true").lower() == "true"

# ── Backend API (used when USE_MOCK=False) ──
API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TOKEN: str = os.getenv("API_TOKEN", "")  # Bearer token for data APIs

# ── LLM ──
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "16000"))
MAX_TOOL_ROUNDS: int = int(os.getenv("MAX_TOOL_ROUNDS", "10"))

# ── Auth (for the agent's own endpoints) ──
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
DEMO_USERS: dict[str, str] = {"analyst": "analyst123"}

# ── Skill location ──
SKILL_DIR: str = os.getenv(
    "SKILL_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "skills", "bond-issuer-report-skill"),
)
