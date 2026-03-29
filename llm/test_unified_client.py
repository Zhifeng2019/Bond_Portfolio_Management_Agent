from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.unified_client import (
    AnthropicProvider,
    GoogleGenAIProvider,
    OpenAICompatibleProvider,
    ProviderDefaultModels,
    ProviderError,
    UnifiedLLMClient,
)


class _FakeOpenAIResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self) -> dict:
        return self._payload


class _FakeOpenAICompletions:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeOpenAIResponse({"choices": [{"message": {"content": "ok"}}]})


class _FakeOpenAIClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.chat = types.SimpleNamespace(completions=_FakeOpenAICompletions())


class _FakeAnthropicResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self) -> dict:
        return self._payload


class _FakeAnthropicMessages:
    def __init__(self):
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeAnthropicResponse({"content": [{"type": "text", "text": "ok"}]})


class _FakeAnthropicClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.messages = _FakeAnthropicMessages()


class _FakeGoogleResponse:
    def __init__(self, payload: dict):
        self._payload = payload
        self.text = payload.get("text", "")

    def to_json_dict(self) -> dict:
        return self._payload


class _FakeGoogleModels:
    def __init__(self):
        self.last_kwargs = None

    def generate_content(self, **kwargs):
        self.last_kwargs = kwargs
        return _FakeGoogleResponse({"text": "ok"})


class _FakeGoogleClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.models = _FakeGoogleModels()


class ProviderTests(unittest.TestCase):
    def test_provider_default_models_lookup(self):
        self.assertEqual(ProviderDefaultModels.get_default_model("openai"), "gpt-pro")
        self.assertEqual(ProviderDefaultModels.get_default_model("anthropic"), "claude-sonnet")
        self.assertEqual(ProviderDefaultModels.get_default_model("GLM"), "glm5")
        with self.assertRaises(ProviderError):
            ProviderDefaultModels.get_default_model("unknown-provider")

    def test_openai_compatible_uses_env_and_default_model(self):
        fake_openai_module = types.ModuleType("openai")
        fake_openai_module.OpenAI = _FakeOpenAIClient

        with patch.dict(sys.modules, {"openai": fake_openai_module}):
            with patch.dict(
                os.environ,
                {"OPENAI_API_KEY": "test-key", "OPENAI_BASE_URL": "https://example.openai/v1"},
                clear=False,
            ):
                provider = OpenAICompatibleProvider(provider_name="openai")
                provider.chat(messages=[{"role": "user", "content": "hello"}], model=None)

                sent = provider._client.chat.completions.last_kwargs
                self.assertEqual(sent["model"], "gpt-5.4")
                self.assertEqual(sent["messages"][0]["content"], "hello")

    def test_openai_compatible_raises_without_key(self):
        fake_openai_module = types.ModuleType("openai")
        fake_openai_module.OpenAI = _FakeOpenAIClient

        with patch.dict(sys.modules, {"openai": fake_openai_module}):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ProviderError):
                    OpenAICompatibleProvider(base_url="https://example.openai/v1")

    def test_anthropic_uses_env_and_default_model(self):
        fake_anthropic_module = types.ModuleType("anthropic")
        fake_anthropic_module.Anthropic = _FakeAnthropicClient

        with patch.dict(sys.modules, {"anthropic": fake_anthropic_module}):
            with patch.dict(
                os.environ,
                {
                    "ANTHROPIC_API_KEY": "test-key",
                    "ANTHROPIC_BASE_URL": "https://example.anthropic",
                },
                clear=False,
            ):
                provider = AnthropicProvider()
                provider.chat(messages=[{"role": "user", "content": "hello"}], model=None)

                sent = provider._client.messages.last_kwargs
                self.assertEqual(sent["model"], "claude-sonnet-4-6")
                self.assertEqual(sent["messages"][0]["content"], "hello")

    def test_anthropic_raises_without_key(self):
        fake_anthropic_module = types.ModuleType("anthropic")
        fake_anthropic_module.Anthropic = _FakeAnthropicClient

        with patch.dict(sys.modules, {"anthropic": fake_anthropic_module}):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ProviderError):
                    AnthropicProvider()

    def test_google_uses_env_default_model_and_tools(self):
        fake_google_module = types.ModuleType("google")
        fake_google_genai_module = types.ModuleType("google.genai")
        fake_google_genai_module.Client = _FakeGoogleClient
        fake_google_module.genai = fake_google_genai_module

        with patch.dict(
            sys.modules,
            {
                "google": fake_google_module,
                "google.genai": fake_google_genai_module,
            },
        ):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False):
                provider = GoogleGenAIProvider()
                provider.chat(
                    model=None,
                    messages=[{"role": "user", "content": "hello"}],
                    tools=[
                        {
                            "type": "function",
                            "function": {
                                "name": "lookup",
                                "description": "Find data",
                                "parameters": {"type": "object", "properties": {}},
                            },
                        }
                    ],
                    tool_choice="auto",
                )

                sent = provider._client.models.last_kwargs
                self.assertEqual(sent["model"], "gemini-3.1-pro-preview")
                self.assertEqual(sent["config"]["tool_config"]["function_calling_config"]["mode"], "AUTO")

    def test_google_raises_without_key(self):
        fake_google_module = types.ModuleType("google")
        fake_google_genai_module = types.ModuleType("google.genai")
        fake_google_genai_module.Client = _FakeGoogleClient
        fake_google_module.genai = fake_google_genai_module

        with patch.dict(
            sys.modules,
            {
                "google": fake_google_module,
                "google.genai": fake_google_genai_module,
            },
        ):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ProviderError):
                    GoogleGenAIProvider()

    def test_unified_client_registers_provider_aliases(self):
        fake_openai_module = types.ModuleType("openai")
        fake_openai_module.OpenAI = _FakeOpenAIClient
        fake_anthropic_module = types.ModuleType("anthropic")
        fake_anthropic_module.Anthropic = _FakeAnthropicClient
        fake_google_module = types.ModuleType("google")
        fake_google_genai_module = types.ModuleType("google.genai")
        fake_google_genai_module.Client = _FakeGoogleClient
        fake_google_module.genai = fake_google_genai_module

        with patch.dict(
            sys.modules,
            {
                "openai": fake_openai_module,
                "anthropic": fake_anthropic_module,
                "google": fake_google_module,
                "google.genai": fake_google_genai_module,
            },
        ):
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "openai-key",
                    "DEEPSEEK_API_KEY": "deepseek-key",
                    "GLM_API_KEY": "glm-key",
                    "ANTHROPIC_API_KEY": "anthropic-key",
                    "GOOGLE_API_KEY": "google-key",
                },
                clear=False,
            ):
                client = UnifiedLLMClient()
                self.assertIn("openai", client._providers)
                self.assertIn("deepseek", client._providers)
                self.assertIn("openai_compatible", client._providers)
                self.assertIn("glm", client._providers)
                self.assertIn("anthropic", client._providers)
                self.assertIn("google", client._providers)


if __name__ == "__main__":
    unittest.main()
