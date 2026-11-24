@echo off
chcp 65001 >nul
title Cortes IA Pro - Painel Central
cd /d "%~dp0"

:MENU
cls
echo =====================================================================
echo       CORTES IA PRO - PAINEL CENTRAL E INICIALIZADOR
echo       Design Microsoft Fluent 2 - Whisper IA - Aceleracao GPU
echo =====================================================================
echo.
echo   Realizando varredura rapida de integridade do ambiente...

if not exist "%~dp0.venv\Scripts\python.exe" (
    echo.
    echo   [!] Primeira execucao detectada.
    echo   Iniciando instalacao e configuracao automatica com 1 clique...
    call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
) else (
    "%~dp0.venv\Scripts\python.exe" -c "import fastapi, customtkinter, faster_whisper, cv2" >nul 2>&1
    if errorlevel 1 (
        echo.
        echo   [!] Bibliotecas ausentes detectadas. Atualizando ambiente...
        call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
    )
)

echo   [OK] Ambiente verificado com sucesso.
echo.
echo =====================================================================
echo   ESCOLHA O MODULO QUE DESEJA INICIAR:
echo =====================================================================
echo   [1] Monitoramento LIVE (Twitch e Kick - Clipes e Downloads)
echo   [2] Studio de Enquadramento 9:16 (Crop Interativo no Navegador)
echo   [3] Interface Grafica Desktop (CustomTkinter - Gerador Manual)
echo   [4] Minerar Video ou Live (Streamlink / yt-dlp + Faster-Whisper)
echo   [5] Fazer Nova Varredura e Reinstalar Dependencias
echo   [0] Sair
echo =====================================================================
echo.

set "OPCAO=3"
set /p "OPCAO=Digite o numero da opcao desejada [padrao 3]: "

if "%OPCAO%"=="1" (
    start "" "%~dp01_MONITORAMENTO_LIVE.bat"
    exit /b 0
)
if "%OPCAO%"=="2" (
    call "%~dp02_STUDIO_CROP_CAPTURA.bat"
    goto MENU
)
if "%OPCAO%"=="3" (
    call "%~dp0INICIAR_INTERFACE_GRAFICA.bat"
    exit /b 0
)
if "%OPCAO%"=="4" (
    start "" "%~dp03_DOWNLOAD_E_MINERADOR.bat"
    exit /b 0
)
if "%OPCAO%"=="5" (
    call "%~dp0INSTALAR_DEPENDENCIAS.bat"
    goto MENU
)
if "%OPCAO%"=="0" (
    exit /b 0
)

echo Opcao invalida. Tente novamente.
timeout /t 2 >nul
goto MENU
