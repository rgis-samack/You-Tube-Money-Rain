@echo off
chcp 65001 >nul
title Minerador Automatico de Cortes Virais
cd /d "%~dp0"

:: Varredura rapida do ambiente
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [INFO] Configurando o ambiente virtual pela primeira vez...
    call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
) else (
    "%~dp0.venv\Scripts\python.exe" -c "import faster_whisper, cv2, yt_dlp" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Detectadas bibliotecas pendentes. Atualizando...
        call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
    )
)

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "ARQUIVO=%~1"

if "%ARQUIVO%"=="" (
    echo =====================================================================
    echo    [3/3] MINERADOR AUTOMATICO DE CORTES VIRAIS (STREAMLINK + IA)
    echo    Whisper IA + VAD Silero + Aceleracao GPU AMD AMF / NVENC
    echo =====================================================================
    echo.
    echo [Dica] Voce pode arrastar qualquer arquivo de video (.mp4, .mkv, .ts)
    echo        diretamente para cima deste arquivo .bat para processa-lo.
    echo.
    "%PYTHON_EXE%" -u "%~dp0minerar_live.py"
    pause
    exit /b
)

if not exist "%ARQUIVO%" (
    echo [ERRO] Arquivo nao encontrado: "%ARQUIVO%"
    pause
    exit /b
)

echo =====================================================================
echo    PROCESSANDO VIDEO ARRASTADO:
echo    "%ARQUIVO%"
echo =====================================================================
echo.

"%PYTHON_EXE%" -u "%~dp0minerar_live.py" "%ARQUIVO%"

echo.
echo =====================================================================
echo    PROCESSAMENTO CONCLUIDO
echo =====================================================================
pause
