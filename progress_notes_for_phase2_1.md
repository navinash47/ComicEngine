# Phase 2 Step 2.1 progress notes — style string bake-off

Goal: pick one canonical style string for the series (Claude playbook Step 2.1). Render 5 candidate style strings against 3 people-free subjects from the Julius Caesar / Ides of March betrayal story, on 2 models, and score each style pass/fail for medium/mood consistency. Phase 1 untouched.

Date: 2026-07-16

---

## What we built

| Path | Role |
|------|------|
| `dev/shared/phase2_styles.py` | 5 style strings, 3 Caesar-story subjects, model specs, `build_prompt()`, `freeze_config()` |
| `dev/mac/phase2.py` | Step 2.1 matrix runner via `ApiManager`; filterable (`styles=`, `models=`, `subjects=`, `skip_existing=`) |
| `dev/mac/api_manager.py` | One-line fix: fal-ai key resolution now also accepts `FAL_API_KEY` (the name used in `.env`) |
| `runs/phase2/step21/{outputs,logs}/` + `styles.json` + `scorecard_step21.json` | Artifacts (gitignored) |

Matrix: **5 styles × 3 subjects × 2 models = 30 images**, all at the shared 800×1280 portrait size (Google output resized from 2:3 as in Phase 1).

### Style candidates
1. `storybook_gouache` — Claude's example string (warm painterly gouache + colored pencil)
2. `watercolor_wash` — soft wet watercolor, paper tooth, gentle blooms
3. `pastel_chalk` — dry pastel / chalk texture, dusty pigments
4. `ink_wash_sepia` — warm sepia ink wash + light watercolor tint
5. `colored_pencil_cozy` — colored-pencil hatching, close-lamp mood

All strings include medium + lighting + form + muted historical palette + negatives (`NOT anime, NOT manga, no cel shading, no hard ink outlines, no photorealism`).

### Subjects (Julius Caesar betrayal story, people-free)
1. `senate_interior` — empty Curia of Pompey, tiered benches, cool morning light
2. `betrayal_aftermath` — Ides of March rendered symbolically: fallen laurel wreath + dropped scroll on marble steps, long shadows, no people/blood/weapons (tasteful-conflict pattern from the playbook)
3. `forum_dusk` — empty Forum at dusk, guttering torchlight, "city after" mood

### Models
- `flux_fal` — `black-forest-labs/FLUX.1-schnell` via HF InferenceClient `provider="fal-ai"`
- `nano_banana` — Google `gemini-3.1-flash-image` via `api.google_image`

---

## Process log

1. **Modules** — wrote `phase2_styles.py` (config) and `phase2.py` (runner, same cell style as `mac_dev.py`). No Phase 1 files or entrypoints changed.

2. **First full run (30 images)** — 20/30 ok. All 15 Nano Banana images succeeded (~6–10s each). 10 FLUX calls failed with **HTTP 402 Payment Required**: HF Inference monthly included credits depleted mid-run, because the client was authenticating with `HF_TOKEN` instead of the fal key.

3. **Root cause + fix** — `.env` names the fal key `FAL_API_KEY`, but `api_manager.py` only looked for `FAL_KEY` and silently fell back to `HF_TOKEN`. Added `FAL_API_KEY` to the lookup chain (`FAL_KEY` → `FAL_API_KEY` → `HF_TOKEN`).

4. **Retry** — added `skip_existing=True` to the runner and re-ran FLUX-only; the 10 missing images generated in ~2–3s each. Matrix complete at 30/30.

5. **Visual QA (per style, 3 subjects, both models)** — checked same medium, same mood/lighting family, coherent palette:
   - Two styles needed a string revision:
     - `pastel_chalk` rendered as generic painterly/concept-art, not chalk → rewrote with "dry pastel and chalk sticks on textured pastel paper, heavy chalk dust, powdery grain, NOT oil paint, NOT digital smooth rendering".
     - `ink_wash_sepia` broke monochrome on `forum_dusk` (full-color purple/orange sky) → added "strictly muted sepia ochre-and-ivory monochrome palette throughout, no full-color sky".
   - Deleted and regenerated those 12 images with the revised strings; refreshed `styles.json`.

6. **Re-score** — sepia now holds monochrome across all 3 subjects; pastel improved but its medium identity is still the weakest of the five (leans charcoal/painterly).

---

## Results (scorecard)

Full details in `runs/phase2/step21/scorecard_step21.json`. Gate = medium/mood unmistakably consistent across the 3 subjects (primary judge: Nano Banana).

| Style | Nano Banana | FLUX fal | Notes |
|-------|-------------|----------|-------|
| `storybook_gouache` | PASS | PASS w/ notes | Strongest overall; betrayal beat reads ominous-but-gentle. FLUX once added red petals that can read as a blood metaphor — keep the `no blood` negatives prominent in later steps |
| `watercolor_wash` | PASS | PASS | Clear watercolor identity, soft bedtime mood held everywhere |
| `pastel_chalk` | borderline | borderline | Improved after revision but medium lock still weaker than the others |
| `ink_wash_sepia` | PASS | PASS | Locked after monochrome tightening; more solemn/documentary than cozy |
| `colored_pencil_cozy` | PASS | PASS | Visible hatching + warm lamp mood consistent |

**Recommendation:** lock **`storybook_gouache`** as the series style (runner-up `watercolor_wash`; intimate alternative `colored_pencil_cozy`). Proceed to Step 2.2 (seed-grid stability) with the chosen string.

---

## How to re-run

```bash
conda activate myenv
python dev/mac/phase2.py                 # full 5×3×2 matrix

# filtered, skipping images that already exist:
python -c "from dev.mac.phase2 import run_step21; run_step21(styles=['storybook_gouache'], skip_existing=True)"
```

Needs in repo-root `.env`: `FAL_API_KEY` (or `FAL_KEY`) for fal-ai FLUX, `GOOGLE_API_KEY` for Nano Banana.

---

## Open follow-ups

- Step 2.2: seed-grid stability test (≥9 seeds) on `storybook_gouache`; note FLUX.1-schnell via the HF text_to_image call doesn't expose a seed parameter — decide whether to bake seeds via fal directly or judge stability on Nano Banana only.
- Either revise `pastel_chalk` once more or drop it from contention.
- Watch the FLUX tendency to sneak in blood-metaphor details (red petals) on the betrayal beat; consider strengthening negatives at the subject level.
- Keep `HF_TOKEN` out of the fal path (fixed) so HF Inference credits aren't consumed accidentally.
