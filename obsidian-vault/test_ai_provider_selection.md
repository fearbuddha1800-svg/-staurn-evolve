---
slug: test_ai_provider_selection
type: note
graph: gitnexus
---

"""Provider selection and extraction contract: all transports are fake."""
import io
import json
import urllib.error
from unittest.mock import mock_open

import pytest
import ai_filter as af


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(af, "_router", None)
    monkeypatch.setattr(af, "_load_env", lambda: {})
    monkeypatch.setattr(af, "_hermes_model_cfg", lambda: {})
    monkeypatch.setattr(af, "ai_cfg", lambda: {"enabled": True, "timeout_s": 2})
    def forbidden(*args, **kwargs):
        raise AssertionError("Real network forbidden")
    monkeypatch.setattr(af.urllib.request, "urlopen", forbidden)


def configure(monkeypatch, provider="openrouter", key=True):
    monkeypatch.setattr(af, "_hermes_model_cfg", lambda: {
        "provider": provider, "default": "configured-model:free",
        "api_mode": "chat_completions",
    })
    monkeypatch.setattr(af, "_load_env", lambda: {
        "OPENROUTER_API_KEY": "fake-key" if key else "",
        "NVIDIA_API_KEY": "unrelated-key",
        "NVIDIA_BASE_URL": "https://wrong-provider.invalid/v1",
    })


def test_configured_provider_does_not_borrow_nvidia_endpoint(monkeypatch):
    configure(monkeypatch)
    assert af._llm_candidates() == [
        ("fake-key", "https://openrouter.ai/api/v1", "configured-model:free")]


def test_no_matching_key_refuses_without_network(monkeypatch):
    configure(monkeypatch, key=False)
    assert af._llm_candidates() == []
    assert af.llm_extract("anything") == (None, "no LLM key in .env")


@pytest.mark.parametrize("provider", ["xai-oauth", "openai-codex", "nous", "unknown"])
def test_unsupported_transport_never_borrows_api_key(monkeypatch, provider):
    configure(monkeypatch, provider=provider)
    assert af._llm_candidates() == []


def test_explicit_pin_is_atomic(monkeypatch):
    configure(monkeypatch, provider="xai-oauth")
    monkeypatch.setattr(af, "ai_cfg", lambda: {
        "provider": "openrouter", "model": "pinned-model:free"})
    assert af._llm_candidates() == [
        ("fake-key", "https://openrouter.ai/api/v1", "pinned-model:free")]
    monkeypatch.setattr(af, "ai_cfg", lambda: {"provider": "openrouter"})
    assert af._llm_candidates() == []


def test_explicit_key_and_custom_api_root(monkeypatch):
    monkeypatch.setattr(af, "_hermes_model_cfg", lambda: {
        "provider": "custom", "default": "model", "key_env": "MY_KEY",
        "base_url": "https://example.invalid/api/v1/"})
    monkeypatch.setattr(af, "_load_env", lambda: {"MY_KEY": "fake"})
    assert af._llm_candidates() == [("fake", "https://example.invalid/api/v1", "model")]


@pytest.mark.parametrize("mode", ["codex_responses", "responses", "anthropic"])
def test_incompatible_api_mode_refuses(monkeypatch, mode):
    monkeypatch.setattr(af, "_hermes_model_cfg", lambda: {
        "provider": "openrouter", "default": "m", "api_mode": mode})
    monkeypatch.setattr(af, "_load_env", lambda: {"OPENROUTER_API_KEY": "fake"})
    assert af._llm_candidates() == []


def test_success_uses_provider_chat_path_and_bounded_router(monkeypatch):
    configure(monkeypatch)
    calls = []
    def fake(req, timeout):
        calls.append((req.full_url, json.loads(req.data), timeout))
        assert req.get_header("Authorization") == "Bearer fake-key"
        return io.BytesIO(json.dumps({"choices": [{"message": {
            "content": '{"is_signal": false, "reason": "recap"}'}}]}).encode())
    monkeypatch.setattr(af.urllib.request, "urlopen", fake)
    data, info = af.llm_extract('text containing "model": null')
    assert data == {"is_signal": False, "reason": "recap"}
    assert af._router is not None
    assert calls[0][0] == "https://openrouter.ai/api/v1/chat/completions"
    assert calls[0][1]["model"] == "configured-model:free"
    assert calls[0][1]["messages"][1]["content"] == 'text containing "model": null'
    assert calls[0][2] == 2


@pytest.mark.parametrize("status", [400, 401, 402, 404, 429])
def test_http_failure_is_plain_extraction_failure(monkeypatch, status):
    configure(monkeypatch)
    def fake(req, timeout):
        raise urllib.error.HTTPError(req.full_url, status, "fake rejection", {}, None)
    monkeypatch.setattr(af.urllib.request, "urlopen", fake)
    data, info = af.llm_extract("messy post")
    assert data is None
    assert "HTTPError" in info
    assert str(status) in info


def test_yaml_mapping_is_scoped_and_handles_end_of_file(monkeypatch):
    # Exercise the real reader, not the fixture's injected mapping.
    import importlib.util
    spec = importlib.util.spec_from_file_location("isolated_ai_filter", af.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    content = ('other:\n  key_env: WRONG\nmodel:\n  provider: openrouter\n'
               '  default: "vendor/model:free"\n  api_mode: chat_completions\n')
    monkeypatch.setattr("builtins.open", mock_open(read_data=content))
    assert module._hermes_model_cfg() == {
        "provider": "openrouter", "default": "vendor/model:free",
        "api_mode": "chat_completions"}

