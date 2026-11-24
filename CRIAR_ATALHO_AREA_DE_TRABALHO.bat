@echo off
chcp 65001 >nul
title Criar Atalho na Area de Trabalho
cd /d "%~dp0"

echo Criando atalho na Area de Trabalho do Windows...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Cortes IA Pro.lnk')); $s.TargetPath = '%~dp00_INICIAR_AQUI.bat'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'Cortes IA Pro e Monitoramento LIVE'; $s.Save()"

if %errorlevel% equ 0 (
    echo [OK] Atalho "Cortes IA Pro" criado com sucesso na sua Area de Trabalho!
) else (
    echo [AVISO] Nao foi possivel criar o atalho automaticamente.
)

timeout /t 3 >nul
exit /b 0
