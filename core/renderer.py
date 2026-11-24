# -*- coding: utf-8 -*-
"""
MOTOR DE RENDERIZAÇÃO VERTICAL DE ALTA PERFORMANCE (GPU AMD AMF)
Layouts Profissionais:
1. SPLIT_PRO: Webcam Topo (38%) + Linha Divisória de Estúdio (via drawbox) + Jogo Base (62%)
2. FULL_BLEED_ZOOM: Tela Cheia 9:16 com Enquadramento Dinâmico
3. BLUR_BACKGROUND: Gameplay 16:9 centralizado com Fundo Desfocado (Downscaled Fast Blur)
Suporte integrado a Audio Ducking e Efeitos Sonoros (SFX)
"""

import os
import shutil
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from .config import TEMP_DIR, SFX_DIR, MUSICAS_DIR, RESOLUCOES
from .audio_analyzer import construir_audio_ducking_filter

def obter_info_video(vid_path: Path) -> Dict[str, Any]:
    """Extrai duração, resolução e taxa de quadros via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,size:stream=width,height,r_frame_rate,codec_name",
        "-of", "json", str(vid_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(res.stdout)
        dur = float(data.get("format", {}).get("duration", 0.0))
        w, h = 1920, 1080
        fps = 60
        for s in data.get("streams", []):
            if "width" in s and "height" in s:
                w, h = s["width"], s["height"]
                r_fr = s.get("r_frame_rate", "60/1")
                if "/" in r_fr:
                    num, den = r_fr.split("/")
                    fps = round(float(num) / max(1.0, float(den)))
                break
        return {"duration": dur, "width": w, "height": h, "fps": fps}
    except Exception:
        return {"duration": 0.0, "width": 1920, "height": 1080, "fps": 60}

def renderizar_video_corte(
    video_origem: Path,
    saida_mp4: Path,
    ass_path: Optional[Path] = None,
    c_start: float = 0.0,
    c_dur: float = 40.0,
    layout: str = "SPLIT_PRO",
    webcam_info: tuple = ("SEM_WEBCAM", 0, 0, 0, 0),
    target_res: str = "2K",
    usar_ducking: bool = False,
    musica_nome: str = "synthwave_energy.wav",
    usar_sfx: bool = True,
    queimar_legendas: bool = True,
    custom_crop: Optional[dict] = None
) -> bool:
    """
    Renderiza o corte com aceleração GPU AMD AMF (Radeon RX 7600).
    Gravação atômica segura: renderiza em arquivo temporário e só substitui se válido.
    Permite renderizar com ou sem legendas queimadas na tela.
    Suporta layout interativo personalizado com cortes manuais de webcam e gameplay.
    """
    v_info = obter_info_video(video_origem)
    orig_w, orig_h = v_info["width"], v_info["height"]

    cfg_res = RESOLUCOES.get(target_res, RESOLUCOES["2K"])
    target_w, target_h = cfg_res["w"], cfg_res["h"]
    bitrate = cfg_res["bitrate"]
    maxrate = cfg_res["maxrate"]
    bufsize = cfg_res["bufsize"]

    tipo_cam, cam_x, cam_y, cam_w, cam_h = webcam_info
    tem_cam = tipo_cam in ["WEBCAM_DIREITA", "WEBCAM_ESQUERDA"]
    tem_legendas = bool(queimar_legendas and ass_path and Path(ass_path).exists())

    subs_ref = ""
    subs_temp = None

    if tem_legendas:
        # Cria arquivo temporário de legenda limpo no diretório de saída para evitar problemas de escape no FFmpeg
        subs_temp = saida_mp4.parent / f"_render_subs_{int(time.time()*1000)}.ass"
        try:
            shutil.copy2(str(ass_path), str(subs_temp))
            subs_ref = subs_temp.name
        except Exception as e:
            print(f"     ⚠️ Erro ao copiar legenda para render: {e}")
            subs_temp = Path(ass_path)
            subs_ref = subs_temp.name

    subs_filter = f",subtitles={subs_ref}" if tem_legendas else ""
    filter_complex_str = ""

    if (layout == "CUSTOM_SPLIT" or custom_crop) and custom_crop:
        # Layout Personalizado Interativo (Webcam + Gameplay definidos pelo usuário no Studio)
        split_ratio = float(custom_crop.get("split_ratio", 0.38))
        split_ratio = max(0.20, min(0.60, split_ratio))

        cam_h_alvo = int(target_h * split_ratio)
        if cam_h_alvo % 2 != 0:
            cam_h_alvo += 1
        game_h_alvo = target_h - cam_h_alvo
        if game_h_alvo % 2 != 0:
            game_h_alvo += 1

        cam_box = custom_crop.get("cam", {})
        game_box = custom_crop.get("display") or custom_crop.get("game", {})

        c_x = cam_box.get("x", 0)
        c_y = cam_box.get("y", 0)
        c_w = cam_box.get("w", orig_w * 0.3)
        c_h = cam_box.get("h", orig_h * 0.35)
        if c_w <= 1.0 and orig_w > 1:
            c_x = int(c_x * orig_w)
            c_y = int(c_y * orig_h)
            c_w = int(c_w * orig_w)
            c_h = int(c_h * orig_h)
        else:
            c_x, c_y, c_w, c_h = int(c_x), int(c_y), int(c_w), int(c_h)

        g_x = game_box.get("x", 0)
        g_y = game_box.get("y", 0)
        g_w = game_box.get("w", orig_w)
        g_h = game_box.get("h", orig_h)
        if g_w <= 1.0 and orig_w > 1:
            g_x = int(g_x * orig_w)
            g_y = int(g_y * orig_h)
            g_w = int(g_w * orig_w)
            g_h = int(g_h * orig_h)
        else:
            g_x, g_y, g_w, g_h = int(g_x), int(g_y), int(g_w), int(g_h)

        c_w = max(64, min(orig_w, c_w))
        c_h = max(64, min(orig_h, c_h))
        c_x = max(0, min(orig_w - c_w, c_x))
        c_y = max(0, min(orig_h - c_h, c_y))
        c_w -= c_w % 2
        c_h -= c_h % 2
        c_x -= c_x % 2
        c_y -= c_y % 2

        g_w = max(64, min(orig_w, g_w))
        g_h = max(64, min(orig_h, g_h))
        g_x = max(0, min(orig_w - g_w, g_x))
        g_y = max(0, min(orig_h - g_h, g_y))
        g_w -= g_w % 2
        g_h -= g_h % 2
        g_x -= g_x % 2
        g_y -= g_y % 2

        filter_complex_str = (
            f"[0:v]split=2[cam_in][game_in];"
            f"[cam_in]crop={c_w}:{c_h}:{c_x}:{c_y},scale={target_w}:{cam_h_alvo}[cam];"
            f"[game_in]crop={g_w}:{g_h}:{g_x}:{g_y},scale={target_w}:{game_h_alvo}[game];"
            f"[cam][game]vstack=inputs=2,drawbox=y={cam_h_alvo-3}:w=iw:h=6:color=0x00D4FF@0.9:t=fill"
            f"{subs_filter}[outv]"
        )

    elif layout == "SPLIT_PRO" and tem_cam:
        cam_h_alvo = int(target_h * 0.38)
        if cam_h_alvo % 2 != 0:
            cam_h_alvo += 1
        game_h_alvo = target_h - cam_h_alvo
        if game_h_alvo % 2 != 0:
            game_h_alvo += 1

        # Enquadramento Proporcional Estúdio: preserva aspect ratio exato sem distorcer o streamer
        cam_h_crop = min(orig_h, max(280, int(orig_h * (0.35 if orig_h <= 1080 else 0.28))))
        if cam_h_crop % 2 != 0:
            cam_h_crop += 1
        cam_w_crop = int(cam_h_crop * (target_w / cam_h_alvo))
        if cam_w_crop % 2 != 0:
            cam_w_crop += 1

        fc_x = cam_x + cam_w / 2.0
        fc_y = cam_y + cam_h / 2.0
        cam_x_real = max(0, min(orig_w - cam_w_crop, int(fc_x - cam_w_crop / 2.0)))
        cam_x_real -= cam_x_real % 2
        cam_y_real = max(0, min(orig_h - cam_h_crop, int(fc_y - cam_h_crop * 0.45)))
        cam_y_real -= cam_y_real % 2

        game_w_crop = int(orig_h * target_w / game_h_alvo)
        if game_w_crop % 2 != 0:
            game_w_crop += 1
        if tipo_cam == "WEBCAM_DIREITA":
            game_x_crop = max(0, min(cam_x_real - game_w_crop, int((orig_w - cam_w_crop - game_w_crop) / 2)))
        else:
            game_x_crop = min(orig_w - game_w_crop, max(cam_x_real + cam_w_crop, int((orig_w - game_w_crop) / 2)))
        game_x_crop -= game_x_crop % 2

        filter_complex_str = (
            f"[0:v]split=2[cam_in][game_in];"
            f"[cam_in]crop={cam_w_crop}:{cam_h_crop}:{cam_x_real}:{cam_y_real},scale={target_w}:{cam_h_alvo}[cam];"
            f"[game_in]crop={game_w_crop}:{orig_h}:{game_x_crop}:0,scale={target_w}:{game_h_alvo}[game];"
            f"[cam][game]vstack=inputs=2,drawbox=y={cam_h_alvo-3}:w=iw:h=6:color=0x00D4FF@0.9:t=fill"
            f"{subs_filter}[outv]"
        )

    elif layout == "DUAL_FOCUS":
        # Formato Dual Focus / Dual Screen:
        # Topo: Gameplay 16:9 completo e sem cortes (mostra webcam, hud e contexto geral)
        # Base: Zoom de ação vertical focado no centro da cena
        top_h = int(target_w * 9 / 16)
        if top_h % 2 != 0:
            top_h += 1

        bottom_h = target_h - top_h
        if bottom_h % 2 != 0:
            bottom_h += 1

        # Aspect ratio proporcional para preencher a base
        crop_w_bottom = int(orig_h * (target_w / bottom_h))
        if crop_w_bottom % 2 != 0:
            crop_w_bottom += 1
        crop_w_bottom = min(orig_w, crop_w_bottom)

        crop_x_bottom = int((orig_w - crop_w_bottom) / 2)
        if crop_x_bottom % 2 != 0:
            crop_x_bottom -= 1
        crop_x_bottom = max(0, min(orig_w - crop_w_bottom, crop_x_bottom))

        filter_complex_str = (
            f"[0:v]split=2[v_top_in][v_bottom_in];"
            f"[v_top_in]scale={target_w}:{top_h}[top_part];"
            f"[v_bottom_in]crop={crop_w_bottom}:{orig_h}:{crop_x_bottom}:0,scale={target_w}:{bottom_h}[bottom_part];"
            f"[top_part][bottom_part]vstack=inputs=2,drawbox=y={top_h-2}:w=iw:h=4:color=black@0.95:t=fill"
            f"{subs_filter}[outv]"
        )

    elif layout == "BLUR_BACKGROUND":
        # Downscaled Fast Blur: 15x mais rápido e sem engasgos
        game_h_center = int(target_w * (orig_h / orig_w))
        if game_h_center % 2 != 0:
            game_h_center += 1
        pad_top = (target_h - game_h_center) // 2
        if pad_top % 2 != 0:
            pad_top += 1
        filter_complex_str = (
            f"[0:v]split=2[v_bg][v_fg];"
            f"[v_bg]scale=360:640,boxblur=8:2,scale={target_w}:{target_h},eq=brightness=-0.18[bg];"
            f"[v_fg]scale={target_w}:{game_h_center}[fg];"
            f"[bg][fg]overlay=0:{pad_top}{subs_filter}[outv]"
        )

    else:
        # FULL_BLEED_ZOOM ou Fallback de tela cheia vertical 9:16
        crop_w_full = int(orig_h * 9 / 16)
        if crop_w_full % 2 != 0:
            crop_w_full += 1
        filter_complex_str = (
            f"[0:v]crop={crop_w_full}:{orig_h}:(iw-{crop_w_full})/2:0,"
            f"scale={target_w}:{target_h}"
            f"{subs_filter}[outv]"
        )

    # Configuração de Áudio (Normal vs Ducking)
    extra_audio_inputs = []
    audio_filter_complex = ""
    tem_ducking = False

    # Verifica se o vídeo de origem possui stream de áudio válido
    tem_audio = True
    try:
        probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video_origem)]
        probe_res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        tem_audio = bool(probe_res.stdout.strip())
    except Exception:
        tem_audio = True

    if usar_ducking and tem_audio:
        musica_path = MUSICAS_DIR / musica_nome
        sfx_path = SFX_DIR / "impact_whoosh.wav" if usar_sfx else None
        if musica_path.exists():
            extra_audio_inputs, audio_filter_complex = construir_audio_ducking_filter(
                musica_path=musica_path,
                sfx_intro_path=sfx_path,
                volume_musica=0.18
            )
            tem_ducking = True

    tmp_out = saida_mp4.parent / f"_tmp_{saida_mp4.name}"
    if tmp_out.exists():
        try: tmp_out.unlink()
        except: pass

    cmd = [
        "ffmpeg",
        "-err_detect", "ignore_err",
        "-max_error_rate", "1.0",
        "-ss", str(c_start),
        "-t", str(c_dur),
        "-i", str(video_origem)
    ]

    if tem_ducking:
        cmd.extend(extra_audio_inputs)
        full_filter = filter_complex_str + ";" + audio_filter_complex
        cmd.extend([
            "-filter_complex", full_filter,
            "-map", "[outv]",
            "-map", "[outa]"
        ])
    elif tem_audio:
        cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", "[outv]",
            "-map", "0:a?",
            "-af", "volume=2dB"
        ])
    else:
        cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", "[outv]",
            "-an"
        ])

    cmd.extend([
        "-c:v", "h264_amf",
        "-quality", "quality",
        "-profile:v", "high",
        "-b:v", bitrate,
        "-maxrate", maxrate,
        "-bufsize", bufsize,
        "-pix_fmt", "yuv420p"
    ])
    if tem_audio or tem_ducking:
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k"
        ])
    cmd.extend([
        "-y", str(tmp_out)
    ])

    print(f"     -> Renderizando {c_dur:.1f}s via GPU AMF ({target_res})...", flush=True)
    t0 = time.time()
    try:
        res = subprocess.run(cmd, cwd=str(saida_mp4.parent), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"     ⚠️ Timeout no AMF ao renderizar {saida_mp4.name}. Tentando CPU...", flush=True)
        res = subprocess.CompletedProcess(cmd, returncode=1, stderr="Timeout expired")

    # Fallback para CPU caso o formato de entrada exija
    if res.returncode != 0:
        if res.stderr:
            print(f"     [AVISO AMF] {res.stderr[-350:].strip()}", flush=True)
        print(f"     -> Utilizando encoder CPU x264 para compatibilidade...", flush=True)
        cmd_cpu = [
            "ffmpeg",
            "-err_detect", "ignore_err",
            "-max_error_rate", "1.0",
            "-ss", str(c_start),
            "-t", str(c_dur),
            "-i", str(video_origem)
        ]
        if tem_ducking:
            cmd_cpu.extend(extra_audio_inputs)
            cmd_cpu.extend([
                "-filter_complex", full_filter,
                "-map", "[outv]",
                "-map", "[outa]"
            ])
        elif tem_audio:
            cmd_cpu.extend([
                "-filter_complex", filter_complex_str,
                "-map", "[outv]",
                "-map", "0:a?",
                "-af", "volume=2dB"
            ])
        else:
            cmd_cpu.extend([
                "-filter_complex", filter_complex_str,
                "-map", "[outv]",
                "-an"
            ])
        cmd_cpu.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-pix_fmt", "yuv420p"
        ])
        if tem_audio or tem_ducking:
            cmd_cpu.extend([
                "-c:a", "aac",
                "-b:a", "192k"
            ])
        cmd_cpu.extend([
            "-y", str(tmp_out)
        ])
        try:
            res = subprocess.run(cmd_cpu, cwd=str(saida_mp4.parent), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            print(f"     ❌ Timeout total no FFmpeg ao renderizar {saida_mp4.name}.", flush=True)
        if res.returncode != 0 and res.stderr:
            print(f"     [ERRO CPU x264] {res.stderr[-350:].strip()}", flush=True)

    dt = time.time() - t0

    # Limpeza do arquivo de legenda temporário
    if subs_temp and subs_temp.exists() and subs_temp != ass_path:
        try: subs_temp.unlink(missing_ok=True)
        except: pass

    if res.returncode == 0 and tmp_out.exists() and tmp_out.stat().st_size > 1000000:
        shutil.move(str(tmp_out), str(saida_mp4))
        mb = saida_mp4.stat().st_size / (1024 * 1024)
        print(f"     ✓ Finalizado em {dt:.1f}s | {mb:.1f} MB", flush=True)
        return True
    else:
        if tmp_out.exists():
            tmp_out.unlink(missing_ok=True)
        return False
