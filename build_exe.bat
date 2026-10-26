@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm --clean --windowed --onedir --name TaskManager --collect-all customtkinter --collect-all tkcalendar --collect-all babel task_app_ctk.py
pause
