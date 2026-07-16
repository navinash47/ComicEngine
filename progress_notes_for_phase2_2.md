# Phase 2 Step 2.2 progress notes — seed-grid style stability

Goal: confirm the locked `storybook_gouache` style holds across seeds (Claude playbook Step 2.2). Generate the same style + **one** subject (`betrayal_aftermath`) across a grid of ≥9 seeds on both models; pass if ≥8/9 read as the same medium/mood. Compare **3 detail levels** (verbose → sparse) and log every generation to timestamped CSV for cost tracking.

Date: 2026-07-16

---

## What we built

| Path | Role |
|------|------|
| `dev/shared/phase2_styles.py` | `STEP22_STYLE_ID`, `DETAIL_LEVELS` (**3**: d1/d3/d5), `SEEDS`, `build_prompt_step22()`, `freeze_config_step22()` |
| `dev/mac/phase2.py` | `run_step22()`; keeps `run_step21()`. Default `__main__` runs Step 2.2 |
| `runs/phase2/step22/{outputs,logs}/` + `styles.json` + CSVs | Artifacts (gitignored) |

Matrix: **1 style × 1 subject × 3 detail levels × 9 seeds × 2 models = 54 images**  
Per model: **9 × 1 × 3 = 27** (cost cap).

### Locked style
- `storybook_gouache` — warm painterly gouache + colored pencil (winner from Step 2.1)

### Detail levels (`betrayal_aftermath` only)
1. `d1_max` — dense sensory + color locks (green laurel, ivory/cream scroll, cool marble)
2. `d3_medium` — Step 2.1 `betrayal_aftermath` wording (baseline control)
3. `d5_min` — one-line gist

### Seeds / samples
- Seeds `0..8` (9 total)
- `flux_fal`: pass `seed=` through HF InferenceClient → fal-ai; if rejected, retry without seed
- `nano_banana`: no seed API — 9 independent samples with `seed_supported=false`

### Models
- `flux_fal` — `black-forest-labs/FLUX.1-schnell` via fal-ai
- `nano_banana` — Google `gemini-3.1-flash-image`

### CSV goal log
- Master: `runs/phase2/step22/goal_log_step22.csv` (rewritten each run)
- Per-run snapshot: `runs/phase2/step22/goal_log_step22_{run_id}.csv`

Columns:

`run_id, stamp, logged_at, style_id, detail_id, detail_rank, model_key, model_id, seed, seed_supported, prompt, output_path, width, height, infer_seconds, ok, skipped, error, style_pass, notes`

`run_id` / `stamp` = UTC run start (`YYYYMMDD_HHMMSS`); `logged_at` = ISO timestamp when that row finished.

---

## Process log

1. **Modules** — Step 2.2 helpers + runner with seed fallback and dual CSV (master + timestamped).

2. **First attempt (aborted)** — started the original 5-detail × 9 × 2 = 90 matrix. Stopped mid-run for cost; had produced most of `d1`–`d4` plus partial `d5`.

3. **Scope trim** — cut to **3** detail levels (`d1_max`, `d3_medium`, `d5_min`) → 54 images (27/model). Dropped `d2_high` / `d4_low`. Added `run_id` + `logged_at` to CSV; each run also writes `goal_log_step22_{stamp}.csv`.

4. **Canonical run** — `run_id=20260716_183822` with `skip_existing=True`:
   - **54/54 ok**
   - Skipped already-paid `d1`/`d3` (+ most `d5` FLUX); generated remaining `d5_min` (esp. all 9 Nano Banana)
   - Nano Banana new gens ~7.7s avg; FLUX gap-fill ~2.8s
   - Artifacts: `goal_log_step22.csv`, `goal_log_step22_20260716_183822.csv`, `logs/run_20260716_183822.{log,json}`

5. **Visual QA (2026-07-16)** — sampled seeds across all 3 details × both models for Claude gate (≥8/9 same medium/mood). Also checked green-wreath fidelity on `d1_max` and content drift on sparse prompts.

---

## Results (scorecard)

Gate = ≥8/9 images share storybook gouache medium/mood (soft painterly texture, warm golden light, muted historical palette, no anime/cel). Secondary = prop fidelity (green wreath, scroll, no blood-metaphor clutter).

| Detail | Nano Banana | FLUX fal | Notes |
|--------|-------------|----------|-------|
| `d1_max` | **PASS** (~9/9) | **PASS** (~9/9) | Strongest prop lock: green laurel + cream scroll consistently. FLUX sometimes renders a branch vs full wreath; red wax seals OK, occasional red berry accents (watch, not blood). |
| `d3_medium` | **PASS** (~9/9) | **PASS** (~9/9) | Style holds. Nano occasionally shifts wreath to gold (e.g. seed5) — style still on, color lock weaker than d1. |
| `d5_min` | **PASS** (~9/9) | **PASS w/ notes** (~8–9/9) | Style medium/mood still reads storybook-painterly, but composition drifts more (extra lamps/flowers/ribbons). FLUX seed5 swapped in yellow flowers + red ribbon — content loose, style mostly OK. |

**Claude Step 2.2 gate: PASSED** for both models on all three detail levels (style stability across seeds).

**Recommendation:** keep **`storybook_gouache`** locked. Prefer **`d1_max`** (or at least green-wreath color tokens) when prop fidelity matters; use `d3_medium` as the lean baseline. Avoid relying on `d5_min` alone for production prompts — too sparse, more layout inventiveness especially on FLUX. Proceed to Step 2.3 (cross-scene).

---

## How to re-run

```bash
conda activate myenv
python dev/mac/phase2.py                 # 3×9×2 = 54 images

# resume without re-billing existing files:
python -c "from dev.mac.phase2 import run_step22; raise SystemExit(run_step22(skip_existing=True))"

# Step 2.1 still available:
python -c "from dev.mac.phase2 import run_step21; raise SystemExit(run_step21())"
```

Needs in repo-root `.env`: `FAL_API_KEY` (or `FAL_KEY`) for fal-ai FLUX, `GOOGLE_API_KEY` for Nano Banana.

---

## Open follow-ups

- Optional: fill CSV `style_pass` / `notes` columns to match this scorecard row-by-row.
- Optional: delete orphan `d2_high` / `d4_low` PNGs from the aborted 5-level run.
- Step 2.3: cross-scene style test (interior / exterior / night / landscape / close-up) with locked `storybook_gouache` (+ prefer d1-level color tokens where props matter).
- Step 2.4: freeze generation settings once cross-scene also passes.
