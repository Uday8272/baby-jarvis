@echo off
title Jarvis 24/7 Voice Daemon
echo Starting Jarvis Voice Daemon...
call .venv\Scripts\activate.bat
python -m voice.daemon 
pause
