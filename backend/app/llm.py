"""OpenAI-compatible chat completions gateway.

Security model (BYOK): each request may carry its own credentials via headers.
They live only in a contextvar for the duration of that request — never written
to the database, logs or the frontend. The server-side key from backend/.env is
NOT shared with visitors unless ALLOW_SERVER_KEY=true is set explicitly.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)

_ACTIVE_MODEL: str | None = None

# 本次请求的个人凭据。ContextVar 保证并发请求之间互不串用；
# 请求结束即丢弃，不写库、不记日志、不回显。
_REQUEST_CREDS: ContextVar[dict[str, str] | None] = ContextVar(
    "velum_request_credentials", default=None
)


class LLMUnavailable(Exception):
    """Raised when the model cannot be reached; callers should degrade gracefully."""


def bind_request_credentials(api_key: str, base_url: str, model: str) -> None:
    """Called by the HTTP middleware once per request. Values are trimmed here."""
    _REQUEST_CREDS.set({
        "api_key": (api_key or "").strip(),
        "base_url": (base_url or "").strip(),
        "model": (model or "").strip(),
    })


def clear_request_credentials() -> None:
    _REQUEST_CREDS.set(None)


def _server_key_allowed() -> bool:
    """Default FALSE: a server-side key must never be silently spent by visitors."""
    return os.getenv("ALLOW_SERVER_KEY", "false").strip().lower() == "true"


def _safe_base_url(value: str) -> str:
    """Only http(s) endpoints are allowed; strip userinfo and trailing slashes."""
    url = (value or "").strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    if "@" in url.split("://", 1)[-1].split("/", 1)[0]:
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    return url


def config() -> dict[str, Any]:
    creds = _REQUEST_CREDS.get() or {}
    personal_key = creds.get("api_key", "")
    env_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    # 个人 Key 优先；服务端 Key 仅在显式开关开启、且本次请求未带个人 Key 时兜底
    if personal_key and not personal_key.startswith("your-api-key"):
        api_key, key_source = personal_key, "personal"
    elif _server_key_allowed() and env_key and not env_key.startswith("your-api-key"):
        api_key, key_source = env_key, "server"
    else:
        api_key, key_source = "", "none"

    personal_base = creds.get("base_url", "")
    base_url = _safe_base_url(personal_base) if personal_base else os.getenv(
        "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
    ).rstrip("/")

    return {
        "api_key": api_key,
        "key_source": key_source,
        "base_url": base_url,
        "model": (creds.get("model") or os.getenv("DEEPSEEK_MODEL", "DeepSeek-V4.1-Flash-1017")).strip(),
        "fallback": os.getenv("DEEPSEEK_MODEL_FALLBACK", "deepseek-flash").strip(),
        "enabled": os.getenv("LLM_ENABLED", "true").strip().lower() == "true",
        "timeout": float(os.getenv("LLM_TIMEOUT", "40")),
        "server_key_available": bool(env_key) and not env_key.startswith("your-api-key"),
        "server_key_shared": _server_key_allowed(),
    }


def _candidates(preferred: str | None) -> list[str]:
    cfg = config()
    ordered = [preferred or _ACTIVE_MODEL or cfg["model"], cfg["model"], cfg["fallback"]]
    seen: set[str] = set()
    return [m for m in ordered if m and not (m in seen or seen.add(m))]


def _post(payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    cfg = config()
    url = cfg["base_url"] + "/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.load(res)


def chat(
    messages: list[dict[str, str]],
    json_mode: bool = False,
    max_tokens: int = 1200,
    temperature: float = 0.4,
    retries: int = 1,
) -> str:
    global _ACTIVE_MODEL
    cfg = config()
    if not cfg["enabled"]:
        raise LLMUnavailable("LLM_ENABLED=false")
    if not cfg["api_key"]:
        raise LLMUnavailable("未配置模型 Key（可在「模型连接」中填写），本次已回退规则稿")

    last_error = ""
    for model in _candidates(None):
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        for attempt in range(retries + 1):
            try:
                out = _post(payload, cfg["timeout"])
                content = out["choices"][0]["message"].get("content") or ""
                if not content.strip():
                    raise LLMUnavailable("模型返回空内容（可能被思考 token 占满）")
                _ACTIVE_MODEL = model
                return content
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="ignore")[:220]
                last_error = f"HTTP {exc.code}: {detail}"
                if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(0.6 * (attempt + 1))
                    continue
                break
            except Exception as exc:  # network / timeout / decode
                last_error = f"{type(exc).__name__}: {exc}"
                break
    raise LLMUnavailable(last_error or "未知错误")


def extract_json(text: str) -> dict[str, Any]:
    """Tolerant JSON extraction: models sometimes wrap JSON in prose or fences."""
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass
        if start >= 0:
            fragment = cleaned[start:]
            for suffix in ("}", '"}', '"]}', '"}}', "]}"):
                try:
                    obj = json.loads(fragment + suffix)
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    continue
    return {}


def probe() -> dict[str, Any]:
    cfg = config()
    started = time.time()
    try:
        reply = chat(
            [{"role": "user", "content": "只回复两个字：可用"}],
            max_tokens=96, temperature=0, retries=0,
        )
        return {
            "ok": True,
            "configured_model": cfg["model"],
            "active_model": _ACTIVE_MODEL,
            "base_url": cfg["base_url"],
            "latency_ms": round((time.time() - started) * 1000),
            "sample": reply.strip()[:30],
        }
    except Exception as exc:
        return {
            "ok": False,
            "configured_model": cfg["model"],
            "base_url": cfg["base_url"],
            "error": str(exc)[:300],
            "latency_ms": round((time.time() - started) * 1000),
        }


def status() -> dict[str, Any]:
    cfg = config()
    return {
        "enabled": cfg["enabled"],
        # 只报告「本次请求」的凭据来源，绝不回显服务端 Key 的任何片段
        "key_source": cfg["key_source"],
        "key_configured": bool(cfg["api_key"]),
        "configured_model": cfg["model"],
        "active_model": _ACTIVE_MODEL,
        "fallback_model": cfg["fallback"],
        "base_url": cfg["base_url"],
        "server_key_available": cfg["server_key_available"],
        "server_key_shared": cfg["server_key_shared"],
    }
