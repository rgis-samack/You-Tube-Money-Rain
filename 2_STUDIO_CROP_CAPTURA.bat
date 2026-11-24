@echo off
chcp 65001 >nul
title Cortes IA Pro - Studio de Crop e Enquadramento Interativo
cd /d "%~dp0"

echo =====================================================================
echo    [2/3] STUDIO DE CROP E ENQUADRAMENTO INTERATIVO 9:16
echo    Crop de Webcam e Gameplay - Preview Real-Time - GPU AMF / NVENC
echo =====================================================================
echo.

:: Varredura rapida do ambiente
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo [INFO] Configurando o ambiente virtual pela primeira vez...
    call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
) else (
    "%~dp0.venv\Scripts\python.exe" -c "import fastapi, uvicorn, cv2" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Detectadas bibliotecas pendentes. Atualizando...
        call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
    )
)

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

echo [INFO] Verificando servidor local em http://127.0.0.1:8765...
curl -s -m 2 http://127.0.0.1:8765/api/settings >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Inicializando servidor FastAPI em segundo plano...
    cd /d "%~dp0Monitoramento LIVE"
    start /min "Servidor Cortes IA Pro" "%PYTHON_EXE%" -m uvicorn backend.server:app --host 127.0.0.1 --port 8765
    timeout /t 3 /nobreak >nul
) else (
    echo [OK] Servidor ja em execucao.
)

echo [INFO] Abrindo Studio de Crop no seu navegador padrao...
start "" "http://127.0.0.1:8765/studio"

exit /b 0
