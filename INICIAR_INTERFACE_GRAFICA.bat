@echo off
chcp 65001 >nul
title Cortes Studio Pro - Interface Grafica Desktop
cd /d "%~dp0"

:: Varredura rapida do ambiente
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo =====================================================================
    echo   [PRIMEIRA EXECUCAO] Configurando o ambiente com 1 clique...
    echo =====================================================================
    call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
) else (
    "%~dp0.venv\Scripts\python.exe" -c "import customtkinter, cv2, fastapi" >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Reparando dependencias ausentes...
        call "%~dp0INSTALAR_DEPENDENCIAS.bat" --auto
    )
)

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if "%~1"=="" (
    start "" "%PYTHON_EXE%" "%~dp0gui_cortes.py"
) else (
    start "" "%PYTHON_EXE%" "%~dp0gui_cortes.py" "%~1"
)

exit /b 0
