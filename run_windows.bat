@echo off
setlocal

if "%~1"=="" (
  echo Usage: run_windows.bat search words
  echo Example: run_windows.bat ban nha binh chanh
  exit /b 1
)

if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -e .

REM Default provider is now the real YouTube website through Playwright.
REM It tries installed Google Chrome first, then Microsoft Edge.
REM Add --headed manually if YouTube shows an anti-bot/challenge page.
python -m ytb_radar --db data\radar.db scan --provider youtube --query "%*" --region VN --seed-limit 20 --depth 1 --recs 20 --delay 0.8
