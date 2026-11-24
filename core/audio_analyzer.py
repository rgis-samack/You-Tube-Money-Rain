# -*- coding: utf-8 -*-
"""
MOTOR DE ÁUDIO E INTELIGÊNCIA DE MINERAÇÃO VIRAL (O 'CÉREBRO')
- Análise de Picos de Volume (dB RMS)
- Cálculo Real de Densidade de Fala (WPM - Words Per Minute)
- Dicionário de Emoções, Gargalhadas, Conflitos e Curiosidade
- Alinhamento Inteligente de Início de Frase (sem cortar fala ao meio)
- Suporte a Audio Ducking nativo e Efeitos Sonoros de Impacto
"""

import math
import struct
import wave
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Any

from .config import TEMP_DIR, SFX_DIR, MUSICAS_DIR

PALAVRAS_CHAVE_VIRAL = [
    "kkk", "hahaha", "rsrs", "mano", "cara", "caralho", "porra", "meu deus",
    "nossa", "olha", "olha isso", "morri", "morreu", "tiro", "socorro",
    "policia", "polícia", "bizarro", "inacreditavel", "inacreditável",
    "absurdo", "loucura", "tancou", "não tankou", "trollou", "bugou",
    "fugiu", "escapou", "mentira", "duvido", "dedo", "pia", "biquini", "biquíni"
]

# Cadeia de filtros vocais de alta fidelidade para o Whisper:
# - highpass=85Hz: corta subgraves e batidas na mesa
# - lowpass=7500Hz: elimina chiados agudos de ventoinha/ar
# - afftdn: remoção espectral de ruído de microfone
# - equalizer=3200Hz: realce de consoantes humanas (s, t, p, k, d, b)
# - acompressor: nivelamento dinâmico de sussurros e gritos
FILTRO_VOCAL_WHISPER = (
    "highpass=f=85,"
    "lowpass=f=7500,"
    "afftdn=nr=12:nf=-30:tn=1,"
    "equalizer=f=3200:width_type=q:width=1.2:g=2.5,"
    "acompressor=threshold=-18dB:ratio=3:attack=10:release=100"
)

