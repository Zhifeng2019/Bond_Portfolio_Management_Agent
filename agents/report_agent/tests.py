"""Tests for the report agent.

Tests the tool layer, issuer resolution, skill loading, and API schemas.
LLM calls are not tested here (require API key) but the full pipeline
around them is verified.

Run: PYTHONPATH=/home/claude python report_agent/tests.py
"""

from __future__ import annotations

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report_agent.data_tools import TOOL_FUNCTIONS, get_llm_tool_schemas
from report_agent.agent import resolve_issuer, _load_skill
from report_agent.config import SKILL_DIR
from pathlib import Path


def test_skill_loads():
    """SKILL.md and all references load into the system prompt."""
    prompt = _load_skill()
    assert "<skill>" in prompt, "Missing <skill> tag"
    assert "<report_css>" in prompt, "Missing <report_css> tag"
    assert "<html_reference>" in prompt, "Missing <html_reference> tag"
    assert "<api_reference>" in prompt, "Missing <api_reference> tag"
    assert "var(--tx2)" in prompt, "CSS variables not in prompt"
    assert "Chart.js" in prompt or "chart.js" in prompt, "Chart.js reference missing"
    print(f"  ✓ skill loaded ({len(prompt):,} chars)")


def test_skill_files_exist():
    """All skill folder files are present."""
    d = Path(SKILL_DIR)
    assert (d / "SKILL.md").exists()
    assert (d / "assets" / "report_styles.css").exists()
    assert (d / "references" / "html_format.md").exists()
    assert (d / "references" / "api_reference.md").exists()
    print("  ✓ skill files complete")


def test_tool_schemas():
    """LLM tool schemas are well-formed."""
    schemas = get_llm_tool_schemas()
    assert len(schemas) == 9
    names = {s["name"] for s in schemas}
    for expected in ["list_issuers", "get_financials", "get_credit_ratings",
                     "get_spread_history", "get_risk_decomposition", "get_peer_comparison",
                     "get_bonds", "get_pd_term_structure", "get_issuer_profile"]:
        assert expected in names, f"Missing tool: {expected}"
    for s in schemas:
        assert "input_schema" in s
        assert "description" in s
        assert len(s["description"]) > 10
    print(f"  ✓ {len(schemas)} tool schemas valid")


async def test_all_tools():
    """Every tool executes with mock data."""
    for name, fn in TOOL_FUNCTIONS.items():
        if name == "list_issuers":
            result = await fn()
        else:
            result = await fn(issuer_id="AAPL")
        assert result is not None, f"Tool {name} returned None"
    print(f"  ✓ all {len(TOOL_FUNCTIONS)} tools execute")


async def test_tool_data_shapes():
    """Verify returned data has the expected structure."""
    issuers = await TOOL_FUNCTIONS["list_issuers"]()
    assert len(issuers) == 5
    assert all("id" in i and "name" in i for i in issuers)

    ratings = await TOOL_FUNCTIONS["get_credit_ratings"](issuer_id="AAPL")
    assert len(ratings) == 4
    assert all("rating" in r and "date" in r for r in ratings)

    pd = await TOOL_FUNCTIONS["get_pd_term_structure"](issuer_id="MSFT")
    assert "current_curve" in pd and "historical" in pd
    assert len(pd["historical"]) == 24

    fins = await TOOL_FUNCTIONS["get_financials"](issuer_id="JPM")
    assert len(fins) == 4
    assert all("revenue" in f and "ebitda" in f for f in fins)

    bonds = await TOOL_FUNCTIONS["get_bonds"](issuer_id="TSLA")
    assert len(bonds) == 6
    assert all("isin" in b and "coupon" in b for b in bonds)

    spreads = await TOOL_FUNCTIONS["get_spread_history"](issuer_id="GS")
    assert len(spreads) == 365

    risk = await TOOL_FUNCTIONS["get_risk_decomposition"](issuer_id="AAPL")
    assert "contributions_pct" in risk and "trend_6m" in risk
    assert len(risk["contributions_pct"]) == 7

    peers = await TOOL_FUNCTIONS["get_peer_comparison"](issuer_id="AAPL")
    assert len(peers) == 5
    assert peers[0]["issuer_id"] == "AAPL"

    print("  ✓ all data shapes correct")


async def test_issuer_resolution():
    """Issuer name/ticker matching from natural language."""
    assert await resolve_issuer("AAPL") == "AAPL"
    assert await resolve_issuer("Analyze Apple") == "AAPL"
    assert await resolve_issuer("report for Tesla") == "TSLA"
    assert await resolve_issuer("Goldman Sachs risk analysis") == "GS"
    assert await resolve_issuer("JPM credit") == "JPM"
    assert await resolve_issuer("microsoft report") == "MSFT"
    assert await resolve_issuer("unknown_xyz_corp") is None
    print("  ✓ issuer resolution")


async def test_tool_results_serializable():
    """All tool results are JSON-serializable (required for LLM tool_result)."""
    import json
    for name, fn in TOOL_FUNCTIONS.items():
        if name == "list_issuers":
            result = await fn()
        else:
            result = await fn(issuer_id="AAPL")
        serialized = json.dumps(result, default=str)
        assert len(serialized) > 0
    print("  ✓ all tool results JSON-serializable")


async def main():
    print("\n=== Credit Report Agent — Test Suite ===\n")

    print("Skill tests:")
    test_skill_files_exist()
    test_skill_loads()

    print("\nTool tests:")
    test_tool_schemas()
    await test_all_tools()
    await test_tool_data_shapes()
    await test_tool_results_serializable()

    print("\nAgent tests:")
    await test_issuer_resolution()

    print("\n=== All tests passed ✓ ===\n")


if __name__ == "__main__":
    asyncio.run(main())
