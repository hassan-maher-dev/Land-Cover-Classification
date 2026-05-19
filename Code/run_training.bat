@echo off
cd /d "%~dp0"
call venv\Scripts\activate
python Model_Training\main.py
pause