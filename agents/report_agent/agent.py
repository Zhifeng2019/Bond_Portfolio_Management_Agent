"""LLM Agent — agentic tool_use loop powered by the credit-report skill.

Flow:
  1. Load SKILL.md + CSS + html_format.md into the system prompt.
  2. Send user request + tool schemas to the Anthropic Messages API.
  3. Loop: LLM emits tool_use blocks → agent executes them → feeds results back.
  4. LLM produces the final HTML report following the skill instructions.
  5. Agent extracts the HTML from the response and returns it.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from report_agent.config import (
    ANTHROPIC_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, MAX_TOOL_ROUNDS, SKILL_DIR,
)
from report_agent.data_tools import TOOL_FUNCTIONS, get_llm_tool_schemas

logger = logging.getLogger(__name__)


# ── Skill loader ─────────────────────────────────────────────────────────

def _load_skill() -> str:
    """Read the skill folder and compose the system prompt."""
    skill_dir = Path(SKILL_DIR)
    parts: list[str] = []

    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        # Strip YAML frontmatter
        text = skill_md.read_text()
        if text.startswith("---"):
            end = text.index("---", 3)
            text = text[end + 3:].strip()
        parts.append(f"<skill>\n{text}\n</skill>")

    css_file = skill_dir / "assets" / "report_styles.css"
    if css_file.exists():
        parts.append(
            "<report_css>\n"
            "Include this CSS verbatim inside the <style> tag of every report you generate.\n\n"
            f"```css\n{css_file.read_text()}\n```\n"
            "</report_css>"
        )

    html_ref = skill_dir / "references" / "html_format.md"
    if html_ref.exists():
        parts.append(f"<html_reference>\n{html_ref.read_text()}\n</html_reference>")

    api_ref = skill_dir / "references" / "api_reference.md"
    if api_ref.exists():
        parts.append(f"<api_reference>\n{api_ref.read_text()}\n</api_reference>")

    return "\n\n".join(parts)


SYSTEM_TEMPLATE = """You are a credit analysis agent. Your job is to produce self-contained HTML
credit analysis reports for bond issuers.

You have data-fetching tools available. You MUST call them to get real data —
never fabricate numbers. Call all the tools you need FIRST, then write the report.

When writing the HTML report, output ONLY the complete raw HTML document.
Do NOT wrap it in markdown code fences. Do NOT add commentary before or after
the HTML. The output must start with <!DOCTYPE html> and end with </html>.

{skill}

IMPORTANT RULES:
- Call ALL necessary tools BEFORE writing the report. You can call multiple
  tools in a single response.
