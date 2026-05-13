@echo off
cd /d d:\MISYBOT_2026\Orbital-prime\orbital-prime-govdocs-engine
.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
