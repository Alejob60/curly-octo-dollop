@echo off
cd /d d:\MISYBOT_2026\Orbital-prime\orbital-prime-govdocs-engine
.venv312\Scripts\python.exe -m celery -A app.tasks.pqrsd_tasks worker --loglevel=info
