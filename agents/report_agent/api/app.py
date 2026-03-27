"""FastAPI application and routes.

Endpoints:
  POST /api/agent/token     — get a JWT Bearer token
  GET  /api/agent/issuers   — list available issuers
  POST /api/agent/report    — generate a report (structured request)
  POST /api/agent/chat      — chat with the agent (natural language)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from report_agent.config import SECRET_KEY, DEMO_USERS
from report_agent.agent import run_agent, resolve_issuer
from report_agent.data_tools import TOOL_FUNCTIONS

# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(title="Credit Report Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ─────────────────────────────────────────────────────────────────

security = HTTPBearer()


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _create_token(username: str) -> str:
    payload = {"sub": username, "exp": datetime.now(timezone.utc) + timedelta(hours=8)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def _verify_token(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub", "")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


@app.post("/api/agent/token", response_model=TokenResponse)
async def login(req: TokenRequest):
    if req.username not in DEMO_USERS or DEMO_USERS[req.username] != req.password:
        raise HTTPException(401, "Invalid credentials")
    return TokenResponse(access_token=_create_token(req.username))


# ── Data endpoints ───────────────────────────────────────────────────────

@app.get("/api/agent/issuers")
async def list_issuers(_user: str = Depends(_verify_token)):
    return await TOOL_FUNCTIONS["list_issuers"]()


# ── Report generation ────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    issuer_id: str
    additional_instructions: str | None = None


class ReportResponse(BaseModel):
    issuer_id: str
    issuer_name: str
    report_html: str
    generated_at: str
    tool_log: list[dict] | None = None
    llm_calls: int | None = None


@app.post("/api/agent/report", response_model=ReportResponse)
async def generate_report(req: ReportRequest, _user: str = Depends(_verify_token)):
    """Generate a report via the LLM agent."""
    prompt = f"Create a credit analysis report for issuer {req.issuer_id}."
    if req.additional_instructions:
        prompt += f" {req.additional_instructions}"

    result = await run_agent(prompt)

    if not result["report_html"]:
        raise HTTPException(500, result["message"])

    profile = await TOOL_FUNCTIONS["get_issuer_profile"](issuer_id=req.issuer_id)
    name = profile["name"] if profile else req.issuer_id

    return ReportResponse(
        issuer_id=req.issuer_id.upper(),
        issuer_name=name,
        report_html=result["report_html"],
        generated_at=datetime.now(timezone.utc).isoformat(),
        tool_log=result["tool_log"],
        llm_calls=result["llm_calls"],
    )


# ── Chat interface ───────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    type: str            # "text" or "report"
    content: str         # agent's text message
    issuer_id: str | None = None
    issuer_name: str | None = None
    report_html: str | None = None
    generated_at: str | None = None
    tool_log: list[dict] | None = None


@app.post("/api/agent/chat", response_model=ChatResponse)
async def agent_chat(req: ChatRequest, _user: str = Depends(_verify_token)):
    """Chat endpoint — natural language in, report or text out."""
    msg = req.message.strip()
    msg_lower = msg.lower()

    # Intent: list issuers
    if any(kw in msg_lower for kw in ["list", "available", "issuers", "help", "which"]):
        issuers = await TOOL_FUNCTIONS["list_issuers"]()
        lines = [f"• **{i['ticker']}** – {i['name']} ({i['sector']})" for i in issuers]
        return ChatResponse(
            type="text",
            content="Here are the available issuers:\n\n" + "\n".join(lines)
                    + "\n\nTell me which issuer you'd like me to analyze.",
        )

    # Intent: generate report — run the LLM agent
    result = await run_agent(msg)

    if result["report_html"]:
        issuer_id = await resolve_issuer(msg)
        issuer_name = ""
        if issuer_id:
            profile = await TOOL_FUNCTIONS["get_issuer_profile"](issuer_id=issuer_id)
            issuer_name = profile["name"] if profile else issuer_id

        return ChatResponse(
            type="report",
            content=result["message"],
            issuer_id=issuer_id,
            issuer_name=issuer_name,
            report_html=result["report_html"],
            generated_at=datetime.now(timezone.utc).isoformat(),
            tool_log=result["tool_log"],
        )

    # Fallback: return the agent's text response
    return ChatResponse(type="text", content=result["message"])


# ── Health ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}
