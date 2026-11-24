@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0INICIAR_INTERFACE_GRAFICA.bat" %*
