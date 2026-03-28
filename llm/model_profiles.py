from __future__ import annotations

from typing import Any, Dict, List, Optional
import json

## This catalog is intentionally explicit so agents can make deterministic routing choices.
# Load the catalog from a JSON or YAML file in a real implementation for easier maintenance and updates.
with open("model_catalog.json", "r") as f:
    model_profile = json.load(f)
MODEL_CATALOG = model_profile["models"]
REASONING_LEVEL_GUIDE = model_profile["reasoning_level_guide"]


def get_model_profile(model_key: str) -> Dict[str, Any]:
    if model_key not in MODEL_CATALOG:
        supported = ", ".join(sorted(MODEL_CATALOG))
        raise ValueError(f"Unknown model_key '{model_key}'. Supported: {supported}")
    return MODEL_CATALOG[model_key]


def recommend_model(task_tags: List[str], budget_sensitive: bool = False) -> str:
    tags = {t.lower() for t in task_tags}

    if "critical" in tags or "high-stakes" in tags or "complex-planning" in tags:
        return "claude-opus"
    if "coding" in tags or "tool-use" in tags or "agent" in tags:
        return "deepseek" if budget_sensitive else "gpt"
    if "multilingual" in tags:
        return "glm5"
    return "claude-sonnet"


def recommend_execution_plan(
    task_tags: List[str],
    *,
    budget_sensitive: bool = False,
    tools_required: bool = False,
    preferred_agent: Optional[str] = None,
    extra_skills_needed: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return a routing plan agents can use before chat execution."""
    model_key = recommend_model(task_tags=task_tags, budget_sensitive=budget_sensitive)
    profile = get_model_profile(model_key)

    skills = list(profile.get("default_skills_needed", []))
    for item in extra_skills_needed or []:
        if item not in skills:
            skills.append(item)

    return {
        "model_key": model_key,
        "provider": profile["provider"],
        "model": profile["model"],
        "reasoning_level": profile.get("recommended_reasoning_level", "medium"),
        "tool_call_enabled": bool(profile.get("supports_tool_call", False) and tools_required),
        "agent_appointment": preferred_agent or profile.get("default_agent_appointment"),
        "skills_needed": skills,
    }
