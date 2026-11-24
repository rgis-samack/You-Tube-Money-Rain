# -*- coding: utf-8 -*-
"""
Configurações Globais do Monitoramento LIVE
Gerencia diretórios, credenciais, preferências e persistência em config.json
"""

import os
import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
CONFIG_FILE = BASE_DIR / "config.json"

# Diretórios padrão
GRAVACOES_PADRAO = Path(r"C:\DEV\Linux\streamlink\gravacoes")
PROJECT_GRAVACOES = PROJECT_DIR / "gravacoes"
LOCAL_DOWNLOADS = BASE_DIR / "downloads"

if GRAVACOES_PADRAO.exists():
    DIR_DOWNLOAD_DEFAULT = str(GRAVACOES_PADRAO)
elif PROJECT_GRAVACOES.exists():
    DIR_DOWNLOAD_DEFAULT = str(PROJECT_GRAVACOES)
else:
    LOCAL_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    DIR_DOWNLOAD_DEFAULT = str(LOCAL_DOWNLOADS)

DEFAULT_CONFIG = {
    "download_dir": DIR_DOWNLOAD_DEFAULT,
    "twitch_client_id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
    "twitch_auth_token": "",
    "kick_auth_token": "",
    "bypass_18_plus": True,
    "port": 8765,
    "host": "127.0.0.1",
    "max_concurrent_downloads": 3,
    "auto_open_folder_after_download": False
}

def carregar_config():
    if not CONFIG_FILE.exists():
        salvar_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Mescla com defaults caso falte chave
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            # Se o diretorio salvo estiver vazio ou nao existir no computador atual, usa a pasta local padrao
            caminho_dir = cfg.get("download_dir", "")
            if not caminho_dir or not Path(caminho_dir).exists():
                cfg["download_dir"] = DIR_DOWNLOAD_DEFAULT
            return cfg
    except Exception as e:
        print(f"[CONFIG] Erro ao ler config.json: {e}")
        return DEFAULT_CONFIG.copy()

def salvar_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[CONFIG] Erro ao salvar config.json: {e}")
        return False

# Carrega configuração em memória
CURRENT_CONFIG = carregar_config()
