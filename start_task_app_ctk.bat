@echo off
cd /d "%~dp0"
python task_app_ctk.py
if errorlevel 1 pause
