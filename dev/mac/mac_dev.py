# %%
"""Phase 1 — Nano Banana (gemini-3.1-flash-image) single-image smoke test (Mac API)."""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# %%
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dev.shared.phase1_prompt import (  # noqa: E402
    IMAGE_ASPECT_RATIO,
    IMAGE_HEIGHT,
    IMAGE_WIDTH,
    MODEL_NANO_BANANA,
    OUTPUT_FILENAME,
    PROMPT,
)

RUN_ROOT = REPO_ROOT / "runs" / "phase1" / "nano_banana"
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


def _image_bytes_from_interactions(client, prompt: str) -> bytes:
    """Preferred path: Interactions API (current Nano Banana docs)."""
    # Interactions uses its own GenerationConfig (dict), not GenerateContentConfig.
    interaction = client.interactions.create(
        model=MODEL_NANO_BANANA,
        input=prompt,
        response_format={
            "type": "image",
            "aspect_ratio": IMAGE_ASPECT_RATIO,
        },
    )
    out = getattr(interaction, "output_image", None)
    if out is None:
        raise RuntimeError("interactions response missing output_image")
    data = getattr(out, "data", None)
    if not data:
        raise RuntimeError("interactions output_image has empty data")
    if isinstance(data, bytes):
        return data
    return base64.b64decode(data)


def _image_bytes_from_generate_content(client, prompt: str) -> bytes:
    """Fallback for older google-genai without client.interactions."""
    from google.genai import types

    response = client.models.generate_content(
        model=MODEL_NANO_BANANA,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=IMAGE_ASPECT_RATIO),
        ),
    )
    parts = []
    if getattr(response, "candidates", None):
        content = response.candidates[0].content
        parts = getattr(content, "parts", None) or []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None and getattr(inline, "data", None):
            data = inline.data
            if isinstance(data, bytes):
                return data
            return base64.b64decode(data)
    raise RuntimeError("generate_content response had no inline image data")


def _generate_image_bytes(client, prompt: str) -> bytes:
    # Prefer interactions; fall back if API missing or request shape rejected.
    try:
        return _image_bytes_from_interactions(client, prompt)
    except Exception as exc:
        # AttributeError: no interactions; ValidationError/TypeError: bad kwargs.
        if type(exc).__name__ not in ("AttributeError", "TypeError", "ValidationError"):
            raise
        return _image_bytes_from_generate_content(client, prompt)

# %%
def main() -> int:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    output_path = OUTPUTS_DIR / OUTPUT_FILENAME
    rel_output = output_path.relative_to(REPO_ROOT).as_posix()

    lines: list[str] = [
        "=== ComicEngine Phase 1 — Nano Banana ===",
        f"utc:        {stamp}",
        f"model:      {MODEL_NANO_BANANA}",
        f"device:     mac-api",
        f"size:       {IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        f"aspect:     {IMAGE_ASPECT_RATIO}",
        f"prompt:     {PROMPT}",
        "",
    ]

    metrics: dict = {
        "model_id": MODEL_NANO_BANANA,
        "prompt": PROMPT,
        "width": IMAGE_WIDTH,
        "height": IMAGE_HEIGHT,
        "load_seconds": None,
        "infer_seconds": None,
        "peak_vram_gb": None,
        "device_name": "mac-api",
        "seed": None,
        "ok": False,
        "error": None,
        "output_path": rel_output,
    }

    try:
        from dotenv import load_dotenv
        from google import genai
        from PIL import Image
        import io
    except ImportError as exc:
        metrics["error"] = f"import failed: {exc}"
        lines.append(f"FAIL: {metrics['error']}")
        _write_logs(stamp, metrics, lines)
        print(lines[-1])
        return 1

    env_path = REPO_ROOT / ".env"
    if not env_path.is_file():
        metrics["error"] = f"missing {env_path}"
        lines.append(f"FAIL: {metrics['error']}")
        _write_logs(stamp, metrics, lines)
        print(lines[-1])
        return 1

    load_dotenv(env_path)
    api_key = (os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        metrics["error"] = "GOOGLE_API_KEY is missing or empty"
        lines.append(f"FAIL: {metrics['error']}")
        _write_logs(stamp, metrics, lines)
        print(lines[-1])
        return 1

    t_load = time.perf_counter()
    client = genai.Client(api_key=api_key)
    load_s = time.perf_counter() - t_load
    metrics["load_seconds"] = round(load_s, 3)
    lines.append(f"load_seconds: {load_s:.3f}")

    print(f"Calling {MODEL_NANO_BANANA}...")
    try:
        t0 = time.perf_counter()
        raw = _generate_image_bytes(client, PROMPT)
        infer_s = time.perf_counter() - t0
        metrics["infer_seconds"] = round(infer_s, 3)

        # Match shared panel size (API returns its own resolution/aspect).
        img = Image.open(io.BytesIO(raw))
        if img.size != (IMAGE_WIDTH, IMAGE_HEIGHT):
            lines.append(f"api_size:     {img.size[0]}x{img.size[1]} -> resize")
            img = img.resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
        metrics["width"], metrics["height"] = img.size
        # Re-encode as PNG for a consistent extension.
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        output_path.write_bytes(buf.getvalue())

        metrics["ok"] = True
        lines.extend(
            [
                f"infer_seconds: {infer_s:.3f}",
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
    summary = (
        f"Nano Banana | infer={metrics['infer_seconds']:.1f}s | "
        f"peak_vram=n/a | saved={rel_output}"
    )
    print(summary)
    print(f"log:  {log_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"json: {json_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


# %%
if __name__ == "__main__":
    raise SystemExit(main())

# %%