def extrair_audio_mono(video_path: Path, wav_path: Path, aplicar_limpeza_vocal: bool = True) -> bool:
    """Extrai áudio mono 16kHz com cadeia de filtros vocais de alta fidelidade para o Whisper."""
    cmd = [
        "ffmpeg", "-err_detect", "ignore_err", "-max_error_rate", "1.0",
        "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000"
    ]
    if aplicar_limpeza_vocal:
        cmd.extend(["-af", FILTRO_VOCAL_WHISPER])
    cmd.extend(["-y", str(wav_path)])
    
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if (res.returncode != 0 or not wav_path.exists()) and aplicar_limpeza_vocal:
        # Fallback sem filtros caso ocorra alguma incompatibilidade de codec
        cmd_fb = [
            "ffmpeg", "-err_detect", "ignore_err", "-max_error_rate", "1.0",
            "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000",
            "-y", str(wav_path)
        ]
        res_fb = subprocess.run(cmd_fb, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res_fb.returncode == 0 and wav_path.exists()
        
    return res.returncode == 0 and wav_path.exists()

def extrair_audio_mono_slice(video_path: Path, wav_path: Path, start_sec: float, dur_sec: float, aplicar_limpeza_vocal: bool = True) -> bool:
    """Extrai áudio mono 16kHz de um trecho específico com busca rápida e limpeza vocal."""
    cmd = [
        "ffmpeg", "-err_detect", "ignore_err", "-max_error_rate", "1.0",
        "-ss", str(max(0.0, start_sec)),
        "-t", str(max(1.0, dur_sec)),
        "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000"
    ]
    if aplicar_limpeza_vocal:
        cmd.extend(["-af", FILTRO_VOCAL_WHISPER])
    cmd.extend(["-y", str(wav_path)])
    
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if (res.returncode != 0 or not wav_path.exists()) and aplicar_limpeza_vocal:
        cmd_fb = [
            "ffmpeg", "-err_detect", "ignore_err", "-max_error_rate", "1.0",
            "-ss", str(max(0.0, start_sec)),
            "-t", str(max(1.0, dur_sec)),
            "-i", str(video_path),
            "-vn", "-ac", "1", "-ar", "16000",
            "-y", str(wav_path)
        ]
        res_fb = subprocess.run(cmd_fb, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res_fb.returncode == 0 and wav_path.exists()

    return res.returncode == 0 and wav_path.exists()

def analisar_energia_db(wav_path: Path, window_sec: float = 2.0) -> List[Tuple[float, float]]:
    """Calcula a curva de decibéis em janelas contínuas de tempo."""
    with wave.open(str(wav_path), "rb") as wf:
        nframes = wf.getnframes()
        rate = wf.getframerate()
        data = wf.readframes(nframes)

    samples = struct.unpack(f"<{len(data)//2}h", data)
    chunk_size = int(rate * window_sec)
    peaks = []

    for i in range(0, len(samples), chunk_size):
        chunk = samples[i:i + chunk_size]
        if not chunk:
            continue
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        db = 20 * math.log10(rms) if rms > 0 else -100.0
        sec = i / rate
        peaks.append((sec, db))

    return peaks

def calcular_score_viral(
    inicio: float,
    fim: float,
    db_pico: float,
    dialogos_no_trecho: List[Dict[str, Any]],
    db_medio_geral: float = 65.0
) -> Tuple[float, float, int, str]:
    """
    Algoritmo Multi-fator de Pontuação Viral:
    Score = (0.35 * Volume) + (0.35 * Densidade WPM) + (0.30 * Impacto Semântico)
    """
    duracao_min = max(0.1, (fim - inicio) / 60.0)
    
    # 1. Total de palavras e WPM
    total_palavras = 0
    texto_acumulado = []
    for d in dialogos_no_trecho:
        palavras = d.get("text", "").split()
        total_palavras += len(palavras)
        texto_acumulado.append(d.get("text", ""))

    wpm = total_palavras / duracao_min
    texto_completo = " ".join(texto_acumulado).lower()

    # 2. Score de Volume normalizado (0 a 100)
    delta_db = max(0.0, db_pico - db_medio_geral)
    score_db = min(100.0, (delta_db / 18.0) * 100.0)

    # Se não há transcrição de falas (modo sem legendas / mineração pura por energia dB)
    if not dialogos_no_trecho:
        score_final = score_db
        motivo = f"Pico dB: {db_pico:.1f} (+{delta_db:.1f}dB acima da média)"
        return score_final, 0.0, 0, motivo

    # 3. Score de WPM normalizado (Sweet spot: 120 a 160 WPM)
    if wpm < 60:
        score_wpm = wpm * 0.5 # streamer quase calado
    elif wpm <= 160:
        score_wpm = min(100.0, (wpm / 140.0) * 100.0)
    else:
        score_wpm = 90.0 # fala muito rápida

    # 4. Score de Emoção / Palavras-chave / Risadas
    pontos_palavras = 0
    for termo in PALAVRAS_CHAVE_VIRAL:
        if termo in texto_completo:
            pontos_palavras += 15
    if "?" in texto_completo:
        pontos_palavras += 10
    if "!" in texto_completo:
        pontos_palavras += 10
    
    score_semantico = min(100.0, float(pontos_palavras))

    # Ponderação Final
    score_final = (0.35 * score_db) + (0.35 * score_wpm) + (0.30 * score_semantico)
    
    motivo = f"dB: {db_pico:.1f} | WPM: {wpm:.0f} | Palavras-chave: {pontos_palavras}pts"
    return score_final, wpm, total_palavras, motivo

def minerar_cortes_cerebro(
    peaks: List[Tuple[float, float]],
    transcricao: List[Dict[str, Any]],
    duracao_total: float,
    qtd: int = 10,
    duracao_corte: float = 40.0
) -> List[Dict[str, Any]]:
    """
    Minerador inteligente com alinhamento de início de frase e cooldown anti-repetição.
    """
    if not peaks:
        return []

    dbs = [p[1] for p in peaks if p[1] > -90]
    db_medio = float(sum(dbs) / len(dbs)) if dbs else 60.0

    candidatos = []
    # Analisa cada pico
    for sec_pico, db in peaks:
        # Ponto aproximado: 5s antes do pico
        ini_est = max(0.0, sec_pico - 5.0)
        fim_est = min(duracao_total, ini_est + duracao_corte)

        if fim_est - ini_est < 15.0:
            continue

        # Alinhamento Inteligente: encontra onde o streamer começou a frase imediatamente antes do pico
        falas_candidatas = [
            t for t in transcricao
            if (t["start"] >= ini_est - 4.0 and t["start"] <= sec_pico)
        ]
        if falas_candidatas:
            ini_real = max(0.0, falas_candidatas[0]["start"] - 0.5)
            fim_real = min(duracao_total, ini_real + duracao_corte)
        else:
            ini_real = ini_est
            fim_real = fim_est

        falas_no_corte = [
            t for t in transcricao
            if (ini_real <= t["start"] <= fim_real or ini_real <= t["end"] <= fim_real)
        ]

        score, wpm, tot_pal, motivo = calcular_score_viral(
            ini_real, fim_real, db, falas_no_corte, db_medio
        )

        candidatos.append({
            "start": ini_real,
            "end": fim_real,
            "duration": fim_real - ini_real,
            "db_peak": db,
            "wpm": wpm,
            "score": score,
            "dialogue": falas_no_corte,
            "motivo": motivo
        })

    # Ordena pelo Score Viral Composto
    candidatos.sort(key=lambda x: x["score"], reverse=True)

    # Aplica Cooldown e Seleção dos Melhores
    selecionados = []
    COOLDOWN = duracao_corte * 0.85 # Evita repetições

    for c in candidatos:
        # Checa se não sobrepõe com nenhum já escolhido
        if any(abs(s["start"] - c["start"]) < COOLDOWN for s in selecionados):
            continue
        selecionados.append(c)
        if len(selecionados) >= qtd:
            break

    # Reordena cronologicamente
    selecionados.sort(key=lambda x: x["start"])
    return selecionados

def construir_audio_ducking_filter(
    musica_path: Path,
    sfx_intro_path: Path = None,
    volume_musica: float = 0.20
) -> Tuple[List[str], str]:
    """
    Retorna os inputs extras de áudio e o filter_complex para Ducking Automático:
    - Música de fundo diminui quando a fala do streamer aparece (sidechain compression)
    - SFX de Whoosh/Bass Drop nos primeiros instantes
    """
    extra_inputs = []
    filter_parts = []
    
    idx_music = 1
    extra_inputs.extend(["-i", str(musica_path)])

    idx_sfx = None
    if sfx_intro_path and sfx_intro_path.exists():
        idx_sfx = 2
        extra_inputs.extend(["-i", str(sfx_intro_path)])

    # Ducking da música através da voz (0:a)
    # [1:a] asplit para ducking controlado
    # sidechaincompress: diminui a música em ~16dB com retorno suave
    filter_ducking = (
        f"[{idx_music}:a]volume={volume_musica}[bg];"
        f"[bg][0:a]sidechaincompress=threshold=0.08:ratio=6:attack=20:release=350[ducked_bg];"
    )
    filter_parts.append(filter_ducking)

    if idx_sfx is not None:
        filter_parts.append(
            f"[{idx_sfx}:a]volume=0.6[sfx];"
            f"[0:a][ducked_bg][sfx]amix=inputs=3:duration=first:dropout_transition=2[outa]"
        )
    else:
        filter_parts.append(
            f"[0:a][ducked_bg]amix=inputs=2:duration=first:dropout_transition=2[outa]"
        )

    return extra_inputs, "".join(filter_parts)
