from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))  # Load env vars from parent .env file

from .messages import ChatHistory
from .model_profiles import get_model_profile


class ProviderError(RuntimeError):
	pass


@dataclass
class ChatResult:
	model_key: str
	provider: str
	model: str
	response_text: str
	trace_id: Optional[str]
	tool_calls: list[dict[str, Any]]
	agent_appointment: Optional[str]
	skills_needed: list[str]
	raw_response: Dict[str, Any]


class BaseProvider:
	def chat(
		self,
		*,
		model: str,
		messages: list[dict[str, str]],
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		raise NotImplementedError


class OpenAICompatibleProvider(BaseProvider):
	"""Works with OpenAI-compatible chat/completions APIs."""

	def __init__(self, base_url: str, api_key: str):
		import openai as _openai
		self._client = _openai.OpenAI(api_key=api_key, base_url=base_url)

	def chat(
		self,
		*,
		model: str,
		messages: list[dict[str, str]],
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		kwargs: Dict[str, Any] = {
			"model": model,
			"messages": messages,
		}
		if temperature is not None:
			kwargs["temperature"] = temperature
		if max_tokens is not None:
			kwargs["max_tokens"] = max_tokens
		if tools:
			kwargs["tools"] = tools
		if tool_choice is not None:
			kwargs["tool_choice"] = tool_choice
		if reasoning_level is not None:
			kwargs["reasoning_effort"] = reasoning_level

		try:
			response = self._client.chat.completions.create(**kwargs)
			return response.model_dump()
		except Exception as exc:  # noqa: BLE001
			raise ProviderError(f"OpenAI-compatible provider call failed: {exc}") from exc


class AnthropicProvider(BaseProvider):
	def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com"):
		import anthropic as _anthropic
		self._client = _anthropic.Anthropic(api_key=api_key, base_url=base_url)

	def chat(
		self,
		*,
		model: str,
		messages: list[dict[str, str]],
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		system_parts = [m["content"] for m in messages if m["role"] == "system"]
		dialog = [m for m in messages if m["role"] != "system"]

		kwargs: Dict[str, Any] = {
			"model": model,
			"messages": dialog,
			"max_tokens": max_tokens or 1024,
		}
		if system_parts:
			kwargs["system"] = "\n\n".join(system_parts)
		if tools:
			kwargs["tools"] = tools
		if tool_choice is not None:
			kwargs["tool_choice"] = tool_choice
		if reasoning_level is not None:
			kwargs["thinking"] = {"type": "adaptive"}
		elif temperature is not None:
			# temperature and extended thinking are mutually exclusive
			kwargs["temperature"] = temperature

		try:
			response = self._client.messages.create(**kwargs)
			return response.model_dump()
		except Exception as exc:  # noqa: BLE001
			raise ProviderError(f"Anthropic provider call failed: {exc}") from exc


def _thinking_tokens(reasoning_level: str) -> int:
	level = reasoning_level.lower()
	mapping = {
		"low": 1024,
		"low-medium": 2048,
		"medium": 4096,
		"medium-high": 8192,
		"high": 16384,
	}
	return mapping.get(level, 4096)


class UnifiedLLMClient:
	"""Single interface for multiple LLM vendors with traceable history support."""

	def __init__(self) -> None:
		self._providers: Dict[str, BaseProvider] = {}

	def register_provider(self, name: str, provider: BaseProvider) -> None:
		self._providers[name] = provider

	def register_default_providers_from_env(self) -> None:
		openai_key = os.getenv("OPENAI_API_KEY")
		openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
		if openai_key:
			self.register_provider("openai", OpenAICompatibleProvider(openai_base, openai_key))

		deepseek_key = os.getenv("DEEPSEEK_API_KEY")
		deepseek_base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
		if deepseek_key:
			self.register_provider("openai_compatible", OpenAICompatibleProvider(deepseek_base, deepseek_key))

		glm_key = os.getenv("GLM_API_KEY")
		glm_base = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
		if glm_key:
			self.register_provider("glm", OpenAICompatibleProvider(glm_base, glm_key))

		anthropic_key = os.getenv("ANTHROPIC_API_KEY")
		if anthropic_key:
			self.register_provider("anthropic", AnthropicProvider(anthropic_key))

	def chat(
		self,
		*,
		model_key: str,
		user_message: str,
		history: Optional[ChatHistory] = None,
		trace_id: Optional[str] = None,
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		agent_appointment: Optional[str] = None,
		skills_needed: Optional[list[str]] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
		metadata: Optional[Dict[str, Any]] = None,
	) -> ChatResult:
		profile = get_model_profile(model_key)
		provider_name = profile["provider"]

		if provider_name == "openai_compatible" and model_key == "glm5" and "glm" in self._providers:
			provider_name = "glm"

		if provider_name not in self._providers:
			registered = ", ".join(sorted(self._providers)) or "none"
			raise ProviderError(
				f"Provider '{provider_name}' is not registered. Registered providers: {registered}"
			)

		effective_reasoning = reasoning_level or profile.get("recommended_reasoning_level")

		if history is None:
			history = ChatHistory()
		user_msg = history.add(
			role="user",
			content=user_message,
			trace_id=trace_id,
			model=profile["model"],
			reasoning_level=effective_reasoning,
			metadata=metadata,
		)

		raw = self._providers[provider_name].chat(
			model=profile["model"],
			messages=history.to_provider_messages(),
			tools=tools,
			tool_choice=tool_choice,
			reasoning_level=effective_reasoning,
			temperature=temperature,
			max_tokens=max_tokens,
		)

		response_text = self._extract_text(provider_name=provider_name, payload=raw)
		tool_calls = self._extract_tool_calls(provider_name=provider_name, payload=raw)
		resolved_agent = agent_appointment or profile.get("default_agent_appointment")
		resolved_skills = skills_needed or list(profile.get("default_skills_needed", []))
		history.add(
			role="assistant",
			content=response_text,
			trace_id=trace_id,
			parent_message_id=user_msg.message_id,
			model=profile["model"],
			reasoning_level=effective_reasoning,
			metadata={
				"provider": provider_name,
				"tool_calls": tool_calls,
				"agent_appointment": resolved_agent,
				"skills_needed": resolved_skills,
			},
		)

		return ChatResult(
			model_key=model_key,
			provider=provider_name,
			model=profile["model"],
			response_text=response_text,
			trace_id=trace_id,
			tool_calls=tool_calls,
			agent_appointment=resolved_agent,
			skills_needed=resolved_skills,
			raw_response=raw,
		)

	@staticmethod
	def _extract_text(*, provider_name: str, payload: Dict[str, Any]) -> str:
		if provider_name in {"openai", "openai_compatible", "glm"}:
			choices = payload.get("choices", [])
			if choices:
				return choices[0].get("message", {}).get("content", "")
			return ""

		if provider_name == "anthropic":
			blocks = payload.get("content", [])
			text_chunks = [b.get("text", "") for b in blocks if b.get("type") == "text"]
			return "\n".join([t for t in text_chunks if t])

		return ""

	@staticmethod
	def _extract_tool_calls(*, provider_name: str, payload: Dict[str, Any]) -> list[dict[str, Any]]:
		if provider_name in {"openai", "openai_compatible", "glm"}:
			choices = payload.get("choices", [])
			if not choices:
				return []
			msg = choices[0].get("message", {})
			calls = msg.get("tool_calls", []) or []

			normalized: list[dict[str, Any]] = []
			for call in calls:
				fn = call.get("function", {})
				args_raw = fn.get("arguments", "{}")
				try:
					parsed_args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
				except Exception:  # noqa: BLE001
					parsed_args = {"_raw": args_raw}
				normalized.append(
					{
						"id": call.get("id"),
						"name": fn.get("name"),
						"arguments": parsed_args,
					}
				)
			return normalized

		if provider_name == "anthropic":
			blocks = payload.get("content", [])
			calls: list[dict[str, Any]] = []
			for block in blocks:
				if block.get("type") == "tool_use":
					calls.append(
						{
							"id": block.get("id"),
							"name": block.get("name"),
							"arguments": block.get("input", {}),
						}
					)
			return calls

		return []
