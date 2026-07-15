"""ComicEngine Mac env verification: API packages + .env keys."""

from __future__ import annotations

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
    import os

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

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
