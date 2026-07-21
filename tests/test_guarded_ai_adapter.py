import json
import socket
from urllib.error import HTTPError

import pytest

from industry_alpha.guarded_ai_adapter import (
    GuardedAIProviderConfig,
    OpenAICompatibleGuardedAIAdapter,
)
from industry_alpha.guarded_ai_contracts import (
    GuardedAIConfigurationError,
    GuardedAIRateLimitError,
    GuardedAITimeoutError,
)


VALID_ENV = {
    "AQUANTAI_GUARDED_AI_ENABLED": "true",
    "AQUANTAI_GUARDED_AI_PROVIDER_ID": "explicit-provider",
    "AQUANTAI_GUARDED_AI_ENDPOINT_URL": "https://example.invalid/v1/chat/completions",
    "AQUANTAI_GUARDED_AI_MODEL_ID": "explicit-model",
    "AQUANTAI_GUARDED_AI_API_KEY": "test-only-secret",
    "AQUANTAI_GUARDED_AI_DATA_USE_NOTICE": "Operator-reviewed provider policy.",
}


class FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")
        self.headers = {"x-request-id": "request-1"}

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _tb):
        return False

    def read(self, _limit):
        return self._body


def test_configuration_has_no_defaults_and_is_disabled_by_default() -> None:
    config = GuardedAIProviderConfig.from_environment({})
    profile = config.public_profile()

    assert config.enabled is False
    assert config.endpoint_url is None
    assert config.provider_id is None
    assert config.model_id is None
    assert profile.available is False
    with pytest.raises(GuardedAIConfigurationError):
        config.require_enabled()


def test_configuration_requires_explicit_https_profile() -> None:
    invalid = dict(VALID_ENV)
    invalid["AQUANTAI_GUARDED_AI_ENDPOINT_URL"] = "http://example.invalid/chat"
    config = GuardedAIProviderConfig.from_environment(invalid)

    assert config.public_profile().available is False
    with pytest.raises(GuardedAIConfigurationError):
        OpenAICompatibleGuardedAIAdapter(config)


def test_adapter_makes_one_fixed_request_without_tools_or_streaming() -> None:
    calls = []

    def opener(request, *, timeout):
        calls.append((request, timeout))
        return FakeResponse({
            "choices": [{"message": {"content": "{\"ok\":true}"}}]
        })

    config = GuardedAIProviderConfig.from_environment(VALID_ENV)
    adapter = OpenAICompatibleGuardedAIAdapter(config, opener=opener)
    result = adapter.generate(
        canonical_manifest="{\"manifest\":true}",
        manifest_fingerprint="sha256:" + "a" * 64,
        prompt_template_version="guarded-ai-company-research-v1",
        maximum_output_tokens=2_000,
    )

    assert result.raw_content == '{"ok":true}'
    assert result.provider_request_id == "request-1"
    assert len(calls) == 1
    request, timeout = calls[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert timeout == 60
    assert payload["stream"] is False
    assert "tools" not in payload
    assert "functions" not in payload
    assert payload["max_tokens"] == 2_000
    assert request.full_url == VALID_ENV["AQUANTAI_GUARDED_AI_ENDPOINT_URL"]


def test_adapter_maps_rate_limit_and_timeout_without_retry() -> None:
    rate_calls = []

    def rate_limited(request, *, timeout):
        rate_calls.append((request, timeout))
        raise HTTPError(request.full_url, 429, "limited", {}, None)

    adapter = OpenAICompatibleGuardedAIAdapter(
        GuardedAIProviderConfig.from_environment(VALID_ENV),
        opener=rate_limited,
    )
    with pytest.raises(GuardedAIRateLimitError):
        adapter.generate(
            canonical_manifest="{}",
            manifest_fingerprint="sha256:" + "a" * 64,
            prompt_template_version="guarded-ai-company-research-v1",
            maximum_output_tokens=2_000,
        )
    assert len(rate_calls) == 1

    timeout_calls = []

    def timed_out(request, *, timeout):
        timeout_calls.append((request, timeout))
        raise socket.timeout("private endpoint detail")

    adapter = OpenAICompatibleGuardedAIAdapter(
        GuardedAIProviderConfig.from_environment(VALID_ENV),
        opener=timed_out,
    )
    with pytest.raises(GuardedAITimeoutError) as captured:
        adapter.generate(
            canonical_manifest="{}",
            manifest_fingerprint="sha256:" + "a" * 64,
            prompt_template_version="guarded-ai-company-research-v1",
            maximum_output_tokens=2_000,
        )
    assert "private endpoint detail" not in str(captured.value)
    assert len(timeout_calls) == 1
