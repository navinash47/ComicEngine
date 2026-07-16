# %%
"""Phase 2 Step 2.1 — style string bake-off (via ApiManager).

Isolated from Phase 1: do not run mac_dev.py from here; outputs go to
runs/phase2/step21/.
"""

from __future__ import annotations

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
    IMAGE_ASPECT_RATIO,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    MODEL_KEYS,
    MODELS,
    STYLE_IDS,
    SUBJECT_IDS,
    build_prompt,
    freeze_config,
    output_filename,
)

RUN_ROOT = REPO_ROOT / "runs" / "phase2" / "step21"
OUTPUTS_DIR = RUN_ROOT / "outputs"
LOGS_DIR = RUN_ROOT / "logs"

# %%
api = ApiManager()


# %%
def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _as_list(values: Iterable[str] | None, default: tuple[str, ...]) -> list[str]:
    if values is None:
        return list(default)
    return list(values)


def _generate(prompt: str, model_key: str) -> Image.Image:
    spec = MODELS[model_key]
    backend = spec["backend"]
    if backend == "hf":
        return api.hf_image(
            prompt,
            provider=spec["provider"],
            model=spec["model_id"],
            width=IMAGE_WIDTH,
            height=IMAGE_HEIGHT,
        )
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

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()

    styles_path = RUN_ROOT / "styles.json"
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
                output_path = OUTPUTS_DIR / filename
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
    log_path = LOGS_DIR / f"run_{stamp}.log"
    json_path = LOGS_DIR / f"run_{stamp}.json"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"done: {ok_count}/{total} ok ({skipped} skipped)")
    print(f"outputs: {OUTPUTS_DIR.relative_to(REPO_ROOT).as_posix()}")
    print(f"log:     {log_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"json:    {json_path.relative_to(REPO_ROOT).as_posix()}")
    print()
    print("QA checklist (per style): same medium/mood across 3 subjects?")
    for style_id in style_ids:
        print(f"  style={style_id}")
        for subject_id in subject_ids:
            for model_key in model_keys:
                name = output_filename(style_id, subject_id, model_key)
                path = OUTPUTS_DIR / name
                mark = "ok" if path.is_file() else "MISSING"
                print(f"    [{mark}] {name}")

    return 0 if ok_count == total else 1


# %%
def main() -> int:
    return run_step21()


if __name__ == "__main__":
    raise SystemExit(main())

# %%
