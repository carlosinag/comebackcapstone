@echo off
echo Starting Ultrasound Clinic Server with WebSocket Support...
cd /d "%~dp0"
python -m uvicorn ultrasound_clinic.asgi:application --host 127.0.0.1 --port 8000 --reload
pause
