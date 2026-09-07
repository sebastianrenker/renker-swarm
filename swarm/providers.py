"""LLM provider rotation with rate-limit backoff.

A provider is only "available" when its key(s) are present in the environment,
so the swarm automatically runs on whatever free tiers you have wired up. Keys
come from env vars (GitHub Actions secrets, or the VM's .env file):

    GEMINI_API_KEY          Google AI Studio free tier
    GROQ_API_KEY            Groq free tier
    OPENROUTER_API_KEY      OpenRouter (use ":free" models)
    CF_ACCOUNT_ID + CF_API_TOKEN   Cloudflare Workers AI free tier
    OLLAMA_HOST             optional — local small models (set only on the VM)

On a 429 / "busy", the provider is put on a short cooldown and the next one is
tried. Nothing here ever asks you for a paid key.
"""
from __future__ import annotations
import os
import time

import requests


class RateLimited(Exception):
    """Provider is busy / over quota — rest it and try the next one."""


class ProviderError(Exception):
    """Provider failed for another reason — try the next one."""


def _post(url, headers=None, params=None, payload=None, timeout=60):
    r = requests.post(url, headers=headers, params=params, json=payload, timeout=timeout)
    if r.status_code in (429, 503):
        raise RateLimited(f"{r.status_code} {r.text[:160]}")
    if r.status_code >= 400:
        raise ProviderError(f"{r.status_code} {r.text[:160]}")
    return r.json()


# ---- individual providers -------------------------------------------------

def _gemini(system, prompt, cfg, timeout):
    key = os.getenv("GEMINI_API_KEY")
    model = cfg.get("model", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": cfg.get("max_output_tokens", 800)},
    }
    data = _post(url, params={"key": key}, payload=payload, timeout=timeout)
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _openai_compatible(base, key, system, prompt, cfg, timeout, extra_headers=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": cfg.get("max_output_tokens", 800),
    }
    data = _post(f"{base}/chat/completions", headers=headers, payload=payload, timeout=timeout)
    return data["choices"][0]["message"]["content"].strip()


def _groq(system, prompt, cfg, timeout):
    return _openai_compatible(
        "https://api.groq.com/openai/v1", os.getenv("GROQ_API_KEY"),
        system, prompt, cfg, timeout)


def _openrouter(system, prompt, cfg, timeout):
    return _openai_compatible(
        "https://openrouter.ai/api/v1", os.getenv("OPENROUTER_API_KEY"),
        system, prompt, cfg, timeout,
        extra_headers={"HTTP-Referer": "https://github.com", "X-Title": "Renker Swarm"})


def _cloudflare(system, prompt, cfg, timeout):
    acct = os.getenv("CF_ACCOUNT_ID")
    token = os.getenv("CF_API_TOKEN")
    model = cfg.get("model", "@cf/meta/llama-3.1-8b-instruct")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}"
    payload = {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt}]}
    data = _post(url, headers={"Authorization": f"Bearer {token}"},
                 payload=payload, timeout=timeout)
    return data["result"]["response"].strip()


def _ollama(system, prompt, cfg, timeout):
    host = os.getenv("OLLAMA_HOST", cfg.get("host", "http://127.0.0.1:11434"))
    payload = {
        "model": cfg.get("model", "qwen2.5:7b"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}],
        "stream": False,
    }
    r = requests.post(f"{host}/api/chat", json=payload, timeout=timeout)
    if r.status_code >= 400:
        raise ProviderError(f"{r.status_code} {r.text[:160]}")
    return r.json()["message"]["content"].strip()


_IMPL = {
    "gemini": _gemini,
    "groq": _groq,
    "openrouter": _openrouter,
    "cloudflare": _cloudflare,
    "ollama": _ollama,
}

_HAS_KEY = {
    "gemini": lambda: bool(os.getenv("GEMINI_API_KEY")),
    "groq": lambda: bool(os.getenv("GROQ_API_KEY")),
    "openrouter": lambda: bool(os.getenv("OPENROUTER_API_KEY")),
    "cloudflare": lambda: bool(os.getenv("CF_ACCOUNT_ID") and os.getenv("CF_API_TOKEN")),
    "ollama": lambda: bool(os.getenv("OLLAMA_HOST")),  # opt-in (set only on the VM)
}


class Router:
    """Tries configured providers in order, skipping ones on cooldown."""

    def __init__(self, providers_cfg):
        self.cfg = providers_cfg or {}
        self.order = self.cfg.get("order", list(_IMPL))
        self.cooldown = self.cfg.get("cooldown_seconds", 90)
        self._cool_until = {}  # provider -> epoch seconds

    def available(self):
        now = time.time()
        return [p for p in self.order
                if p in _IMPL and _HAS_KEY[p]() and self._cool_until.get(p, 0) <= now]

    def call(self, system, prompt, timeout=60):
        """Return (text, provider_name) on success, else (None, reason)."""
        reason = "no provider available"
        for p in self.available():
            try:
                text = _IMPL[p](system, prompt, self.cfg.get(p, {}), timeout)
                if text:
                    return text, p
                reason = f"{p}: empty response"
            except RateLimited as e:
                self._cool_until[p] = time.time() + self.cooldown
                reason = f"{p}: rate-limited ({e})"
            except Exception as e:  # noqa: BLE001 — try the next provider
                reason = f"{p}: {e}"
        return None, reason
