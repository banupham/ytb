@echo off
setlocal
if "%YTB_INVIDIOUS_BASE%"=="" (
  echo Set YTB_INVIDIOUS_BASE first.
  echo Example:
  echo   set YTB_INVIDIOUS_BASE=https://YOUR-INVIDIOUS-INSTANCE
  exit /b 1
)

if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -e .
python -m ytb_radar --db data\radar.db scan --query "%*" --region VN --seed-limit 20 --depth 1 --recs 20
