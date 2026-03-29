from __future__ import annotations

import json
import os
from enum import Enum
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
		model: Optional[str] = None,
		messages: list[dict[str, str]],
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		raise NotImplementedError


class ProviderDefaultModels(Enum):
	"""Central registry for provider-level default model keys."""

	OPENAI = "gpt-pro"
	DEEPSEEK = "deepseek-chat"
	GLM = "glm5"
	ANTHROPIC = "claude-sonnet"
	GOOGLE = "gemini-pro"

	@classmethod
	def get_default_model(cls, provider_name: str) -> str:
		try:
			return cls[provider_name.upper()].value
		except KeyError as exc:
			raise ProviderError(f"No default model configured for provider '{provider_name}'.") from exc


def _resolve_provider_model_name(provider_name: str, model: Optional[str]) -> str:
	if model:
		return model
	default_model_key = ProviderDefaultModels.get_default_model(provider_name)
	profile = get_model_profile(default_model_key)
	return profile["model"]


class OpenAIProvider(BaseProvider):
	"""Works with OpenAI-compatible chat/completions APIs."""

	def __init__(
		self,
		base_url: Optional[str] = None,
		api_key: Optional[str] = None,
		*,
		provider_name: str = "openai",
		env_api_key_var: str = "OPENAI_API_KEY",
		env_base_url_var: str = "OPENAI_BASE_URL",
		default_base_url: str = "https://api.openai.com/v1",
	):
		import openai as _openai

		resolved_api_key = api_key or os.getenv(env_api_key_var)
		resolved_base_url = base_url or os.getenv(env_base_url_var) or default_base_url

		if not resolved_api_key:
			raise ProviderError(
				f"OpenAI provider requires api_key or env var '{env_api_key_var}'."
			)
		if not resolved_base_url:
			raise ProviderError(
				f"OpenAI provider requires base_url or env var '{env_base_url_var}'."
			)

		self._provider_name = provider_name
		self._client = _openai.OpenAI(api_key=resolved_api_key, base_url=resolved_base_url)

	def chat(
		self,
		*,
		model: Optional[str] = None,
		messages: list[dict[str, str]],
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		resolved_model = _resolve_provider_model_name(self._provider_name, model)
		kwargs: Dict[str, Any] = {
			"model": resolved_model,
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
		except Exception as exc:
			raise ProviderError(f"OpenAI provider call failed: {exc}") from exc


class AnthropicProvider(BaseProvider):
	def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
		import anthropic as _anthropic

		resolved_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
		resolved_base_url = base_url or os.getenv("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"

		if not resolved_api_key:
			raise ProviderError(
				"Anthropic provider requires api_key or env var 'ANTHROPIC_API_KEY'."
			)
		if not resolved_base_url:
			raise ProviderError(
				"Anthropic provider requires base_url or env var 'ANTHROPIC_BASE_URL'."
			)

		self._client = _anthropic.Anthropic(api_key=resolved_api_key, base_url=resolved_base_url)

	def chat(
		self,
		*,
		model: Optional[str] = None,
		messages: list[dict[str, str]],
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		system_parts = [m["content"] for m in messages if m["role"] == "system"]
		dialog = [m for m in messages if m["role"] != "system"]
		resolved_model = _resolve_provider_model_name("anthropic", model)

		kwargs: Dict[str, Any] = {
			"model": resolved_model,
			"messages": dialog,
			"max_tokens": max_tokens or 64*1024,
		}
		if system_parts:
			kwargs["system"] = "\n\n".join(system_parts)
		if tools:
			kwargs["tools"] = tools
		if tool_choice is not None:
			kwargs["tool_choice"] = tool_choice
		if reasoning_level is not None:
			kwargs["thinking"] = {"type": reasoning_level}
		else:
			kwargs["thinking"] = {"type": "adaptive"}
		if temperature is not None:
			# temperature and extended thinking are mutually exclusive
			kwargs["temperature"] = temperature

		try:
			response = self._client.messages.create(**kwargs)
			return response.model_dump()
		except Exception as exc:
			raise ProviderError(f"Anthropic provider call failed: {exc}") from exc


class GoogleGenAIProvider(BaseProvider):
	"""Google provider using the google-genai package."""

	def __init__(self, api_key: Optional[str] = None):
		from google import genai as _genai

		resolved_api_key = api_key or os.getenv("GOOGLE_API_KEY")
		if not resolved_api_key:
			raise ProviderError(
				"Google GenAI provider requires api_key or env var 'GOOGLE_API_KEY'."
			)

		self._client = _genai.Client(api_key=resolved_api_key)

	@staticmethod
	def _to_google_tool_declarations(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
		declarations: list[dict[str, Any]] = []
		for tool in tools:
			if tool.get("type") != "function":
				continue
			fn = tool.get("function", {})
			name = fn.get("name")
			if not name:
				continue
			decl: dict[str, Any] = {
				"name": name,
				"description": fn.get("description", ""),
				"parameters": fn.get("parameters", {"type": "object", "properties": {}}),
			}
			declarations.append(decl)
		return declarations

	def chat(
		self,
		*,
		model: Optional[str] = None,
		messages: list[dict[str, str]],
		tools: Optional[list[dict[str, Any]]] = None,
		tool_choice: Optional[str] = None,
		reasoning_level: Optional[str] = None,
		temperature: Optional[float] = None,
		max_tokens: Optional[int] = None,
	) -> Dict[str, Any]:
		resolved_model = _resolve_provider_model_name("google", model)
		system_parts = [m.get("content", "") for m in messages if m.get("role") == "system"]
		contents: list[dict[str, Any]] = []
		for msg in messages:
			role = msg.get("role")
			if role == "system":
				continue
			if role == "assistant":
				google_role = "model"
			else:
				google_role = "user"
			content = msg.get("content", "")
			if not content:
				continue
			contents.append({"role": google_role, "parts": [{"text": content}]})

		config: Dict[str, Any] = {}
		if system_parts:
			config["system_instruction"] = "\n\n".join([p for p in system_parts if p])
		if temperature is not None:
			config["temperature"] = temperature
		if max_tokens is not None:
			config["max_output_tokens"] = max_tokens
		if reasoning_level is not None:
			config["thinking_config"] = {"thinking_budget": _thinking_tokens(reasoning_level)}
		if tools:
			declarations = self._to_google_tool_declarations(tools)
			if declarations:
				config["tools"] = [{"function_declarations": declarations}]
				if tool_choice in {"none", "auto", "required"}:
					config["tool_config"] = {
						"function_calling_config": {"mode": tool_choice.upper()}
					}

		kwargs: Dict[str, Any] = {
			"model": resolved_model,
			"contents": contents,
		}
		if config:
			kwargs["config"] = config

		try:
			response = self._client.models.generate_content(**kwargs)
			if hasattr(response, "to_json_dict"):
				payload = response.to_json_dict()
			elif hasattr(response, "model_dump"):
				payload = response.model_dump()
			else:
				payload = {"text": getattr(response, "text", "")}
			if "text" not in payload:
				payload["text"] = getattr(response, "text", "")
			return payload
		except Exception as exc:  # noqa: BLE001
			raise ProviderError(f"Google GenAI provider call failed: {exc}") from exc


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
		self.register_default_providers_from_env()

	def register_provider(self, name: str, provider: BaseProvider) -> None:
		self._providers[name] = provider

	def register_default_providers_from_env(self) -> None:
		openai_key = os.getenv("OPENAI_API_KEY")
		openai_base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
		if openai_key:
			self.register_provider(
				"openai",
				OpenAIProvider(openai_base, openai_key, provider_name="openai"),
			)

		deepseek_key = os.getenv("DEEPSEEK_API_KEY")
		deepseek_base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
		if deepseek_key:
			self.register_provider(
				"deepseek",
				OpenAIProvider(deepseek_base, deepseek_key, provider_name="deepseek"),
			)

		glm_key = os.getenv("GLM_API_KEY")
		glm_base = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
		if glm_key:
			self.register_provider(
				"glm",
				OpenAIProvider(glm_base, glm_key, provider_name="glm"),
			)

		anthropic_key = os.getenv("ANTHROPIC_API_KEY")
		if anthropic_key:
			self.register_provider("anthropic", AnthropicProvider(anthropic_key))

		google_key = os.getenv("GOOGLE_API_KEY")
		if google_key:
			self.register_provider("google", GoogleGenAIProvider(google_key))

	def chat(
		self,
		*,
		model_key: str="deepseek-reasoner",
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
		if provider_name in {"openai", "deepseek", "glm"}:
			choices = payload.get("choices", [])
			if choices:
				return choices[0].get("message", {}).get("content", "")
			return ""

		if provider_name == "google":
			if payload.get("text"):
				return payload.get("text", "")
			for candidate in payload.get("candidates", []) or []:
				parts = candidate.get("content", {}).get("parts", [])
				texts = [part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text")]
				if texts:
					return "\n".join(texts)
			return ""

		if provider_name == "anthropic":
			blocks = payload.get("content", [])
			text_chunks = [b.get("text", "") for b in blocks if b.get("type") == "text"]
			return "\n".join([t for t in text_chunks if t])

		return ""

	@staticmethod
	def _extract_tool_calls(*, provider_name: str, payload: Dict[str, Any]) -> list[dict[str, Any]]:
		if provider_name in {"openai", "deepseek", "glm"}:
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

		if provider_name == "google":
			calls: list[dict[str, Any]] = []
			for candidate in payload.get("candidates", []) or []:
				for part in candidate.get("content", {}).get("parts", []) or []:
					if not isinstance(part, dict):
						continue
					function_call = part.get("functionCall") or part.get("function_call")
					if not function_call:
						continue
					calls.append(
						{
							"id": function_call.get("id"),
							"name": function_call.get("name"),
							"arguments": function_call.get("args", {}),
						}
					)
			return calls

		return []
