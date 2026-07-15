"""ComicEngine Mac env verification: API packages, .env keys, hello calls."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY")
REQUIRED_IMPORTS = (
    ("dotenv", "python-dotenv"),
    ("anthropic", "anthropic"),
    ("openai", "openai"),
    ("google.genai", "google-genai"),
)


def _require_key(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise RuntimeError(f"{name} is missing or empty")
    return value


def hello_anthropic() -> int:
    import anthropic

    client = anthropic.Anthropic(api_key=_require_key("ANTHROPIC_API_KEY"))
    raw = client.messages.with_raw_response.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16,
        messages=[{"role": "user", "content": "hello"}],
    )
    return raw.status_code


def hello_openai() -> int:
    import openai

    client = openai.OpenAI(api_key=_require_key("OPENAI_API_KEY"))
    raw = client.chat.completions.with_raw_response.create(
        model="gpt-4o-mini",
        max_tokens=16,
        messages=[{"role": "user", "content": "hello"}],
    )
    return raw.status_code


def hello_google() -> int:
    from google import genai

    client = genai.Client(api_key=_require_key("GOOGLE_API_KEY"))
    # google-genai does not expose with_raw_response; success means HTTP 200.
    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents="hello",
    )
    if not getattr(response, "text", None) and not getattr(response, "candidates", None):
        raise RuntimeError("empty Google response")
    return 200


def main() -> int:
    print("=== ComicEngine Mac env verify ===\n")
    print(f"python: {sys.executable}")
    print(f"repo:   {REPO_ROOT}\n")

    failed = False

    for module_name, pip_name in REQUIRED_IMPORTS:
        try:
            __import__(module_name)
            print(f"OK: import {module_name}")
        except ImportError as exc:
            print(f"FAIL: import {module_name} ({exc})")
            print(f"      fix: pip install {pip_name}")
            failed = True

    if failed:
        return 1

    from dotenv import load_dotenv

    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        print(f"FAIL: missing {env_path}")
        print("      copy .env.example to .env and fill in your keys")
        return 1
    print(f"OK: found {env_path.name}")

    load_dotenv(env_path)

    for key in REQUIRED_KEYS:
        value = (os.getenv(key) or "").strip()
        if value:
            print(f"OK: {key} is set ({len(value)} chars)")
        else:
            print(f"FAIL: {key} is missing or empty")
            failed = True

    if failed:
        print("\nFill the missing keys in .env (never commit that file).")
        return 1

    print("\n--- Live API hello checks ---")
    checks = (
        ("Anthropic", hello_anthropic),
        ("OpenAI", hello_openai),
        ("Google", hello_google),
    )
    for name, fn in checks:
        try:
            status = fn()
            if status == 200:
                print(f'OK: {name} hello -> {status}')
            else:
                print(f'FAIL: {name} hello -> {status} (expected 200)')
                failed = True
        except Exception as exc:
            print(f"FAIL: {name} hello ({type(exc).__name__}: {exc})")
            failed = True

    if failed:
        print("\nOne or more API hello checks failed.")
        return 1

    print('\nSuccess: a "hello" call to each API returns 200.')
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
