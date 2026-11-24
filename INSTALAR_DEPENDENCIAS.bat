@echo off
chcp 65001 >nul
title Instalador e Verificador Automatico - Cortes IA Pro
cd /d "%~dp0"

echo =====================================================================
echo    INSTALADOR E VERIFICADOR DE AMBIENTE - CORTES IA PRO
echo    Varredura Automatica de Dependencias, Python e FFmpeg
echo =====================================================================
echo.

:: 1. Verificacao do Python
echo [1/4] Verificando instalacao do Python no Windows...
set "SYS_PYTHON="
where.exe python >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('where.exe python 2^>nul') do (
        if not defined SYS_PYTHON set "SYS_PYTHON=%%i"
    )
)

if not defined SYS_PYTHON (
    echo.
    echo [AVISO] Python nao foi encontrado no PATH do sistema.
    echo Tentando instalar Python 3.11 via Windows Package Manager winget...
    where.exe winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        echo.
        echo [OK] Python instalado. Reinicie este script para carregar o PATH.
        pause
        exit /b 0
    ) else (
        echo [ERRO CRITICO] Python nao encontrado e winget indisponivel.
        echo Por favor instale o Python 3.10 ou superior manualmente:
        echo https://www.python.org/downloads/
        echo Marque a opcao "Add Python to PATH" durante a instalacao.
        pause
        exit /b 1
    )
)
echo      [OK] Python detectado: %SYS_PYTHON%

:: 2. Verificacao do FFmpeg
echo [2/4] Verificando FFmpeg para renderizacao e audio...
where.exe ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] FFmpeg nao encontrado no PATH do Windows.
    echo Tentando instalar FFmpeg via winget automaticamente...
    where.exe winget >nul 2>&1
    if %errorlevel% equ 0 (
        winget install Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
        echo      [OK] FFmpeg instalado via winget.
    ) else (
        echo [AVISO] Baixe o FFmpeg em: https://ffmpeg.org/download.html
    )
) else (
    echo      [OK] FFmpeg pronto no PATH.
)

:: 3. Criacao do Ambiente Virtual .venv
echo [3/4] Verificando Ambiente Virtual .venv...
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo      Criando ambiente virtual isolado em "%~dp0.venv"...
    "%SYS_PYTHON%" -m venv "%~dp0.venv"
    if %errorlevel% neq 0 (
        echo [ERRO] Falha ao criar ambiente virtual com "%SYS_PYTHON%".
        pause
        exit /b 1
    )
    echo      [OK] Ambiente virtual criado com sucesso.
) else (
    echo      [OK] Ambiente virtual .venv ja existe.
)

set "VENV_PY=%~dp0.venv\Scripts\python.exe"

:: 4. Varredura e Instalacao de Bibliotecas
echo [4/4] Verificando integridade das bibliotecas de IA, Web e GUI...
"%VENV_PY%" -c "import fastapi, uvicorn, faster_whisper, cv2, customtkinter, yt_dlp" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo      [INSTALANDO] Bibliotecas ausentes detectadas.
    echo      Atualizando pip e instalando pacotes do requirements.txt...
    echo      Aguarde alguns minutos durante a primeira instalacao...
    echo.
    "%VENV_PY%" -m pip install --upgrade pip
    "%VENV_PY%" -m pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo [AVISO] Ocorreram alertas durante o pip install.
    )
    echo.
    echo      [OK] Todas as dependencias foram instaladas com sucesso.
) else (
    echo      [OK] Todas as bibliotecas estao 100%% atualizadas e funcionais.
)

echo.
echo =====================================================================
echo    SISTEMA 100%% PRONTO E OPERACIONAL
echo =====================================================================
if not "%~1"=="--auto" (
    echo.
    echo Pressione qualquer tecla para continuar...
    pause >nul
)
exit /b 0
