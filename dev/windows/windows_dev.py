# %%
"""Phase 1 — local FLUX.1-schnell single-image smoke test (Windows GPU)."""

from __future__ import annotations

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
    FLUX_GUIDANCE,
    FLUX_HEIGHT,
    FLUX_MAX_SEQ_LEN,
    FLUX_SEED,
    FLUX_STEPS,
    FLUX_WIDTH,
    MODEL_FLUX,
    OUTPUT_FILENAME,
    PROMPT,
    TARGET_INFER_SECONDS,
    TARGET_VRAM_GB,
)

RUN_ROOT = REPO_ROOT / "runs" / "phase1" / "flux_schnell"
OUTPUTS_DIR = RUN_ROOT / "outputs"
LOGS_DIR = RUN_ROOT / "logs"


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _write_logs(stamp: str, metrics: dict, lines: list[str]) -> tuple[Path, Path]:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"run_{stamp}.log"
    json_path = LOGS_DIR / f"run_{stamp}.json"
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return log_path, json_path


def _load_hf_token() -> str | None:
    env_path = REPO_ROOT / ".env"
    if env_path.is_file():
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path)
        except ImportError:
            pass
    token = (
        (os.getenv("HF_TOKEN") or "").strip()
        or (os.getenv("HUGGING_FACE_HUB_TOKEN") or "").strip()
    )
    return token or None


def main() -> int:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()
    output_path = OUTPUTS_DIR / OUTPUT_FILENAME
    rel_output = output_path.relative_to(REPO_ROOT).as_posix()

    lines: list[str] = [
        "=== ComicEngine Phase 1 — FLUX.1-schnell ===",
        f"utc:        {stamp}",
        f"model:      {MODEL_FLUX}",
        f"size:       {FLUX_WIDTH}x{FLUX_HEIGHT}",
        f"steps:      {FLUX_STEPS}",
        f"seed:       {FLUX_SEED}",
        f"prompt:     {PROMPT}",
        "",
    ]

    metrics: dict = {
        "model_id": MODEL_FLUX,
        "prompt": PROMPT,
        "width": FLUX_WIDTH,
        "height": FLUX_HEIGHT,
        "load_seconds": None,
        "infer_seconds": None,
        "peak_vram_gb": None,
        "device_name": None,
        "seed": FLUX_SEED,
        "ok": False,
        "error": None,
        "output_path": rel_output,
        "targets": {
            "vram_gb": TARGET_VRAM_GB,
            "infer_seconds": TARGET_INFER_SECONDS,
        },
        "vram_pass": None,
        "infer_pass": None,
    }

    try:
        import torch
        from diffusers import FluxPipeline
    except ImportError as exc:
        metrics["error"] = f"import failed: {exc}"
        lines.append(f"FAIL: {metrics['error']}")
        _write_logs(stamp, metrics, lines)
        print(lines[-1])
        return 1

    if not torch.cuda.is_available():
        metrics["error"] = "CUDA is not available"
        lines.append(f"FAIL: {metrics['error']}")
        _write_logs(stamp, metrics, lines)
        print(lines[-1])
        return 1

    device_name = torch.cuda.get_device_name(0)
    metrics["device_name"] = device_name
    lines.append(f"device:     {device_name}")

    hf_token = _load_hf_token()
    if hf_token:
        lines.append("hf_token:  set (from env)")
    else:
        lines.append("hf_token:  not set (may fail on gated HF repo)")

    print(f"Loading {MODEL_FLUX} (bfloat16 + sequential cpu offload)...")

    try:
        # Prefer math/eager attention on Blackwell (sm_120); fused SDP can hard-crash.
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        torch.backends.cuda.enable_math_sdp(True)

        t_load = time.perf_counter()
        pipe = FluxPipeline.from_pretrained(
            MODEL_FLUX,
            torch_dtype=torch.bfloat16,
            token=hf_token,
        )
        try:
            pipe.transformer.set_attention_backend("_native_math")
            lines.append("attn_backend: _native_math")
        except Exception as attn_exc:
            lines.append(f"attn_backend: default ({type(attn_exc).__name__}: {attn_exc})")
        # Sequential offload: move one submodule at a time (avoids AV/OOM when
        # dumping the full ~12GB transformer onto a 16GB card in one .to(cuda)).
        pipe.enable_sequential_cpu_offload()
        lines.append("offload: sequential_cpu_offload")
        load_s = time.perf_counter() - t_load
        metrics["load_seconds"] = round(load_s, 3)
        lines.append(f"load_seconds: {load_s:.3f}")
        print(f"Pipeline loaded in {load_s:.2f}s")

        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        image = pipe(
            prompt=PROMPT,
            height=FLUX_HEIGHT,
            width=FLUX_WIDTH,
            num_inference_steps=FLUX_STEPS,
            guidance_scale=FLUX_GUIDANCE,
            max_sequence_length=FLUX_MAX_SEQ_LEN,
            generator=torch.Generator("cpu").manual_seed(FLUX_SEED),
        ).images[0]
        infer_s = time.perf_counter() - t0
        peak_gb = torch.cuda.max_memory_allocated() / (1024**3)

        metrics["infer_seconds"] = round(infer_s, 3)
        metrics["peak_vram_gb"] = round(peak_gb, 3)
        vram_pass = peak_gb < TARGET_VRAM_GB
        infer_pass = infer_s < TARGET_INFER_SECONDS
        metrics["vram_pass"] = vram_pass
        metrics["infer_pass"] = infer_pass

        image.save(output_path)
        metrics["ok"] = True

        vram_tag = "PASS" if vram_pass else "WARN"
        infer_tag = "PASS" if infer_pass else "WARN"
        lines.extend(
            [
                f"infer_seconds: {infer_s:.3f}  [{infer_tag} target < {TARGET_INFER_SECONDS}s]",
                f"peak_vram_gb:  {peak_gb:.3f}  [{vram_tag} target < {TARGET_VRAM_GB}GB]",
                f"saved:         {rel_output}",
                "ok: true",
            ]
        )
        summary = (
            f"FLUX schnell | infer={infer_s:.1f}s | peak_vram={peak_gb:.1f}GB | "
            f"saved={rel_output}"
        )
        print(summary)
    except Exception as exc:
        metrics["error"] = f"{type(exc).__name__}: {exc}"
        hint = (
            "Accept the gate at https://huggingface.co/black-forest-labs/FLUX.1-schnell "
            "then set HF_TOKEN in .env (Read token) or run: hf auth login"
        )
        lines.append(f"FAIL: {metrics['error']}")
        lines.append(f"hint: {hint}")
        print(lines[-2])
        print(f"hint: {hint}")
        log_path, json_path = _write_logs(stamp, metrics, lines)
        print(f"log:  {log_path.relative_to(REPO_ROOT).as_posix()}")
        print(f"json: {json_path.relative_to(REPO_ROOT).as_posix()}")
        return 1

    log_path, json_path = _write_logs(stamp, metrics, lines)
    print(f"log:  {log_path.relative_to(REPO_ROOT).as_posix()}")
    print(f"json: {json_path.relative_to(REPO_ROOT).as_posix()}")
    return 0


# %%
if __name__ == "__main__":
    raise SystemExit(main())
