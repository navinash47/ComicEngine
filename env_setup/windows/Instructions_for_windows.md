# ComicEngine

Windows GPU env verification for RTX 50-series (sm_120 / capability `(12, 0)`).

## Setup

```powershell
conda activate myenv
pip install -r env_setup/windows/requirements.txt
```

## Verify

```powershell
python env_setup/windows/verify.py
```

Expects CUDA capability `(12, 0)` and no `sm_120` warning.

## Phase 1 — FLUX.1-schnell (gated Hugging Face)

`black-forest-labs/FLUX.1-schnell` is Apache-2.0 but **gated**. Before the first download:

1. Open https://huggingface.co/black-forest-labs/FLUX.1-schnell and click **Agree and access repository**.
2. Create a Read token at https://huggingface.co/settings/tokens
3. Either:
   - `hf auth login` and paste the token, or
   - copy `.env.example` → `.env` and set `HF_TOKEN=...`

Then:

```powershell
conda activate myenv
python dev/windows/windows_dev.py
```

Artifacts land in `runs/phase1/flux_schnell/{outputs,logs}/`.
