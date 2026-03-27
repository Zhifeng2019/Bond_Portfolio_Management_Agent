"""Data tools — callable functions the LLM agent invokes via tool_use.

Each tool either serves mock data or calls the real backend API,
controlled by USE_MOCK in config.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from report_agent.config import USE_MOCK, API_BASE_URL, API_TOKEN


# ── Execution layer ──────────────────────────────────────────────────────

async def _api_get(path: str) -> Any:
    """Call the real backend API."""
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{API_BASE_URL}{path}", headers=headers)
        resp.raise_for_status()
        return resp.json()


# ── Tool functions ───────────────────────────────────────────────────────

async def list_issuers() -> list[dict]:
    """List all available bond issuers."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import list_issuers as f
        return f()
    return await _api_get("/api/data/issuers")


async def get_issuer_profile(issuer_id: str) -> dict | None:
    """Get basic profile of an issuer."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import ISSUERS
        iid = issuer_id.upper()
        info = ISSUERS.get(iid)
        return {**info, "id": iid} if info else None
    data = await _api_get(f"/api/data/issuers/{issuer_id}")
    return data.get("issuer")


async def get_credit_ratings(issuer_id: str) -> list[dict]:
    """Fetch credit rating history for an issuer."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import get_rating_history
        return get_rating_history(issuer_id)
    return await _api_get(f"/api/data/issuers/{issuer_id}/ratings")


async def get_pd_term_structure(issuer_id: str) -> dict:
    """Fetch PD term structure and historical PD."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import get_pd_data
        return get_pd_data(issuer_id)
    return await _api_get(f"/api/data/issuers/{issuer_id}/pd")


async def get_financials(issuer_id: str) -> list[dict]:
    """Fetch annual financial statements."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import get_financials as f
        return f(issuer_id)
    return await _api_get(f"/api/data/issuers/{issuer_id}/financials")


async def get_bonds(issuer_id: str) -> list[dict]:
    """Fetch outstanding bonds of an issuer."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import get_bonds as f
        return f(issuer_id)
    return await _api_get(f"/api/data/issuers/{issuer_id}/bonds")


async def get_spread_history(issuer_id: str) -> list[dict]:
    """Fetch 12-month daily credit spread history."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import get_spread_history as f
        return f(issuer_id)
    return await _api_get(f"/api/data/issuers/{issuer_id}/spreads")


async def get_risk_decomposition(issuer_id: str) -> dict:
    """Fetch risk factor breakdown and 6-month trends."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import get_risk_decomposition as f
        return f(issuer_id)
    return await _api_get(f"/api/data/issuers/{issuer_id}/risk-decomposition")


async def get_peer_comparison(issuer_id: str) -> list[dict]:
    """Get peer comparison table for an issuer vs sector peers."""
    if USE_MOCK:
        from report_agent.mock_data.mock_issuer_data import get_peer_comparison as f
        return f(issuer_id)
    return await _api_get(f"/api/data/issuers/{issuer_id}/peers")


# ── Registry: maps tool names to (function, LLM schema) ─────────────────

TOOL_FUNCTIONS: dict[str, Any] = {
    "list_issuers": list_issuers,
    "get_issuer_profile": get_issuer_profile,
    "get_credit_ratings": get_credit_ratings,
    "get_pd_term_structure": get_pd_term_structure,
    "get_financials": get_financials,
    "get_bonds": get_bonds,
    "get_spread_history": get_spread_history,
    "get_risk_decomposition": get_risk_decomposition,
    "get_peer_comparison": get_peer_comparison,
}

def get_llm_tool_schemas() -> list[dict]:
    """Return Anthropic API tool definitions."""
    _issuer_param = {
        "type": "object",
        "properties": {"issuer_id": {"type": "string", "description": "Ticker symbol, e.g. AAPL"}},
        "required": ["issuer_id"],
    }
    return [
        {"name": "list_issuers", "description": "List all available bond issuers with name, sector, country, ticker.", "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "get_issuer_profile", "description": "Get basic profile of a bond issuer: name, sector, country, ticker.", "input_schema": _issuer_param},
        {"name": "get_credit_ratings", "description": "Fetch credit rating history. Returns [{date, rating, agency, outlook}].", "input_schema": _issuer_param},
        {"name": "get_pd_term_structure", "description": "Fetch PD term structure (current curve) and historical PD (24 months of pd_1y, pd_5y). PD values are raw decimals.", "input_schema": _issuer_param},
        {"name": "get_financials", "description": "Fetch 4 years of annual financials: revenue, net_income, total_assets, total_debt, equity, ebitda, interest_expense, cash, operating_cf. Values in raw dollars.", "input_schema": _issuer_param},
        {"name": "get_bonds", "description": "Fetch outstanding bonds: isin, coupon, maturity, face_value, currency, issue_size_mm, price, ytm, spread_bps, modified_duration.", "input_schema": _issuer_param},
        {"name": "get_spread_history", "description": "Fetch 12-month daily credit spread history. Returns [{date, spread_bps}]. Sample every 7th point for charts.", "input_schema": _issuer_param},
        {"name": "get_risk_decomposition", "description": "Fetch risk factor contributions (%) and 6-month trends. Positive trend = worsening.", "input_schema": _issuer_param},
        {"name": "get_peer_comparison", "description": "Peer comparison: [{issuer_id, name, rating, leverage, interest_coverage, profit_margin_pct, debt_to_equity}]. Target issuer first.", "input_schema": _issuer_param},
    ]
