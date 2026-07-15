"""Basic ComicEngine env verification for Windows (PyTorch + CUDA)."""

from __future__ import annotations

import sys
import warnings


def main() -> int:
    print("=== ComicEngine Windows env verify ===\n")

    try:
        import torch
    except ImportError as exc:
        print(f"FAIL: torch not installed ({exc})")
        return 1

    print(f"python:     {sys.executable}")
    print(f"torch:      {torch.__version__}")
    print(f"cuda built: {torch.version.cuda}")

    if not torch.cuda.is_available():
        print("FAIL: CUDA is not available")
        return 1

    name = torch.cuda.get_device_name(0)
    capability = torch.cuda.get_device_capability(0)
    print(f"device:     {name}")
    print(f"capability: {capability}")

    if capability != (12, 0):
        print(f"FAIL: expected capability (12, 0), got {capability}")
        return 1
    print("OK: device capability is (12, 0)")

    caught: list[warnings.WarningMessage] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        a = torch.randn(64, 64, device="cuda")
        b = torch.randn(64, 64, device="cuda")
        c = a @ b
        _ = c.sum().item()
        _ = torch.nn.functional.relu(c).mean().item()

    sm120 = [
        w
        for w in caught
        if "sm_120" in str(w.message).lower() or "sm_120" in str(w.message)
    ]
    if sm120:
        print("FAIL: sm_120 compatibility warning detected:")
        for w in sm120:
            print(f"  {w.message}")
        return 1
    print("OK: no sm_120 warning")

    print("OK: basic CUDA matmul + relu succeeded")
    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
