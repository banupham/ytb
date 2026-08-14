@echo off
setlocal

if not exist .venv (
  py -m venv .venv
)
call .venv\Scripts\activate
python -m pip install -e .

python auto_radar.py

if errorlevel 1 (
  echo.
  echo AUTO RADAR FAILED
  exit /b 1
)

echo.
echo AUTO RADAR DONE
echo Open: reports\latest_summary.txt
