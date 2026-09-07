"""Minimal .env loader — no external dependency.

Reads KEY=VALUE lines from a `.env` file at the project root and puts them into
os.environ (without overwriting anything already set). This is what makes the
local "paste your key into .env and run" flow work. On GitHub Actions there is
no .env file — the keys come from repository Secrets instead — so this is a no-op
there.
"""
import os
import pathlib


def load_env(path=None):
    p = pathlib.Path(path) if path else pathlib.Path(__file__).resolve().parent.parent / ".env"
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
            val = val[1:-1]
        elif " #" in val:  # tolerate an inline comment after the value
            val = val.split(" #", 1)[0].strip()
        if key and val and not os.environ.get(key):
            os.environ[key] = val
