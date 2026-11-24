# -*- coding: utf-8 -*-
"""
VISÃO COMPUTACIONAL E RASTREAMENTO FACIAL ESTÁVEL (YuNet)
- Filtro de escala: rejeita close-ups gigantes de cutscenes do jogo (> 18% da tela)
- Centralização milimétrica do crop na face real do streamer
- Identificação precisa de cantos (esquerda ou direita)
"""

import subprocess
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from .config import TEMP_DIR, YUNET_MODEL

def detectar_webcam_yunet(
    video_path: Path,
    start_s: float,
    dur_s: float,
    video_w: int = 1920,
    video_h: int = 1080
) -> Tuple[str, int, int, int, int]:
    """
    Rastreamento facial preciso via YuNet ONNX com filtro anti-cutscene.
    Retorna: (tipo_cam, cam_x, cam_y, cam_w, cam_h)
    tipo_cam: 'WEBCAM_DIREITA', 'WEBCAM_ESQUERDA' ou 'SEM_WEBCAM'
    """
    if not YUNET_MODEL.exists():
        return "SEM_WEBCAM", 0, 0, 0, 0

    corner_faces = []
    samples = 7 # 7 amostras para estabilidade máxima

    for k in range(samples):
        t = start_s + (k + 0.5) * (dur_s / samples)
        frame_jpg = TEMP_DIR / f"det_frame_{k}.jpg"
        if frame_jpg.exists():
            try: frame_jpg.unlink()
            except: pass

        cmd = [
            "ffmpeg", "-err_detect", "ignore_err", "-max_error_rate", "1.0",
            "-ss", str(t), "-i", str(video_path),
            "-frames:v", "1", "-update", "1", "-q:v", "2", str(frame_jpg), "-y"
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not frame_jpg.exists():
            continue

        img = cv2.imread(str(frame_jpg))
        try: frame_jpg.unlink(missing_ok=True)
        except: pass

        if img is None:
            continue
        h, w = img.shape[:2]

        try:
            det = cv2.FaceDetectorYN.create(str(YUNET_MODEL), "", (w, h), 0.55, 0.3)
            _, faces = det.detect(img)
            if faces is not None:
                for fa in faces:
                    fx, fy, fw, fh, conf = fa[0], fa[1], fa[2], fa[3], fa[14]
                    
                    # FILTRO ANTI-CUTSCENE:
                    # Rostos de webcam têm tamanho proporcional de 2% a 18% da largura da tela
                    # Rostos gigantes (> 18%) são closes cinematográficos do próprio jogo (GTA, etc)
                    if fw > w * 0.18 or fw < w * 0.02:
                        continue
                    if fh > h * 0.30 or fh < h * 0.03:
                        continue

                    fc_x = fx + fw / 2.0
                    fc_y = fy + fh / 2.0

                    # Cantos: até 40% na esquerda ou a partir de 60% na direita
                    if fc_x < w * 0.40:
                        corner_faces.append(("LEFT", fx, fy, fw, fh, fc_x, fc_y, conf))
                    elif fc_x > w * 0.60:
                        corner_faces.append(("RIGHT", fx, fy, fw, fh, fc_x, fc_y, conf))
        except Exception:
            continue

    left_faces = [f for f in corner_faces if f[0] == "LEFT"]
    right_faces = [f for f in corner_faces if f[0] == "RIGHT"]

    cam_w = int(video_w * 0.25)
    cam_h = int(cam_w * 9 / 16)

    # Escolhe o canto mais estável (com mais detecções consistentes)
    if len(left_faces) >= 3 and len(left_faces) >= len(right_faces):
        med_fc_x = float(np.median([f[5] for f in left_faces]))
        med_fc_y = float(np.median([f[6] for f in left_faces]))
        cam_x = max(0, min(video_w - cam_w, int(med_fc_x - cam_w / 2.0)))
        cam_y = max(0, min(video_h - cam_h, int(med_fc_y - cam_h * 0.45)))
        return "WEBCAM_ESQUERDA", cam_x, cam_y, cam_w, cam_h

    elif len(right_faces) >= 3:
        med_fc_x = float(np.median([f[5] for f in right_faces]))
        med_fc_y = float(np.median([f[6] for f in right_faces]))
        cam_x = max(0, min(video_w - cam_w, int(med_fc_x - cam_w / 2.0)))
        cam_y = max(0, min(video_h - cam_h, int(med_fc_y - cam_h * 0.45)))
        return "WEBCAM_DIREITA", cam_x, cam_y, cam_w, cam_h

    return "SEM_WEBCAM", 0, 0, 0, 0
