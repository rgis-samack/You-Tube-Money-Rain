@echo off
chcp 65001 >nul
title Monitoramento LIVE - Twitch e Kick Pro
cd /d "%~dp0"

echo =====================================================================
echo    INICIANDO PLATAFORMA DE MONITORAMENTO LIVE (TWITCH E KICK)
echo    Design Microsoft Fluent 2 - Clipes Sem Censura + Download em Lote
echo =====================================================================

:: Utiliza preferencialmente o ambiente virtual (.venv) com todas as bibliotecas de IA e aceleracao GPU AMF
set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=C:\DEV\You Tube Money Rain\.venv\Scripts\python.exe"
)
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [INFO] Python: "%PYTHON_EXE%"
echo [INFO] Inicializando servidor e interface desktop...
"%PYTHON_EXE%" "%~dp0iniciar_servidor.py"

pause
