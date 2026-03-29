# Unified LLM Interface

This module provides:

- A unified client for multiple model providers (Anthropic, OpenAI, DeepSeek, GLM, Google GenAI).
- Traceable message and conversation history objects with IDs/timestamps/lineage.
- A model capability catalog for model-routing decisions by agents.
- Native support for tool call, agent appointment, and skills-needed routing metadata.
- Separation of stable model keys from provider model names so model upgrades stay in `model_catalog.json`.

## Files

- `messages.py`: `ChatMessage`, `ChatHistory`
- `unified_client.py`: providers and `UnifiedLLMClient`
- `model_profiles.py`: model catalog loaders and recommendation helpers
- `model_catalog.json`: JSON model catalog for non-Python consumers

## Environment Variables

Set any provider keys you plan to use:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` (optional, defaults to `https://api.openai.com/v1`)
- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL` (optional, defaults to `https://api.deepseek.com/v1`)
- `GLM_API_KEY`
- `GLM_BASE_URL` (optional, defaults to `https://open.bigmodel.cn/api/paas/v4`)
- `GOOGLE_API_KEY`
- `ANTHROPIC_BASE_URL` (optional, defaults to `https://api.anthropic.com`)

## Quick Start

```python
from llm import ChatHistory, UnifiedLLMClient

history = ChatHistory()
history.add("system", "You are a bond research assistant.")

client = UnifiedLLMClient()
client.register_default_providers_from_env()

result = client.chat(
    model_key="claude-sonnet",
    history=history,
    user_message="Summarize issuer risks from latest filing.",
    trace_id="run-2026-03-28-001",
    tools=[
        {
            "type": "function",
            "function": {
                "name": "get_issuer_profile",
                "description": "Get basic issuer profile",
                "parameters": {
                    "type": "object",
                    "properties": {"issuer_id": {"type": "string"}},
                    "required": ["issuer_id"],
                },
            },
        }
    ],
    tool_choice="auto",
    agent_appointment="report-agent",
    skills_needed=["credit-report", "html-generation"],
)

print(result.response_text)
print(result.tool_calls)
print(result.agent_appointment)
print(result.skills_needed)
history.save_json("conversation_trace.json")
```

## Routing Helper

`model_key` is the stable application-facing identifier. The actual provider model name is resolved from `model_catalog.json` at runtime.

```python
from llm import recommend_execution_plan

plan = recommend_execution_plan(
    task_tags=["coding", "agent", "tool-use"],
    tools_required=True,
)
# plan has model_key, reasoning_level, tool_call_enabled, agent_appointment, skills_needed
```
