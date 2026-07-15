# ComicEngine

Windows GPU env verification for RTX 50-series (sm_120 / capability `(12, 0)`).

## Setup

```powershell
conda activate myenv
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

## Verify

```powershell
python env_setup/windows/verify.py
```

Expects CUDA capability `(12, 0)` and no `sm_120` warning.
