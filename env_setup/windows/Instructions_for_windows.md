# ComicEngine

Windows GPU env verification for RTX 50-series (sm_120 / capability `(12, 0)`).

## Setup

```powershell
conda activate myenv
pip install -r env_setup/windows/requirements.txt
```

## Verify

```powershell
python env_setup/windows/verify.py
```

Expects CUDA capability `(12, 0)` and no `sm_120` warning.
