@echo off
REM Run this from the project folder in Windows Command Prompt.
REM It installs required packages if needed, then starts the FastAPI server.
python -m pip install fastapi uvicorn
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8002
