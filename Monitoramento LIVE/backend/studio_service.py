# -*- coding: utf-8 -*-
"""
CORTES IA PRO 2.0 - STUDIO SERVICE
Serviço de extração rápida de snapshots para preview interativo (Opus Clip / Streamladder Style)
Gera amostras leves em milissegundos sem sobrecarregar a memória, mesmo em lives de 4+ horas.
"""

import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DIR_RAIZ = Path(__file__).resolve().parent.parent.parent
if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

from core.config import PROJECT_DIR, TEMP_DIR, seg_para_hms
from core.renderer import obter_info_video
try:
    from core.vision import detectar_webcam_yunet
except Exception:
    detectar_webcam_yunet = None

PASTA_SNAPSHOTS = Path(__file__).resolve().parent.parent / "static" / "temp_snapshots"
PASTA_SNAPSHOTS.mkdir(parents=True, exist_ok=True)

LOCAIS_BUSCA_VIDEOS = [
    Path(r"B:\Samack Downloads"),
    Path(r"C:\DEV\Linux\streamlink\gravacoes"),
    Path(r"C:\DEV\Linux\streamlink\gravacoes\Twitch"),
    Path(r"C:\DEV\Linux\streamlink\gravacoes\Kick"),
    PROJECT_DIR / "videos",
    PROJECT_DIR / "gravacoes",
    Path(r"C:\DEV\PythonDownloader\Samack Downloads")
]

def resolver_caminho_video(caminho_str: str) -> Optional[Path]:
    """Localiza o arquivo de vídeo pelo caminho absoluto, relativo ou apenas nome."""
    if not caminho_str:
        return None
    p = Path(caminho_str.strip('"\''))
    if p.exists() and p.is_file():
        return p
    
    # Procura nos diretórios de download conhecidos
    for base in LOCAIS_BUSCA_VIDEOS:
        if not base.exists():
            continue
        cand = base / p.name
        if cand.exists() and cand.is_file():
            return cand
        # Busca recursiva rápida se for nome específico
        for f in base.glob(f"**/{p.name}"):
            if f.is_file():
                return f
    return None

def listar_videos_disponiveis() -> List[Dict]:
    """Lista todos os vídeos disponíveis nos diretórios de gravação e download (busca rápida)."""
    videos = []
    nomes_vistos = set()
    exts = {".mp4", ".mkv", ".mov", ".ts", ".webm"}

    for base in LOCAIS_BUSCA_VIDEOS:
        if not base.exists():
            continue
        try:
            # Varredura rasa (profundidade máx 2) para performance instantânea
            for root, dirs, files in os.walk(str(base)):
                rel_depth = len(Path(root).relative_to(base).parts)
                if rel_depth > 2:
                    dirs.clear()
                    continue
                for f_name in files:
                    ext = os.path.splitext(f_name)[1].lower()
                    if ext in exts:
                        low = f_name.lower()
                        if low.startswith("corte_") or low.startswith("slice_") or low.startswith("temp_"):
                            continue
                        if f_name in nomes_vistos:
                            continue
                        nomes_vistos.add(f_name)
                        
                        full_p = Path(root) / f_name
                        try:
                            sz_mb = full_p.stat().st_size / (1024 * 1024)
                            mod_time = time.strftime("%d/%m/%Y %H:%M", time.localtime(full_p.stat().st_mtime))
                            videos.append({
                                "nome": f_name,
                                "caminho": str(full_p),
                                "tamanho_mb": round(sz_mb, 1),
                                "modificado": mod_time,
                                "pasta": full_p.parent.name
                            })
                        except Exception:
                            pass
        except Exception:
            pass

    videos.sort(key=lambda x: x.get("tamanho_mb", 0), reverse=True)
    return videos

