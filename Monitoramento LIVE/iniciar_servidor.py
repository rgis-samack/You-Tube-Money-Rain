# -*- coding: utf-8 -*-
"""
Inicializador Desktop do Monitoramento LIVE
Inicia o servidor backend FastAPI e abre a janela em Modo Aplicativo Nativo (Microsoft Fluent)
"""

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
import time
import socket
import threading
import subprocess
import webbrowser
from pathlib import Path

DIR_MONITORAMENTO = Path(__file__).resolve().parent
PROJECT_DIR = DIR_MONITORAMENTO.parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"

# Auto-reexecuta no ambiente virtual caso tenha sido iniciado pelo Python global do sistema
if VENV_PYTHON.exists():
    try:
        if Path(sys.executable).resolve() != VENV_PYTHON.resolve():
            print(f"[INFO] Redirecionando execução para o ambiente virtual com IA: {VENV_PYTHON}")
            res = subprocess.call([str(VENV_PYTHON), str(Path(__file__).resolve())] + sys.argv[1:])
            sys.exit(res)
    except Exception as e:
        print(f"[AVISO] Falha ao re-executar com venv: {e}")

# Adiciona ao sys.path
if str(DIR_MONITORAMENTO) not in sys.path:
    sys.path.insert(0, str(DIR_MONITORAMENTO))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import uvicorn
from backend.config import CURRENT_CONFIG

PORTA = int(CURRENT_CONFIG.get("port", 8765))
HOST = CURRENT_CONFIG.get("host", "127.0.0.1")
URL_APP = f"http://{HOST}:{PORTA}"

def porta_em_uso(porta: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, porta)) == 0

def abrir_janela_aplicativo():
    """Abre como Janela Nativa de Aplicativo Windows (App Mode)"""
    time.sleep(1.2) # Aguarda servidor subir
    
    # Navegadores compatíveis com flag --app (Aparência 100% de aplicativo nativo)
    caminhos_navegadores = [
        Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Zen Browser\zen.exe")
    ]
    
    for nav in caminhos_navegadores:
        if nav.exists():
            print(f"[INTERFACE] Abrindo em Modo Janela Nativa com: {nav.name}")
            try:
                subprocess.Popen([str(nav), f"--app={URL_APP}", "--window-size=1380,920"])
                return
            except Exception as e:
                print(f"[INTERFACE] Falha ao abrir com {nav.name}: {e}")

    # Fallback para navegador padrão
    print(f"[INTERFACE] Abrindo no navegador padrão: {URL_APP}")
    webbrowser.open(URL_APP)

def iniciar():
    print("=" * 65)
    print("      MONITORAMENTO LIVE — TWITCH & KICK PRO")
    print("      Interface Microsoft Fluent 2 + Motor de Clipes Sem Censura")
    print("=" * 65)
    print(f"👉 Servidor Local: {URL_APP}")
    print(f"👉 Pasta de Downloads: {CURRENT_CONFIG.get('download_dir')}")
    print("=" * 65)

    if not porta_em_uso(PORTA, HOST):
        # Dispara abertura da janela em thread separada
        threading.Thread(target=abrir_janela_aplicativo, daemon=True).start()
        
        # Sobe o servidor FastAPI
        from backend.server import app
        uvicorn.run(app, host=HOST, port=PORTA, log_level="warning")
    else:
        print(f"[AVISO] Porta {PORTA} já está em execução. Abrindo janela...")
        abrir_janela_aplicativo()

if __name__ == "__main__":
    iniciar()
