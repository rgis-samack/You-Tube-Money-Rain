@echo off
chcp 65001 >nul
title Monitoramento LIVE - Twitch e Kick Pro
cd /d "%~dp0"

echo =====================================================================
echo    [1/3] MONITORAMENTO LIVE - TWITCH E KICK PRO
echo    Design Microsoft Fluent 2 - Clipes Sem Censura - Download em Lote
echo =====================================================================
echo.

:: Varredura rapida do ambiente
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [INFO] Configurando o ambiente virtual pela primeira vez...
    call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
) else (
    "%~dp0.venv\Scripts\python.exe" -c "import fastapi, uvicorn, yt_dlp" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Detectadas bibliotecas pendentes. Atualizando...
        call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
    )
)

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

echo [INFO] Inicializando servidor FastAPI e interface nativa...
cd /d "%~dp0Monitoramento LIVE"
"%PYTHON_EXE%" "iniciar_servidor.py"

pause