- The report must be a COMPLETE, self-contained HTML document.
- Use the CSS from <report_css> verbatim inside <style> tags.
- Follow the chart patterns from <html_reference> exactly.
- Every chart canvas needs a unique id. Every chart script in its own IIFE.
- Financial values: display as $X.XB or $X.XM, never raw numbers.
- PD values: multiply raw decimals by 100 and show as X.XXX%.
- For spread history: sample every 7th data point for the chart.
- The HTML MUST include a working light/dark theme toggle.
"""


# ── LLM call ─────────────────────────────────────────────────────────────

async def _call_llm(
    messages: list[dict], system: str, tools: list[dict]
) -> dict:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": LLM_MODEL,
        "max_tokens": LLM_MAX_TOKENS,
        "system": system,
        "messages": messages,
        "tools": tools,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
        )
        resp.raise_for_status()
        return resp.json()


# ── Tool execution ───────────────────────────────────────────────────────

async def _execute_tool(name: str, inputs: dict) -> Any:
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return await fn(**inputs)
    except Exception as exc:
        logger.error("Tool %s failed: %s", name, exc)
        return {"error": str(exc)}


# ── Agentic loop ─────────────────────────────────────────────────────────

async def run_agent(user_message: str) -> dict[str, Any]:
    """Run the full agentic loop.

    Parameters
    ----------
    user_message : str
        The user's request, e.g. "Create a credit report for Apple" or
        "Analyze TSLA focusing only on risk decomposition and financials".

    Returns
    -------
    dict with keys:
        report_html : str — the complete HTML report (empty if generation failed)
        message     : str — agent's text message for the chat UI
        tool_log    : list — tools called during the run
        llm_calls   : int — number of LLM roundtrips
        usage       : dict — token counts
    """
    if not ANTHROPIC_API_KEY:
        return {
            "report_html": "",
            "message": "Error: ANTHROPIC_API_KEY is not set. Cannot run the LLM agent.",
            "tool_log": [],
            "llm_calls": 0,
            "usage": {},
        }

    skill_prompt = _load_skill()
    system = SYSTEM_TEMPLATE.format(skill=skill_prompt)
    tools = get_llm_tool_schemas()

    messages: list[dict] = [{"role": "user", "content": user_message}]

    tool_log: list[dict] = []
    llm_calls = 0
    total_in = 0
    total_out = 0
    content_blocks: list[dict] = []

    for round_num in range(MAX_TOOL_ROUNDS):
        llm_calls += 1
        logger.info("LLM call #%d (round %d)", llm_calls, round_num + 1)

        response = await _call_llm(messages, system, tools)

        total_in += response.get("usage", {}).get("input_tokens", 0)
        total_out += response.get("usage", {}).get("output_tokens", 0)

        stop_reason = response.get("stop_reason", "end_turn")
        content_blocks = response.get("content", [])

        # Append assistant message to conversation
        messages.append({"role": "assistant", "content": content_blocks})

        # If no more tool calls, we're done
        if stop_reason != "tool_use":
            break

        # Execute all tool calls in this response
        tool_results: list[dict] = []
        for block in content_blocks:
            if block.get("type") != "tool_use":
                continue
            tool_name = block["name"]
            tool_input = block.get("input", {})
            tool_id = block["id"]

            logger.info("  → %s(%s)", tool_name, json.dumps(tool_input)[:100])
            result = await _execute_tool(tool_name, tool_input)

            tool_log.append({
                "round": round_num + 1,
                "tool": tool_name,
                "input": tool_input,
                "ok": not (isinstance(result, dict) and "error" in result),
            })

            result_str = json.dumps(result, default=str)
            # Truncate very large responses (spread history = 365 points)
            if len(result_str) > 60000:
                result_str = result_str[:60000] + '..."truncated"}'

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": result_str,
            })

        # Feed tool results back to the LLM
        messages.append({"role": "user", "content": tool_results})

    # ── Extract HTML from final response ─────────────────────────────
    report_html = ""
    text_message = ""

    for block in content_blocks:
        if block.get("type") == "text":
            text = block["text"]
            # Look for the HTML document in the text
            doctype_pos = text.find("<!DOCTYPE html>")
            html_pos = text.find("<html")
            start = doctype_pos if doctype_pos != -1 else html_pos

            if start != -1:
                html_candidate = text[start:]
                end = html_candidate.rfind("</html>")
                if end != -1:
                    report_html = html_candidate[:end + 7]
                else:
                    report_html = html_candidate
                # Any text before the HTML is the agent's message
                text_message += text[:start].strip()
            else:
                text_message += text

    if report_html and not text_message:
        text_message = "Report generated successfully."

    if not report_html and not text_message:
        text_message = "I wasn't able to generate the report. Please try again."

    return {
        "report_html": report_html,
        "message": text_message.strip(),
        "tool_log": tool_log,
        "llm_calls": llm_calls,
        "usage": {"input_tokens": total_in, "output_tokens": total_out},
    }


# ── Issuer resolution helper (used by the API layer) ─────────────────────

async def resolve_issuer(text: str) -> str | None:
    """Best-effort issuer ID extraction from natural language."""
    issuers = await TOOL_FUNCTIONS["list_issuers"]()
    msg_upper = text.strip().upper()
    msg_lower = text.strip().lower()
    words = set(msg_upper.split())

    # Exact ticker
    for iss in issuers:
        t = iss.get("ticker", iss["id"]).upper()
        if msg_upper == t or t in words:
            return iss["id"]

    # Full name
    for iss in issuers:
        if iss["name"].lower() in msg_lower:
            return iss["id"]

    # Significant word from name
    skip = {"inc", "inc.", "co", "co.", "corp", "ltd", "llc", "group", "the", "and", "plc", "&"}
    for iss in issuers:
        name_words = iss["name"].lower().replace(",", "").replace(".", "").split()
        for w in name_words:
            if len(w) >= 3 and w not in skip and w in msg_lower.split():
                return iss["id"]

    return None
