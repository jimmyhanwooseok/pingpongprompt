@echo off

REM 백엔드 실행
cd backend\app
if not exist venv (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r ..\requirements.txt
start cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug"

REM 프론트엔드 실행
cd ..\..\frontend
if not exist node_modules (
    call npm install
)
start cmd /k "npm start" 