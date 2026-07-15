# ComicEngine — Mac setup

Mac setup for API clients and `.env` keys (Anthropic, OpenAI, Google AI Studio).  
fal.ai and RunPod are skipped for now.

This is separate from the Windows GPU stack under `env_setup/windows/`.

## Prerequisites

- conda env `myenv` (or another Python 3.11+ env)
- Accounts + API keys for Anthropic, OpenAI, and Google AI Studio

## Setup

From the ComicEngine repo root:

```bash
conda activate myenv
pip install -r env_setup/mac/requirements.txt
```

Create secrets file (do this once):

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```bash
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

**Never commit `.env`.** It is listed in `.gitignore`.  
`.env.example` is safe to commit (empty placeholders only).

## Verify

```bash
conda activate myenv
python env_setup/mac/verify.py
```

Expects:

- imports for `dotenv`, `anthropic`, `openai`, `google.genai`
- `.env` present at the repo root
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `GOOGLE_API_KEY` set (non-empty)

Optional git check:

```bash
git check-ignore -v .env
```

Should report that `.gitignore` ignores `.env`.

## What we configured

| Item | Purpose |
|------|---------|
| `env_setup/mac/requirements.txt` | Mac pip deps for LLM/API clients |
| `.env` / `.env.example` | Local API keys (Anthropic, OpenAI, Google) |
| `.gitignore` | Keeps `.env` out of git |
| `env_setup/mac/verify.py` | Confirms packages + keys load |

fal.ai (`FAL_KEY`) and RunPod (`RUNPOD_API_KEY`) are intentionally not required yet.

## Phase 1 — Nano Banana (Mac)

From the ComicEngine repo root (after Windows/Mac sync of `dev/`):

```bash
conda activate myenv
pip install -r env_setup/mac/requirements.txt   # includes pillow
python env_setup/mac/verify.py                  # optional
python dev/mac/mac_dev.py
```

Uses `GOOGLE_API_KEY` and model `gemini-3.1-flash-image`. Artifacts land in:

`runs/phase1/nano_banana/{outputs,logs}/`

