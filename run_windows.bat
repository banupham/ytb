@echo off
setlocal

if "%~1"=="" (
  echo Usage: run_windows.bat search words
  echo Example: run_windows.bat minecraft sinh ton
  exit /b 1
)

if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -e .

REM Research default: real YouTube, isolated watch context per seed, direct Watch Next only.
REM depth=0 avoids recursive topic drift; use explicit commands for deeper experiments.
python -m ytb_radar --db data\radar.db scan --provider youtube --query "%*" --region VN --seed-limit 20 --depth 0 --recs 20 --delay 0.8
