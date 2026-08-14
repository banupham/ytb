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

REM YTB_INVIDIOUS_BASE is optional.
REM If it is unset, ytb-radar discovers official public instances and probes them.
python -m ytb_radar --db data\radar.db scan --query "%*" --region VN --seed-limit 20 --depth 1 --recs 20