def extrair_snapshots_video(video_path: Path, qtd_frames: int = 8) -> Dict:
    """
    Extrai rapidamente 6 a 8 snapshots leves espaçados ao longo do vídeo com FFmpeg fast seek.
    Executa detecção facial YuNet para posicionar as caixas de CAM e DISPLAY automaticamente.
    """
    v_info = obter_info_video(video_path)
    dur = float(v_info.get("duration", 0.0))
    orig_w = int(v_info.get("width", 1920))
    orig_h = int(v_info.get("height", 1080))
    fps = v_info.get("fps", 60)

    if dur <= 0:
        dur = 60.0

    # Cria subpasta única para o vídeo
    safe_stem = "".join([c if c.isalnum() else "_" for c in video_path.stem])[:30]
    out_dir = PASTA_SNAPSHOTS / safe_stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # Gera timestamps espaçados (ex: 5%, 15%, 30%, 45%, 60%, 75%, 88%, 95%)
    ratios = [0.05, 0.15, 0.30, 0.45, 0.60, 0.75, 0.88, 0.95][:qtd_frames]
    sample_times = [max(1.0, min(dur - 1.0, dur * r)) for r in ratios]

    snapshots = []
    for idx, t in enumerate(sample_times):
        img_name = f"snap_{idx:02d}_{int(t)}s.jpg"
        img_path = out_dir / img_name
        
        # Só extrai se ainda não existir em cache
        if not img_path.exists() or img_path.stat().st_size == 0:
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{t:.2f}",
                "-i", str(video_path),
                "-vframes", "1",
                "-q:v", "3",
                "-vf", f"scale={min(1920, orig_w)}:-2",
                str(img_path)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if img_path.exists():
            snapshots.append({
                "index": idx,
                "time_sec": round(t, 1),
                "time_hms": seg_para_hms(t),
                "url": f"/static/temp_snapshots/{safe_stem}/{img_name}",
                "file_path": str(img_path)
            })

    # Detecção facial inteligente via YuNet na primeira fatia
    webcam_info = ("SEM_WEBCAM", 0, 0, 0, 0)
    if detectar_webcam_yunet:
        try:
            webcam_info = detectar_webcam_yunet(video_path, sample_times[0], min(40.0, dur), orig_w, orig_h)
        except Exception as e:
            print(f"[Studio] Erro na detecção facial: {e}")

    tipo_cam, f_x, f_y, f_w, f_h = webcam_info

    # Configura caixas iniciais padrão de enquadramento
    if tipo_cam in ["WEBCAM_DIREITA", "WEBCAM_ESQUERDA"]:
        # Expande um pouco para respiração e bordas da câmera
        pad_x = int(f_w * 0.25)
        pad_y = int(f_h * 0.30)
        c_x = max(0, f_x - pad_x)
        c_y = max(0, f_y - pad_y)
        c_w = min(orig_w - c_x, f_w + pad_x * 2)
        c_h = min(orig_h - c_y, f_h + pad_y * 2)

        # Garante proporção agradável (aprox 16:9 ou 4:3 para a webcam)
        if tipo_cam == "WEBCAM_DIREITA":
            disp_x = 0
            disp_y = 0
            disp_w = max(int(orig_w * 0.70), c_x)
            disp_h = orig_h
        else:
            disp_x = c_x + c_w
            disp_y = 0
            disp_w = orig_w - disp_x
            disp_h = orig_h
    else:
        # Fallback padrão estúdio: webcam superior esquerda, gameplay 16:9 central
        c_x = int(orig_w * 0.03)
        c_y = int(orig_h * 0.05)
        c_w = int(orig_w * 0.28)
        c_h = int(orig_h * 0.32)

        disp_x = 0
        disp_y = 0
        disp_w = orig_w
        disp_h = orig_h

    initial_crop = {
        "cam": {
            "x": int(c_x),
            "y": int(c_y),
            "w": int(c_w),
            "h": int(c_h)
        },
        "display": {
            "x": int(disp_x),
            "y": int(disp_y),
            "w": int(disp_w),
            "h": int(disp_h)
        },
        "split_ratio": 0.38, # 38% webcam no topo, 62% gameplay na base
        "tipo_detectado": tipo_cam
    }

    return {
        "success": True,
        "video_path": str(video_path),
        "nome": video_path.name,
        "duracao": dur,
        "duracao_hms": seg_para_hms(dur),
        "largura": orig_w,
        "altura": orig_h,
        "fps": fps,
        "snapshots": snapshots,
        "initial_crop": initial_crop
    }
