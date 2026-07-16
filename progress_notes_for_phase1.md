# Phase 1 progress notes

Goal: prove local FLUX + Nano Banana both render one Julius Caesar / Republic→Empire comic panel, with separate outputs + logs, and log seconds/image + VRAM for FLUX. Later: unify Mac API clients and smoke-test FLUX via fal-ai at the same shared panel size.

Date: 2026-07-15

---

## What we built

| Path | Role |
|------|------|
| `dev/shared/phase1_prompt.py` | Shared prompt + size/seed/model constants (800×1280) |
| `dev/windows/windows_dev.py` | FLUX.1-schnell local smoke (Windows GPU) |
| `dev/mac/api_manager.py` | Unified Mac API clients: HF providers, Google, OpenAI, Anthropic |
| `dev/mac/mac_dev.py` | Interactive cells; default smoke = fal-ai FLUX via `ApiManager` |
| `env_setup/mac/requirements.txt` | Includes `huggingface_hub` (+ existing genai/LLM deps) |
| `.gitignore` | Ignores `runs/`, `.env`, caches |
| `runs/phase1/{flux_schnell,nano_banana,flux_fal}/{outputs,logs}/` | Artifacts (gitignored) |

Prompt (all models): comic panel of Julius Caesar before the Senate as Republic gives way to Empire.

Shared panel size for phone-scroll comics: **800×1280** (portrait).

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

8. **Nano Banana** — Google `gemini-3.1-flash-image` (Interactions API primary, `generate_content` fallback). First attempt hit `MemoryError` while FLUX leftovers still held RAM; after killing Python processes, succeeded. Logic later moved into `api_manager.GoogleAPI`.

9. **Mac API manager** — consolidated HF Inference providers (`fal-ai`, `together`, `replicate`, `nscale`, `wavespeed`, `hf-inference`), Google (chat + image), OpenAI (chat + DALL·E), Anthropic (chat) into `dev/mac/api_manager.py`. `mac_dev.py` is cell-friendly: pick provider/model in-code, no CLI args.

10. **fal-ai FLUX smoke** — `ApiManager.hf_image(..., provider="fal-ai")`. First run returned provider default **1024×768**; updated call to pass `width=800`, `height=1280` (shared constants) so output matches portrait comic size. Keys: prefer `FAL_KEY`, fall back to `HF_TOKEN`.

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

- Output: `runs/phase1/nano_banana/outputs/julius_caesar_republic_to_empire.png` (1408×768 then resized toward shared size in script)
- Log: `runs/phase1/nano_banana/logs/run_20260715_102515.*`
- infer: **9.8s**
- peak VRAM: n/a (API)

### FLUX.1-schnell via fal-ai (HF InferenceClient)

- Output: `runs/phase1/flux_fal/outputs/julius_caesar_republic_to_empire.png` (**800×1280**)
- Log: `runs/phase1/flux_fal/logs/run_20260716_035141.*`
- infer: **2.6s**
- peak VRAM: n/a (API)
- Note: ~100× faster than local sequential-offload FLUX on this machine for the same shared size

---

## How to re-run

```powershell
# Windows local FLUX
conda activate myenv
python dev/windows/windows_dev.py
```

```bash
# Mac API — default cell is fal-ai FLUX (800×1280)
conda activate myenv
pip install -r env_setup/mac/requirements.txt   # includes huggingface_hub
python dev/mac/mac_dev.py
```

Needs in repo-root `.env`:

- `HF_TOKEN` — local FLUX gate + non-fal HF providers
- `FAL_KEY` — preferred for `provider="fal-ai"` (falls back to `HF_TOKEN` if unset)
- `GOOGLE_API_KEY` — Nano Banana / Gemini (via `api.google_image` / `api.google_chat`)
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` — chat (and OpenAI images) when needed

Interactive examples (commented in `mac_dev.py`): other HF providers, Google Nano Banana, OpenAI/Anthropic chat.

---

## Open follow-ups

- Get local FLUX under 30s/image: try `enable_model_cpu_offload()` again with more system RAM / larger pagefile, or quantized weights, once AV is understood.
- Keep secrets only in `.env` (never commit keys).
- Optional: re-run Nano Banana through `api.google_image` and save under a fresh log for apples-to-apples vs fal at 800×1280.
- Compare quality across local FLUX / fal FLUX / Nano Banana for the same prompt + size.
