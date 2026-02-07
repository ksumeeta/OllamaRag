@echo off
echo Starting Backend...
:: call venv\Scripts\activate
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
