"""Routing tools — LLM-callable tools for agent appointment and skill activation.

When agent/skill descriptions are provided in the system prompt, the LLM can
call these tools to signal which agent should handle a task and which skills
to activate.  The orchestration layer inspects the tool calls in ChatResult
and routes accordingly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ── Tool schemas (Anthropic format) ─────────────────────────────────────

_APPOINT_AGENT_SCHEMA: dict[str, Any] = {
    "name": "appoint_agent",
    "description": (
        "Appoint a specific agent to handle the current task. "
        "Call this when you determine that the user's request should be "
        "delegated to a specialised agent. Provide the agent name (must "
        "match one of the available agents listed in your instructions) "
        "and a brief reason for the appointment."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": (
                    "The identifier of the agent to appoint, e.g. "
                    "'report_agent' or 'stress_testing_agent'."
                ),
            },
            "task_summary": {
                "type": "string",
                "description": (
                    "A concise summary of the task to hand off to the agent, "
                    "capturing the user's intent and any key parameters."
                ),
            },
            "reason": {
                "type": "string",
                "description": (
                    "Why this agent is the best fit for the request."
                ),
            },
        },
        "required": ["agent_name", "task_summary"],
    },
}

_USE_SKILL_SCHEMA: dict[str, Any] = {
    "name": "use_skill",
    "description": (
        "Activate one or more skills for the current task. "
        "Call this when you determine that specific skills are needed "
        "to fulfil the user's request. Provide the skill names (must "
        "match skills listed in your instructions) and context for "
        "how each skill should be applied."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "skill_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of skill identifiers to activate, e.g. "
                    "['bond-issuer-report-skill']."
                ),
            },
            "context": {
                "type": "string",
                "description": (
                    "Additional context or instructions for how the "
                    "skills should be applied to this specific request."
                ),
            },
        },
        "required": ["skill_names"],
    },
}


# ── Schema accessors ────────────────────────────────────────────────────

def get_routing_tool_schemas(fmt: str = "anthropic") -> list[dict[str, Any]]:
    """Return tool schemas for agent appointment and skill activation.

    Parameters
    ----------
    fmt : str
        ``"anthropic"`` returns Anthropic Messages API format (``input_schema``).
        ``"openai"`` returns OpenAI function-calling format (``function`` wrapper).
    """
    anthropic_schemas = [_APPOINT_AGENT_SCHEMA, _USE_SKILL_SCHEMA]

    if fmt == "anthropic":
        return anthropic_schemas

    if fmt == "openai":
        return [_to_openai_tool(s) for s in anthropic_schemas]

    raise ValueError(f"Unsupported schema format: {fmt!r}. Use 'anthropic' or 'openai'.")


def _to_openai_tool(anthropic_schema: dict[str, Any]) -> dict[str, Any]:
    """Convert an Anthropic tool schema to OpenAI function-calling format."""
    return {
        "type": "function",
        "function": {
            "name": anthropic_schema["name"],
            "description": anthropic_schema["description"],
            "parameters": anthropic_schema["input_schema"],
        },
    }


# ── Tool handlers ───────────────────────────────────────────────────────

def handle_appoint_agent(
    agent_name: str,
    task_summary: str,
    reason: str = "",
    *,
    available_agents: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Process an appoint_agent tool call.

    Validates the agent name against the available list (when provided)
    and returns a structured routing decision.
    """
    if available_agents is not None and agent_name not in available_agents:
        return {
            "status": "error",
            "message": (
                f"Unknown agent '{agent_name}'. "
                f"Available agents: {', '.join(sorted(available_agents))}"
            ),
        }

    return {
        "status": "ok",
        "agent_name": agent_name,
        "task_summary": task_summary,
        "reason": reason,
    }


def handle_use_skill(
    skill_names: List[str],
    context: str = "",
    *,
    available_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Process a use_skill tool call.

    Validates skill names against the available list (when provided)
    and returns a structured activation decision.
    """
    if available_skills is not None:
        unknown = [s for s in skill_names if s not in available_skills]
        if unknown:
            return {
                "status": "error",
                "message": (
                    f"Unknown skill(s): {', '.join(unknown)}. "
                    f"Available skills: {', '.join(sorted(available_skills))}"
                ),
            }

    return {
        "status": "ok",
        "skill_names": skill_names,
        "context": context,
    }


# ── Registry ────────────────────────────────────────────────────────────

ROUTING_TOOL_HANDLERS: Dict[str, Any] = {
    "appoint_agent": handle_appoint_agent,
    "use_skill": handle_use_skill,
}


def execute_routing_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    *,
    available_agents: Optional[List[str]] = None,
    available_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute a routing tool call by name.

    This is the main entry point for the orchestration layer to process
    appoint_agent / use_skill tool calls extracted from ChatResult.tool_calls.

    Parameters
    ----------
    tool_name : str
        ``"appoint_agent"`` or ``"use_skill"``.
    arguments : dict
        The parsed arguments from the LLM's tool call.
    available_agents : list[str], optional
        If provided, agent names are validated against this list.
    available_skills : list[str], optional
        If provided, skill names are validated against this list.

    Returns
    -------
    dict with ``status`` (``"ok"`` or ``"error"``) and routing details.
    """
    if tool_name == "appoint_agent":
        return handle_appoint_agent(
            agent_name=arguments.get("agent_name", ""),
            task_summary=arguments.get("task_summary", ""),
            reason=arguments.get("reason", ""),
            available_agents=available_agents,
        )

    if tool_name == "use_skill":
        return handle_use_skill(
            skill_names=arguments.get("skill_names", []),
            context=arguments.get("context", ""),
            available_skills=available_skills,
        )

    return {"status": "error", "message": f"Unknown routing tool: {tool_name}"}


def is_routing_tool(tool_name: str) -> bool:
    """Check whether a tool name is a routing tool (vs. a data/action tool)."""
    return tool_name in ROUTING_TOOL_HANDLERS
