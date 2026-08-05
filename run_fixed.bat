@echo off
REM Run this from the project folder in Windows Command Prompt.
REM It installs required packages if needed, then starts the FastAPI server.
"C:\Users\USER\AppData\Local\Programs\Python\Python313\python.exe" -m pip install fastapi uvicorn sqlmodel passlib[bcrypt] pyjwt
"C:\Users\USER\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
