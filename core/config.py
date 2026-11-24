# -*- coding: utf-8 -*-
"""
CONFIGURAÇÕES GLOBAIS E CAMINHOS DO PROJETO
100% Autônomo e sem dependências de diretórios temporários do Antigravity
"""

import os
import sys
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

STREAMLINK_LOCAL_VENV = PROJECT_DIR / ".venv" / "Scripts" / "streamlink.exe"
STREAMLINK_DEV_VENV = Path(r"C:\DEV\Linux\streamlink\.venv\Scripts\streamlink.exe")
STREAMLINK_SYS_EXE = Path(r"C:\Program Files\Streamlink\bin\streamlink.exe")
import shutil
STREAMLINK_WHICH = shutil.which("streamlink")

if STREAMLINK_LOCAL_VENV.exists():
    STREAMLINK_EXE = STREAMLINK_LOCAL_VENV
elif STREAMLINK_DEV_VENV.exists():
    STREAMLINK_EXE = STREAMLINK_DEV_VENV
elif STREAMLINK_SYS_EXE.exists():
    STREAMLINK_EXE = STREAMLINK_SYS_EXE
elif STREAMLINK_WHICH:
    STREAMLINK_EXE = Path(STREAMLINK_WHICH)
else:
    STREAMLINK_EXE = Path("streamlink")

GRAVACOES_DIR = PROJECT_DIR / "gravacoes"
if not GRAVACOES_DIR.exists():
    dev_gravacoes = Path(r"C:\DEV\Linux\streamlink\gravacoes")
    if dev_gravacoes.exists():
        GRAVACOES_DIR = dev_gravacoes
    else:
        GRAVACOES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR = PROJECT_DIR / "temp"
ASSETS_DIR = PROJECT_DIR / "assets"
SFX_DIR = ASSETS_DIR / "sfx"
MUSICAS_DIR = ASSETS_DIR / "musicas"
YUNET_MODEL = PROJECT_DIR / "yunet.onnx"

TEMP_DIR.mkdir(parents=True, exist_ok=True)
SFX_DIR.mkdir(parents=True, exist_ok=True)
MUSICAS_DIR.mkdir(parents=True, exist_ok=True)

# Presets de Resolução e Bitrate para GPU AMD AMF
RESOLUCOES = {
    "2K": {"w": 1440, "h": 2560, "bitrate": "25M", "maxrate": "32M", "bufsize": "48M"},
    "1080p": {"w": 1080, "h": 1920, "bitrate": "16M", "maxrate": "20M", "bufsize": "32M"},
    "4K": {"w": 2160, "h": 3840, "bitrate": "35M", "maxrate": "45M", "bufsize": "70M"}
}

def limpar_string_arquivo(texto: str, max_len: int = 40) -> str:
    s = re.sub(r'[\\/*?:"<>|]', "", str(texto)).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:max_len]

def seg_para_hms(seg: float) -> str:
    h = int(seg // 3600)
    m = int((seg % 3600) // 60)
    s = int(seg % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def hms_para_seg(hms_str: str) -> float:
    partes = str(hms_str).strip().split(":")
    try:
        if len(partes) == 3:
            return float(partes[0]) * 3600 + float(partes[1]) * 60 + float(partes[2])
        elif len(partes) == 2:
            return float(partes[0]) * 60 + float(partes[1])
        else:
            return float(partes[0])
    except (ValueError, IndexError):
        return 0.0
