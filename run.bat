@echo off
REM Run this from the project folder in Windows Command Prompt.
REM It installs required packages into the active Python, then starts the FastAPI server.
cd /d %~dp0
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 --app-dir .
