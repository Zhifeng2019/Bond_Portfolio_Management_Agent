from __future__ import annotations

from typing import Any, Dict, List, Optional


# This catalog is intentionally explicit so agents can make deterministic routing choices.
MODEL_CATALOG: Dict[str, Dict[str, Any]] = {
    "claude-opus": {
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "display_name": "Claude Opus",
        "supports_tool_call": True,
        "default_agent_appointment": "senior-analyst-agent",
        "default_skills_needed": ["deep-analysis", "strategy", "risk-synthesis"],
        "strengths": [
            "Deep reasoning for ambiguous tasks",
            "High quality long-form writing",
            "Complex planning and multi-step analysis",
        ],
        "best_for": [
            "Critical reports",
            "Hard architecture decisions",
            "Detailed synthesis from many inputs",
        ],
        "avoid_when": [
            "Simple low-cost classification",
            "High-throughput trivial transforms",
        ],
        "recommended_reasoning_level": "high",
        "cost_tier": "high",
        "latency_tier": "medium",
    },
    "claude-sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "display_name": "Claude Sonnet",
        "supports_tool_call": True,
        "default_agent_appointment": "general-purpose-agent",
        "default_skills_needed": ["coding", "editing", "reporting"],
        "strengths": [
            "Balanced quality, speed, and cost",
            "Reliable coding and editing",
            "Good instruction following",
        ],
        "best_for": [
            "General agent work",
            "Code generation and refactoring",
            "Report drafting",
        ],
        "avoid_when": [
            "When maximum reasoning depth is required",
        ],
        "recommended_reasoning_level": "medium",
        "cost_tier": "medium",
        "latency_tier": "fast",
    },
    "gpt": {
        "provider": "openai",
        "model": "gpt-5",
        "display_name": "GPT",
        "supports_tool_call": True,
        "default_agent_appointment": "orchestrator-agent",
        "default_skills_needed": ["tool-use", "coding", "structured-output"],
        "strengths": [
            "Strong tool-use and coding workflows",
            "Robust instruction following",
            "High quality structured output",
        ],
        "best_for": [
            "Agent orchestration",
            "Code tasks",
            "Schema-constrained responses",
        ],
        "avoid_when": [
            "Ultra-low-cost batch operations",
        ],
        "recommended_reasoning_level": "medium-high",
        "cost_tier": "high",
        "latency_tier": "fast-medium",
    },
    "deepseek": {
        "provider": "openai_compatible",
        "model": "deepseek-chat",
        "display_name": "DeepSeek",
        "supports_tool_call": True,
        "default_agent_appointment": "cost-efficient-coding-agent",
        "default_skills_needed": ["coding", "math", "batch-analysis"],
        "strengths": [
            "Cost-effective coding and math",
            "Strong performance for structured reasoning",
        ],
        "best_for": [
            "Budget-sensitive coding",
            "Large-volume analytical passes",
        ],
        "avoid_when": [
            "Highest-stakes writing polish",
        ],
        "recommended_reasoning_level": "medium",
        "cost_tier": "low-medium",
        "latency_tier": "fast",
    },
    "glm5": {
        "provider": "openai_compatible",
        "model": "glm-5",
        "display_name": "GLM5",
        "supports_tool_call": True,
        "default_agent_appointment": "multilingual-agent",
        "default_skills_needed": ["multilingual", "general-chat"],
        "strengths": [
            "Practical multilingual handling",
            "Efficient general-purpose generation",
        ],
        "best_for": [
            "General chat",
            "Mixed-language workflows",
        ],
        "avoid_when": [
            "Very deep chain-of-thought tasks",
        ],
        "recommended_reasoning_level": "low-medium",
        "cost_tier": "low",
        "latency_tier": "fast",
    },
}


REASONING_LEVEL_GUIDE: Dict[str, Dict[str, Any]] = {
    "low": {
        "use_when": "Simple extraction, formatting, or direct Q&A.",
        "target": "lowest cost and latency",
    },
    "low-medium": {
        "use_when": "Routine business logic with small ambiguity.",
        "target": "balanced speed and quality",
    },
    "medium": {
        "use_when": "Most coding, analysis, and report drafting tasks.",
        "target": "default setting for agents",
    },
    "medium-high": {
        "use_when": "Non-trivial planning and higher quality synthesis.",
        "target": "higher accuracy while containing cost",
    },
    "high": {
        "use_when": "Complex, high-stakes, ambiguous decisions.",
        "target": "maximum reasoning depth",
    },
    "adaptive": {
		"use_when": "When task complexity is unknown or variable.",
		"target": "dynamically adjust reasoning depth based on task needs",
	},
}


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
