@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Seguimiento Minero
where python >nul 2>nul || (echo No se encontro Python. Instala Python 3.11 o superior desde python.org marcando "Add Python to PATH". & pause & exit /b 1)
if not exist .venv (
  echo Primera vez: instalando componentes, tarda unos minutos...
  python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\pip install -r requirements.txt
)
.venv\Scripts\streamlit run app.py
pause
