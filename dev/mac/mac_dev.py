# %%
"""Phase 1 — Mac API smoke / interactive cells (via ApiManager)."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# %%
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.mac.api_manager import ApiManager  # noqa: E402
from dev.shared.phase1_prompt import (  # noqa: E402
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    MODEL_FLUX,
    MODEL_NANO_BANANA,
    OUTPUT_FILENAME,
    PROMPT,
)

# Default active run: fal-ai FLUX via Hugging Face InferenceClient
RUN_NAME = "flux_fal"
RUN_ROOT = REPO_ROOT / "runs" / "phase1" / RUN_NAME
OUTPUTS_DIR = RUN_ROOT / "outputs"
LOGS_DIR = RUN_ROOT / "logs"

# %%
def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _write_logs(stamp: str, metrics: dict, lines: list[str]) -> tuple[Path, Path]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"run_{stamp}.log"
    json_path = LOGS_DIR / f"run_{stamp}.json"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return log_path, json_path


# %%
api = ApiManager()

# %%
# --- Active smoke: fal-ai + FLUX.1-schnell ---
def run_fal_flux() -> int:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    output_path = OUTPUTS_DIR / OUTPUT_FILENAME
    rel_output = output_path.relative_to(REPO_ROOT).as_posix()
    provider = "fal-ai"
    model_id = MODEL_FLUX

    lines: list[str] = [
        "=== ComicEngine Phase 1 — FLUX via fal-ai ===",
        f"utc:        {stamp}",
        f"model:      {model_id}",
        f"provider:   {provider}",
        f"device:     mac-api",
        f"size:       {IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        f"prompt:     {PROMPT}",
        "",
    ]
    metrics: dict = {
        "model_id": model_id,
        "provider": provider,
        "prompt": PROMPT,
        "width": None,
        "height": None,
        "load_seconds": None,
        "infer_seconds": None,
        "peak_vram_gb": None,
        "device_name": "mac-api",
        "seed": None,
        "ok": False,
        "error": None,
        "output_path": rel_output,
    }

    print(f"Calling {model_id} via {provider}...")
    try:
        t0 = time.perf_counter()
        img = api.hf_image(
            PROMPT,
            provider=provider,
            model=model_id,
            width=IMAGE_WIDTH,
            height=IMAGE_HEIGHT,
        )
        infer_s = time.perf_counter() - t0
        metrics["infer_seconds"] = round(infer_s, 3)
        lines.append(f"infer_seconds: {infer_s:.3f}")

        if img.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
            from PIL import Image

            lines.append(f"api_size:     {img.size[0]}x{img.size[1]} -> resize")
            img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)

        metrics["width"], metrics["height"] = img.size
        img.save(output_path)
        metrics["ok"] = True
        lines.extend(
            [
                f"size:          {metrics['width']}x{metrics['height']}",
                f"saved:         {rel_output}",
                "ok: true",
            ]
        )
    except Exception as exc:
        metrics["error"] = f"{type(exc).__name__}: {exc}"
        lines.append(f"FAIL: {metrics['error']}")
        _write_logs(stamp, metrics, lines)
        print(lines[-1])
        return 1

    log_path, json_path = _write_logs(stamp, metrics, lines)
    print(
        f"FLUX fal-ai | infer={metrics['infer_seconds']:.1f}s | "
        f"peak_vram=n/a | saved={rel_output}"
    )
    print(f"log:  {log_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"json: {json_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


# %%
# --- Examples (uncomment to run) ---

# img = api.hf_image(PROMPT, provider="together", model=MODEL_FLUX)
# img = api.hf_image(PROMPT, provider="replicate", model=MODEL_FLUX)
# img = api.hf_image(PROMPT, provider="nscale", model=MODEL_FLUX)
# img = api.hf_image(PROMPT, provider="wavespeed", model=MODEL_FLUX)
# img = api.hf_image(PROMPT, provider="hf-inference", model=MODEL_FLUX)

# img = api.google_image(PROMPT, model=MODEL_NANO_BANANA)
# if img.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
#     from PIL import Image
#     img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)

# text = api.google_chat("hello", model="gemini-3.5-flash")
# text = api.openai_chat("hello", model="gpt-4o-mini")
# text = api.anthropic_chat("hello", model="claude-haiku-4-5-20251001")
# img = api.openai_image("Astronaut riding a horse", model="dall-e-3")

# %%
def main() -> int:
    return run_fal_flux()


if __name__ == "__main__":
    raise SystemExit(main())

# %%
