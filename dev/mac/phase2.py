# %%
"""Phase 2 runners (via ApiManager).

Step 2.1 — style string bake-off → runs/phase2/step21/
Step 2.2 — seed-grid style stability → runs/phase2/step22/

Isolated from Phase 1: do not run mac_dev.py from here.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image

# %%
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.mac.api_manager import ApiManager  # noqa: E402
from dev.shared.phase2_styles import (  # noqa: E402
    DETAIL_IDS,
    DETAIL_RANKS,
    IMAGE_ASPECT_RATIO,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    MODEL_KEYS,
    MODELS,
    SEEDS,
    STEP22_STYLE_ID,
    STYLE_IDS,
    SUBJECT_IDS,
    build_prompt,
    build_prompt_step22,
    freeze_config,
    freeze_config_step22,
    model_supports_seed,
    output_filename,
    output_filename_step22,
)

RUN_ROOT_21 = REPO_ROOT / "runs" / "phase2" / "step21"
OUTPUTS_DIR_21 = RUN_ROOT_21 / "outputs"
LOGS_DIR_21 = RUN_ROOT_21 / "logs"

RUN_ROOT_22 = REPO_ROOT / "runs" / "phase2" / "step22"
OUTPUTS_DIR_22 = RUN_ROOT_22 / "outputs"
LOGS_DIR_22 = RUN_ROOT_22 / "logs"
CSV_PATH_22 = RUN_ROOT_22 / "goal_log_step22.csv"

CSV_FIELDS_22 = [
    "run_id",
    "stamp",
    "logged_at",
    "style_id",
    "detail_id",
    "detail_rank",
    "model_key",
    "model_id",
    "seed",
    "seed_supported",
    "prompt",
    "output_path",
    "width",
    "height",
    "infer_seconds",
    "ok",
    "skipped",
    "error",
    "style_pass",
    "notes",
]

# Backward-compatible aliases used by Step 2.1 helpers below.
RUN_ROOT = RUN_ROOT_21
OUTPUTS_DIR = OUTPUTS_DIR_21
LOGS_DIR = LOGS_DIR_21

# %%
api = ApiManager()


# %%
def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _as_list(values: Iterable[str] | None, default: tuple[str, ...]) -> list[str]:
    if values is None:
        return list(default)
    return list(values)


def _as_seed_list(values: Iterable[int] | None) -> list[int]:
    if values is None:
        return list(SEEDS)
    return [int(v) for v in values]


def _generate(
    prompt: str,
    model_key: str,
    *,
    seed: int | None = None,
) -> Image.Image:
    spec = MODELS[model_key]
    backend = spec["backend"]
    if backend == "hf":
        kwargs: dict = {
            "provider": spec["provider"],
            "model": spec["model_id"],
            "width": IMAGE_WIDTH,
            "height": IMAGE_HEIGHT,
        }
        if seed is not None and model_supports_seed(model_key):
            kwargs["seed"] = seed
        return api.hf_image(prompt, **kwargs)
    if backend == "google":
        return api.google_image(
            prompt,
            model=spec["model_id"],
            aspect_ratio=IMAGE_ASPECT_RATIO,
        )
    raise ValueError(f"unknown backend {backend!r} for model_key {model_key!r}")


def _maybe_resize(img: Image.Image, lines: list[str]) -> Image.Image:
    if img.size == (IMAGE_WIDTH, IMAGE_HEIGHT):
        return img
    lines.append(f"api_size:     {img.size[0]}x{img.size[1]} -> resize")
    return img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)


def _csv_row_22(row: dict) -> dict:
    return {k: row.get(k, "") for k in CSV_FIELDS_22}


def _write_csv_22(rows: list[dict], *, run_csv: Path | None = None) -> None:
    """Write the cumulative master CSV and optionally a per-run timestamped copy."""
    CSV_PATH_22.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH_22.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS_22, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(_csv_row_22(row))
    if run_csv is not None:
        with run_csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS_22, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(_csv_row_22(row))


# %%
def run_step21(
    styles: Iterable[str] | None = None,
    models: Iterable[str] | None = None,
    subjects: Iterable[str] | None = None,
    *,
    skip_existing: bool = False,
) -> int:
    """Run style × subject × model matrix; write PNGs + logs under runs/phase2/step21/."""
    style_ids = _as_list(styles, STYLE_IDS)
    subject_ids = _as_list(subjects, SUBJECT_IDS)
    model_keys = _as_list(models, MODEL_KEYS)

    for sid in style_ids:
        if sid not in STYLE_IDS:
            raise KeyError(f"unknown style {sid!r}; expected one of {STYLE_IDS}")
    for sub in subject_ids:
        if sub not in SUBJECT_IDS:
            raise KeyError(f"unknown subject {sub!r}; expected one of {SUBJECT_IDS}")
    for mk in model_keys:
        if mk not in MODEL_KEYS:
            raise KeyError(f"unknown model {mk!r}; expected one of {MODEL_KEYS}")

    OUTPUTS_DIR_21.mkdir(parents=True, exist_ok=True)
    LOGS_DIR_21.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()

    styles_path = RUN_ROOT_21 / "styles.json"
    styles_path.write_text(
        json.dumps(freeze_config(), indent=2) + "\n", encoding="utf-8"
    )

    total = len(style_ids) * len(subject_ids) * len(model_keys)
    results: list[dict] = []
    lines: list[str] = [
        "=== ComicEngine Phase 2 Step 2.1 — style bake-off ===",
        f"utc:        {stamp}",
        f"styles:     {style_ids}",
        f"subjects:   {subject_ids}",
        f"models:     {model_keys}",
        f"size:       {IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        f"matrix:     {total} images",
        f"skip_existing: {skip_existing}",
        f"styles_json:{styles_path.relative_to(REPO_ROOT).as_posix()}",
        "",
    ]

    print(
        f"Step 2.1 bake-off: {len(style_ids)} styles × "
        f"{len(subject_ids)} subjects × {len(model_keys)} models = {total}"
        + (" (skip existing)" if skip_existing else "")
    )

    ok_count = 0
    skipped = 0
    idx = 0
    for style_id in style_ids:
        for subject_id in subject_ids:
            for model_key in model_keys:
                idx += 1
                prompt = build_prompt(style_id, subject_id)
                filename = output_filename(style_id, subject_id, model_key)
                output_path = OUTPUTS_DIR_21 / filename
                rel_output = output_path.relative_to(REPO_ROOT).as_posix()
                model_id = MODELS[model_key]["model_id"]

                entry: dict = {
                    "style_id": style_id,
                    "subject_id": subject_id,
                    "model_key": model_key,
                    "model_id": model_id,
                    "prompt": prompt,
                    "output_path": rel_output,
                    "width": None,
                    "height": None,
                    "infer_seconds": None,
                    "ok": False,
                    "skipped": False,
                    "error": None,
                }
                header = f"[{idx}/{total}] {filename}"
                print(f"{header} ...")
                lines.append(header)

                if skip_existing and output_path.is_file():
                    entry["ok"] = True
                    entry["skipped"] = True
                    skipped += 1
                    ok_count += 1
                    with Image.open(output_path) as existing:
                        entry["width"], entry["height"] = existing.size
                    lines.append(f"  skipped existing: {rel_output}")
                    print(f"  skipped existing")
                    results.append(entry)
                    lines.append("")
                    continue

                try:
                    t0 = time.perf_counter()
                    img = _generate(prompt, model_key)
                    infer_s = time.perf_counter() - t0
                    entry["infer_seconds"] = round(infer_s, 3)
                    lines.append(f"  infer_seconds: {infer_s:.3f}")

                    img = _maybe_resize(img, lines)
                    entry["width"], entry["height"] = img.size
                    img.save(output_path)
                    entry["ok"] = True
                    ok_count += 1
                    lines.append(f"  saved: {rel_output}")
                    print(
                        f"  ok infer={infer_s:.1f}s size={img.size[0]}x{img.size[1]}"
                    )
                except Exception as exc:
                    entry["error"] = f"{type(exc).__name__}: {exc}"
                    lines.append(f"  FAIL: {entry['error']}")
                    print(f"  FAIL: {entry['error']}")

                results.append(entry)
                lines.append("")

    summary = {
        "step": "2.1",
        "stamp": stamp,
        "total": total,
        "ok": ok_count,
        "skipped": skipped,
        "failed": total - ok_count,
        "styles": style_ids,
        "subjects": subject_ids,
        "models": model_keys,
        "results": results,
    }
    log_path = LOGS_DIR_21 / f"run_{stamp}.log"
    json_path = LOGS_DIR_21 / f"run_{stamp}.json"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"done: {ok_count}/{total} ok ({skipped} skipped)")
    print(f"outputs: {OUTPUTS_DIR_21.relative_to(REPO_ROOT).as_posix()}")
    print(f"log:     {log_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"json:    {json_path.relative_to(REPO_ROOT).as_posix()}")
    print()
    print("QA checklist (per style): same medium/mood across 3 subjects?")
    for style_id in style_ids:
        print(f"  style={style_id}")
        for subject_id in subject_ids:
            for model_key in model_keys:
                name = output_filename(style_id, subject_id, model_key)
                path = OUTPUTS_DIR_21 / name
                mark = "ok" if path.is_file() else "MISSING"
                print(f"    [{mark}] {name}")

    return 0 if ok_count == total else 1


# %%
def run_step22(
    detail_levels: Iterable[str] | None = None,
    models: Iterable[str] | None = None,
    seeds: Iterable[int] | None = None,
    *,
    skip_existing: bool = False,
) -> int:
    """Seed-grid style stability on storybook_gouache; CSV + PNGs under step22/."""
    detail_ids = _as_list(detail_levels, DETAIL_IDS)
    model_keys = _as_list(models, MODEL_KEYS)
    seed_list = _as_seed_list(seeds)
    style_id = STEP22_STYLE_ID

    for did in detail_ids:
        if did not in DETAIL_IDS:
            raise KeyError(f"unknown detail_id {did!r}; expected one of {DETAIL_IDS}")
    for mk in model_keys:
        if mk not in MODEL_KEYS:
            raise KeyError(f"unknown model {mk!r}; expected one of {MODEL_KEYS}")

    OUTPUTS_DIR_22.mkdir(parents=True, exist_ok=True)
    LOGS_DIR_22.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    run_csv = RUN_ROOT_22 / f"goal_log_step22_{stamp}.csv"
    per_model = len(detail_ids) * len(seed_list)

    styles_path = RUN_ROOT_22 / "styles.json"
    styles_path.write_text(
        json.dumps(freeze_config_step22(), indent=2) + "\n", encoding="utf-8"
    )

    total = len(detail_ids) * len(model_keys) * len(seed_list)
    results: list[dict] = []
    csv_rows: list[dict] = []
    lines: list[str] = [
        "=== ComicEngine Phase 2 Step 2.2 — seed-grid style stability ===",
        f"utc:        {stamp}",
        f"run_id:     {stamp}",
        f"style:      {style_id}",
        f"subject:    betrayal_aftermath (1)",
        f"details:    {detail_ids}",
        f"models:     {model_keys}",
        f"seeds:      {seed_list}",
        f"size:       {IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        f"matrix:     {total} images ({per_model}/model = "
        f"{len(seed_list)} seeds × 1 subject × {len(detail_ids)} details)",
        f"skip_existing: {skip_existing}",
        f"styles_json:{styles_path.relative_to(REPO_ROOT).as_posix()}",
        f"csv_master: {CSV_PATH_22.relative_to(REPO_ROOT).as_posix()}",
        f"csv_run:    {run_csv.relative_to(REPO_ROOT).as_posix()}",
        "",
    ]

    print(
        f"Step 2.2 seed-grid: {style_id} × 1 subject × {len(detail_ids)} details × "
        f"{len(seed_list)} seeds × {len(model_keys)} models = {total} "
        f"({per_model}/model)"
        + (" (skip existing)" if skip_existing else "")
    )

    ok_count = 0
    skipped = 0
    idx = 0
    # Per-model flag: if seed kwarg is rejected, stop passing seed for that model.
    seed_fallback: dict[str, bool] = {mk: False for mk in model_keys}

    for detail_id in detail_ids:
        prompt = build_prompt_step22(detail_id, style_id)
        detail_rank = DETAIL_RANKS[detail_id]
        for model_key in model_keys:
            seed_supported = model_supports_seed(model_key) and not seed_fallback[model_key]
            model_id = MODELS[model_key]["model_id"]
            for seed in seed_list:
                idx += 1
                filename = output_filename_step22(detail_id, model_key, seed, style_id)
                output_path = OUTPUTS_DIR_22 / filename
                rel_output = output_path.relative_to(REPO_ROOT).as_posix()

                entry: dict = {
                    "run_id": stamp,
                    "stamp": stamp,
                    "logged_at": datetime.now(timezone.utc).isoformat(),
                    "style_id": style_id,
                    "detail_id": detail_id,
                    "detail_rank": detail_rank,
                    "model_key": model_key,
                    "model_id": model_id,
                    "seed": seed,
                    "seed_supported": seed_supported,
                    "prompt": prompt,
                    "output_path": rel_output,
                    "width": None,
                    "height": None,
                    "infer_seconds": None,
                    "ok": False,
                    "skipped": False,
                    "error": None,
                    "style_pass": "",
                    "notes": "",
                }
                header = f"[{idx}/{total}] {filename}"
                print(f"{header} ...")
                lines.append(header)

                if skip_existing and output_path.is_file():
                    entry["ok"] = True
                    entry["skipped"] = True
                    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
                    skipped += 1
                    ok_count += 1
                    with Image.open(output_path) as existing:
                        entry["width"], entry["height"] = existing.size
                    lines.append(f"  skipped existing: {rel_output}")
                    print(f"  skipped existing")
                    results.append(entry)
                    csv_rows.append(entry)
                    _write_csv_22(csv_rows, run_csv=run_csv)
                    lines.append("")
                    continue

                try:
                    t0 = time.perf_counter()
                    use_seed = seed if seed_supported else None
                    try:
                        img = _generate(prompt, model_key, seed=use_seed)
                    except Exception as seed_exc:
                        # If seed kwarg is rejected, retry once without seed and
                        # disable seeds for the rest of this model's run.
                        err_text = f"{type(seed_exc).__name__}: {seed_exc}".lower()
                        if (
                            use_seed is not None
                            and "seed" in err_text
                            and not seed_fallback[model_key]
                        ):
                            seed_fallback[model_key] = True
                            seed_supported = False
                            entry["seed_supported"] = False
                            entry["notes"] = (
                                f"seed rejected; retry without seed ({type(seed_exc).__name__})"
                            )
                            lines.append(f"  seed rejected, retrying without: {seed_exc}")
                            print(f"  seed rejected, retrying without")
                            img = _generate(prompt, model_key, seed=None)
                        else:
                            raise
                    infer_s = time.perf_counter() - t0
                    entry["infer_seconds"] = round(infer_s, 3)
                    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
                    lines.append(f"  infer_seconds: {infer_s:.3f}")
                    lines.append(f"  seed: {seed} supported={entry['seed_supported']}")

                    img = _maybe_resize(img, lines)
                    entry["width"], entry["height"] = img.size
                    img.save(output_path)
                    entry["ok"] = True
                    ok_count += 1
                    lines.append(f"  saved: {rel_output}")
                    print(
                        f"  ok infer={infer_s:.1f}s size={img.size[0]}x{img.size[1]} "
                        f"seed={seed} supported={entry['seed_supported']}"
                    )
                except Exception as exc:
                    entry["error"] = f"{type(exc).__name__}: {exc}"
                    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
                    lines.append(f"  FAIL: {entry['error']}")
                    print(f"  FAIL: {entry['error']}")

                results.append(entry)
                csv_rows.append(entry)
                _write_csv_22(csv_rows, run_csv=run_csv)
                lines.append("")

    summary = {
        "step": "2.2",
        "run_id": stamp,
        "stamp": stamp,
        "style_id": style_id,
        "total": total,
        "ok": ok_count,
        "skipped": skipped,
        "failed": total - ok_count,
        "detail_levels": detail_ids,
        "models": model_keys,
        "seeds": seed_list,
        "seed_fallback": seed_fallback,
        "csv_path": CSV_PATH_22.relative_to(REPO_ROOT).as_posix(),
        "csv_run_path": run_csv.relative_to(REPO_ROOT).as_posix(),
        "results": results,
    }
    log_path = LOGS_DIR_22 / f"run_{stamp}.log"
    json_path = LOGS_DIR_22 / f"run_{stamp}.json"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_csv_22(csv_rows, run_csv=run_csv)

    print()
    print(f"done: {ok_count}/{total} ok ({skipped} skipped)")
    print(f"outputs: {OUTPUTS_DIR_22.relative_to(REPO_ROOT).as_posix()}")
    print(f"csv:     {CSV_PATH_22.relative_to(REPO_ROOT).as_posix()}")
    print(f"csv_run: {run_csv.relative_to(REPO_ROOT).as_posix()}")
    print(f"log:     {log_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"json:    {json_path.relative_to(REPO_ROOT).as_posix()}")
    print()
    print("QA checklist (per detail × model): ≥8/9 same style medium/mood?")
    for detail_id in detail_ids:
        for model_key in model_keys:
            print(f"  detail={detail_id} model={model_key}")
            for seed in seed_list:
                name = output_filename_step22(detail_id, model_key, seed, style_id)
                path = OUTPUTS_DIR_22 / name
                mark = "ok" if path.is_file() else "MISSING"
                print(f"    [{mark}] {name}")

    return 0 if ok_count == total else 1


# %%
def main() -> int:
    return run_step22()


if __name__ == "__main__":
    raise SystemExit(main())

# %%
