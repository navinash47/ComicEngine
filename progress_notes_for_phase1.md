# Phase 1 progress notes

Goal: prove local FLUX + Nano Banana both render one Julius Caesar / Republic→Empire comic panel, with separate outputs + logs, and log seconds/image + VRAM for FLUX.

Date: 2026-07-15

---

## What we built

| Path | Role |
|------|------|
| `dev/shared/phase1_prompt.py` | Shared prompt + size/seed/model constants |
| `dev/windows/windows_dev.py` | FLUX.1-schnell local smoke (Windows GPU) |
| `dev/mac/mac_dev.py` | Nano Banana (`gemini-3.1-flash-image`) via `google-genai` |
| `.gitignore` | Ignores `runs/`, `.env`, caches |
| `.env.example` | Placeholder keys including `HF_TOKEN` |
| `runs/phase1/{flux_schnell,nano_banana}/{outputs,logs}/` | Artifacts (gitignored) |

Prompt (both models): comic panel of Julius Caesar before the Senate as Republic gives way to Empire.

---

## Process log

1. **Scaffold** — shared prompt, Windows/Mac scripts, folder layout, logging schema (`.log` + `.json` per run).

2. **HF gate (blocked first run)** — `black-forest-labs/FLUX.1-schnell` is Apache-2.0 but gated. First attempt → `GatedRepoError` 401 (no token). Token was pasted into `.env.example`; moved to `.env` and scrubbed example. Auth OK as HF user `avinashnandyala2`.

3. **First FLUX download** — ~7 min for 23 files into HF cache. Pipeline loaded (~441s cold / ~1s warm).

4. **Inference crash** — `enable_model_cpu_offload()` hard-crashed (Windows access violation `0xC0000005`) when moving the ~12GB transformer onto the RTX 5060 Ti (16GB VRAM). Stack showed crash during accelerate offload `.to(cuda)`, not in attention math. Machine also sits on ~16GB system RAM, which is tight for full BF16 FLUX in CPU offload.

5. **Mitigations that worked**
   - `pipe.transformer.set_attention_backend("_native_math")` (valid backends; `"eager"` is invalid in this diffusers version)
   - Disable flash / mem-efficient SDP; keep math SDP
   - **`enable_sequential_cpu_offload()`** instead of `enable_model_cpu_offload()` — moves submodules one at a time; avoids the AV

6. **Smoke** — 512² / 1-step red-circle success with sequential offload.

7. **Full FLUX run** — 800×1280, 4 steps, seed 42, Julius Caesar prompt → PNG + metrics written.

8. **Nano Banana** — `dev/mac/mac_dev.py` with `GOOGLE_API_KEY` (Interactions API primary, `generate_content` fallback). First attempt hit `MemoryError` while FLUX leftovers still held RAM; after killing Python processes, succeeded.

---

## Results

### FLUX.1-schnell (Windows / RTX 5060 Ti)

- Output: `runs/phase1/flux_schnell/outputs/julius_caesar_republic_to_empire.png` (800×1280)
- Log: `runs/phase1/flux_schnell/logs/run_20260715_101818.*`
- load: **1.25s** (warm cache)
- infer: **282.4s** — WARN vs target &lt;30s (sequential offload is slow)
- peak VRAM: **5.75GB** — PASS vs target &lt;12GB
- offload used: `sequential_cpu_offload` + `_native_math`

### Nano Banana / `gemini-3.1-flash-image`

- Output: `runs/phase1/nano_banana/outputs/julius_caesar_republic_to_empire.png` (1408×768)
- Log: `runs/phase1/nano_banana/logs/run_20260715_102515.*`
- infer: **9.8s**
- peak VRAM: n/a (API)

---

## How to re-run

```powershell
# Windows FLUX
conda activate myenv
python dev/windows/windows_dev.py
```

```bash
# Mac (or any machine with GOOGLE_API_KEY in .env)
conda activate myenv
python dev/mac/mac_dev.py
```

Needs: `HF_TOKEN` in `.env` (and HF gate accepted for FLUX.1-schnell); `GOOGLE_API_KEY` for Nano Banana.

---

## Open follow-ups (not done in Phase 1)

- Get FLUX under 30s/image: try `enable_model_cpu_offload()` again with more system RAM / larger pagefile, or quantized weights, once AV is understood.
- Keep secrets only in `.env` (never `.env.example`).
- Mac can re-run `mac_dev.py` on the Mac clone for a true Mac-side log if desired; generation itself is API-only.
