# provider-agnostic structured LLM call. Gemini-first (has a free tier),
# Ollama as the local/offline fallback (engineering guidelines, section 3/32: Ollama
# optional, proves provider-agnostic design without a paid dependency).
# callers are expected to catch exceptions and fall back to deterministic
# logic, so a missing/unreachable provider is never fatal - see
# planner.py / completion.py.
from __future__ import annotations

import json
import os
import time

import requests

from logger import get_logger

log = get_logger("llm")

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def active_provider() -> str | None:
    # which provider will actually be used, or None if the pipeline will fall
    # back to deterministic logic. the UI shows this so it's obvious during a
    # demo whether the LLM path is live.
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit in ("gemini", "ollama"):
        if explicit == "gemini":
            return "gemini" if os.getenv("GEMINI_API_KEY") else None
        return "ollama" if os.getenv("OLLAMA_BASE_URL") else None
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    if os.getenv("OLLAMA_BASE_URL"):
        return "ollama"
    return None


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    # models sometimes wrap json in a fence even when told not to
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
    return "\n".join(lines).strip()


def _parse_json_object(text: str) -> dict:
    # some models append trailing content after a valid JSON object even with
    # responseMimeType=application/json (e.g. a stray newline plus repeated
    # text) - json.loads() rejects the whole string in that case even though
    # the JSON itself is well-formed, so parse only the first JSON value and
    # ignore whatever follows it.
    return json.JSONDecoder().raw_decode(text)[0]


# nodes that only narrate already-computed facts (summarization, not
# planning/reasoning/recovery) route to the smaller model, per the
# smallest-sufficient-model rule (engineering guidelines, section 5):
# Flash-Lite for extraction/classification/normalization, Flash for
# planning/reasoning/recovery/interpretation.
LITE_NODES = frozenset({"completion", "signal_narrative", "digest"})


def _call_gemini(system: str, user: str, max_tokens: int, model_override: str | None = None) -> str:
    # "gemini-flash-latest" is an alias, so this keeps working when Google
    # retires a specific dated model (pinned versions get 404'd for new keys).
    model = model_override or os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    url = GEMINI_ENDPOINT.format(model=model)
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.2,
            # forces valid json back, which is exactly what every caller wants
            "responseMimeType": "application/json",
        },
    }
    # key goes in a header, not the query string, so it can't leak into
    # request URLs, tracebacks, or proxy logs
    response = requests.post(
        url,
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    return body["candidates"][0]["content"]["parts"][0]["text"]


def _call_ollama(system: str, user: str, max_tokens: int) -> str:
    # local/offline provider - no API key, just a reachable Ollama server.
    # Ollama's /api/chat endpoint mirrors the OpenAI-style chat shape closely
    # enough that this stays a thin wrapper like the Gemini path above.
    base_url = os.environ["OLLAMA_BASE_URL"].rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    response = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "format": "json",
            "options": {"num_predict": max_tokens, "temperature": 0.2},
        },
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    return body["message"]["content"]


def _model_name_for(provider: str, node: str = "") -> str:
    if provider == "gemini":
        if node in LITE_NODES:
            return os.getenv("GEMINI_MODEL_LITE") or os.getenv("GEMINI_MODEL", "gemini-flash-latest")
        return os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    return f"ollama:{os.getenv('OLLAMA_MODEL', 'llama3.1')}"


def _record_invocation(*, node: str, purpose: str, provider: str, model_name: str,
                        run_id: str | None, chat_session_id: str | None,
                        prompt_summary: str | None, input_ref_ids: dict | None,
                        output_summary: str | None, latency_ms: int,
                        fallback_triggered: bool, success: bool, error_message: str | None) -> None:
    # audit row for every LLM call, written from the single choke point every
    # caller already funnels through (Phase 29 - "LLM usage isn't visible" was
    # a missing audit table, not a UI problem). Never raises: a logging
    # failure must not take down the actual LLM call/pipeline it's observing.
    try:
        from backend.app.database.session import SessionLocal
        from backend.app.models.model_invocation import ModelInvocation

        db = SessionLocal()
        try:
            db.add(ModelInvocation(
                run_id=run_id, chat_session_id=chat_session_id, node=node, provider=provider,
                model_name=model_name, purpose=purpose, prompt_summary=prompt_summary,
                input_ref_ids=json.dumps(input_ref_ids) if input_ref_ids else None,
                output_summary=output_summary, latency_ms=latency_ms,
                fallback_triggered=fallback_triggered, success=success, error_message=error_message,
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        log.warning("failed to record model_invocation audit row", exc_info=True)


def call_structured(system: str, user: str, max_tokens: int = 2000, *,
                     node: str = "unspecified", purpose: str = "", run_id: str | None = None,
                     chat_session_id: str | None = None, prompt_summary: str | None = None,
                     input_ref_ids: dict | None = None) -> dict:
    # system prompt is responsible for describing the json shape; we just parse
    provider = active_provider()
    if provider is None:
        raise RuntimeError("No LLM provider configured (set GEMINI_API_KEY or OLLAMA_BASE_URL).")

    model_name = _model_name_for(provider, node)
    start = time.monotonic()
    try:
        raw = (
            _call_gemini(system, user, max_tokens, model_override=model_name)
            if provider == "gemini" else _call_ollama(system, user, max_tokens)
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        result = _parse_json_object(_strip_code_fence(raw))
        log.info(f"structured call completed via {provider}")
        _record_invocation(
            node=node, purpose=purpose, provider=provider, model_name=model_name,
            run_id=run_id, chat_session_id=chat_session_id,
            prompt_summary=prompt_summary or user[:500], input_ref_ids=input_ref_ids,
            output_summary=str(result)[:500], latency_ms=latency_ms,
            fallback_triggered=False, success=True, error_message=None,
        )
        return result
    except Exception as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        _record_invocation(
            node=node, purpose=purpose, provider=provider, model_name=model_name,
            run_id=run_id, chat_session_id=chat_session_id,
            prompt_summary=prompt_summary or user[:500], input_ref_ids=input_ref_ids,
            output_summary=None, latency_ms=latency_ms,
            fallback_triggered=True, success=False, error_message=str(exc)[:500],
        )
        raise
