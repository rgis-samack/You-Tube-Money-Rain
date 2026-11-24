# -*- coding: utf-8 -*-
"""
PIPELINE PRINCIPAL DE MINERAÇÃO E PROCESSAMENTO
Orquestra o fluxo completo com feedback contínuo no terminal (CMD):
1. Extração e Análise de Áudio (Picos + WPM)
2. Transcrição Whisper com timestamps
3. Algoritmo de Pontuação Viral (Cérebro Multi-fator)
4. Rastreamento Facial YuNet Anti-Cutscene
5. Geração de Ganchos Virais e Legendas Dinâmicas MrBeast
6. Renderização de Alta Fidelidade (AMF) com Layouts Modernos e Ducking
"""

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import re
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from .config import (
    PROJECT_DIR, VENV_PYTHON, TEMP_DIR, RESOLUCOES,
    limpar_string_arquivo, seg_para_hms
)

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

from .audio_analyzer import (
    extrair_audio_mono, extrair_audio_mono_slice, analisar_energia_db, minerar_cortes_cerebro
)
from .vision import detectar_webcam_yunet
from .subtitles import gerar_ass_mrbeast, parse_arquivo_txt_companion, gerar_srt_universal
from .hook_generator import gerar_ganchos_virais, gerar_texto_post_completo
from .renderer import obter_info_video, renderizar_video_corte

# Cache de modelos Whisper por tamanho para evitar recargas desnecessárias na memória
_WHISPER_MODELS: Dict[str, Any] = {}

INITIAL_PROMPT_WHISPER = (
    "Transcrição de lives, podcasts e gameplay brasileira: "
    "gírias de internet, pontuação e acentuação corretas, nomes de streamers, "
    "Alanzoka, Cellbit, Bisteconee, Gaules, GTA 6, Twitch, Kick, risadas e reações espontâneas."
)

HOTWORDS_WHISPER = (
    "Alanzoka, Cellbit, Bisteconee, Gaules, GTA, GTA 6, tankou, não tankou, "
    "tancou, mano, véi, slk, gameplay, clipe, stream, streamer, tropa, caramba"
)

DICIONARIO_CORRECOES_FONETICAS = {
    r"\b[eE]la zoca\b": "Alanzoka",
    r"\b[aA]lan zoca\b": "Alanzoka",
    r"\b[aA]lazoca\b": "Alanzoka",
    r"\b[vV]istecone\b": "Bisteconee",
    r"\b[bB]istecone\b": "Bisteconee",
    r"\b[cC]elbit\b": "Cellbit",
    r"\b[tT]ancou\b": "tankou",
    r"\b[tT]ancar\b": "tankar",
    r"\b[nN]ão tancou\b": "não tankou",
    r"\b[gG]aule[sz]\b": "Gaules"
}

def corrigir_texto_transcricao(texto: str) -> str:
    """Aplica pós-processador ortográfico para corrigir vícios fonéticos conhecidos do Whisper."""
    import re
    res = texto
    for padrao, subst in DICIONARIO_CORRECOES_FONETICAS.items():
        res = re.sub(padrao, subst, res)
    return res

def obter_whisper_model(model_size: str = "medium", log_callback: Optional[Callable[[str], None]] = None):
    global _WHISPER_MODELS
    if WhisperModel is None:
        raise RuntimeError(
            "faster_whisper não foi encontrado no ambiente Python atual. "
            f"Certifique-se de executar via ambiente virtual: {VENV_PYTHON}"
        )
    if model_size not in _WHISPER_MODELS:
        msg = f"[Whisper IA] Inicializando modelo '{model_size}' com Silero VAD (8 threads CPU AVX2)..."
        if log_callback:
            log_callback(msg)
        else:
            print(msg, flush=True)
        _WHISPER_MODELS[model_size] = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
            cpu_threads=8
        )
    return _WHISPER_MODELS[model_size]

def transcrever_audio(
    wav_path: Path,
    model_size: str = "medium",
    progress_callback: Optional[Callable[[float, float], None]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    initial_prompt: Optional[str] = None
) -> list:
    """
    Transcreve o áudio completo com alta fidelidade:
    - Silero VAD ativo (filtra pausas e ruído sem fala)
    - initial_prompt contextualizado (PT-BR)
    - condition_on_previous_text=False (elimina efeito cascata de alucinação)
    - temperature=[0.0, 0.2, 0.4] (decodificação conservadora de alta confiança)
    - hotwords para vocabulário de lives e streamers
    - Pós-processador ortográfico para correção de nomes próprios
    """
    model = obter_whisper_model(model_size, log_callback=log_callback)
    prompt = initial_prompt or INITIAL_PROMPT_WHISPER
    
    if log_callback:
        log_callback(f"[Whisper IA] Analisando áudio com Silero VAD e decodificador neural '{model_size}'...")

    segments, info = model.transcribe(
        str(wav_path),
        language="pt",
        beam_size=5,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters=dict(
            min_silence_duration_ms=500,
            threshold=0.45,
            speech_pad_ms=250
        ),
        initial_prompt=prompt,
        condition_on_previous_text=False,
        repetition_penalty=1.1,
        no_repeat_ngram_size=3,
        temperature=[0.0, 0.2, 0.4],
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
        hotwords=HOTWORDS_WHISPER
    )
    total_dur = getattr(info, "duration", 0.0) if info else 0.0
    out = []
    last_cb_time = 0.0
    for s in segments:
        txt = s.text.strip()
        if txt:
            txt_corrigido = corrigir_texto_transcricao(txt)
            out.append({
                "start": s.start,
                "end": s.end,
                "text": txt_corrigido
            })
        if progress_callback and total_dur > 0:
            agora = time.time()
            if agora - last_cb_time >= 1.2:
                last_cb_time = agora
                pct = min(99.0, (s.end / total_dur) * 100.0)
                progress_callback(pct, s.end)
    if progress_callback:
        progress_callback(100.0, total_dur)
    return out

def processar_video_completo(
    video_path: Path,
    pasta_saida: Path,
    info_video: Optional[Dict[str, str]] = None,
    qtd_cortes: int = 10,
    dur_corte: float = 40.0,
    layout_modo: str = "SPLIT_PRO", # "SPLIT_PRO", "CUSTOM_SPLIT", "DUAL_FOCUS", "BLUR_BACKGROUND", "AUTO"
    target_res: str = "2K",
    usar_ducking: bool = False,
    musica_nome: str = "synthwave_energy.wav",
    usar_sfx: bool = True,
    gerar_legendas: bool = True,
    log_callback: Optional[Callable[[str], None]] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    custom_crop: Optional[dict] = None,
    whisper_model: str = "medium"
) -> list:
    """
    Executa a mineração e renderização completa de um vídeo com feedback detalhado no terminal.
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)
        else:
            print(msg, flush=True)

    pasta_saida.mkdir(parents=True, exist_ok=True)
    
    if info_video is None:
        stem = video_path.stem
        partes = stem.split("_")
        canal = partes[0].capitalize() if partes else "Streamer"
        titulo = " ".join(partes[1:]).capitalize() if len(partes) > 1 else stem
    else:
        canal = info_video.get("canal", "Streamer")
        titulo = info_video.get("titulo", "Gameplay")

    log("=" * 65)
    log(f"🎬 INICIANDO MINERAÇÃO VIRAL: {video_path.name}")
    log(f"Canal: {canal} | Assunto: {titulo}")
    log(f"Destino: {pasta_saida.name}")
    log(f"Modo de Layout: {layout_modo} | Resolução: {target_res} | Legendas: {'Sim (Whisper)' if gerar_legendas else 'Não (Vídeo Limpo / Rápido)'} | Ducking: {usar_ducking}")
    log("=" * 65)

    v_meta = obter_info_video(video_path)
    total_dur = v_meta["duration"]
    orig_w, orig_h = v_meta["width"], v_meta["height"]

    # 1. Extração de Áudio
    if progress_callback:
        progress_callback(0.04, "Extraindo áudio mono 16kHz...")
    wav_path = TEMP_DIR / f"{video_path.stem}_mono.wav"
    log("[1/5] Extraindo áudio mono 16kHz...")
    if not extrair_audio_mono(video_path, wav_path):
        log("❌ Erro ao extrair áudio.")
        return []
    if progress_callback:
        progress_callback(0.09, "Áudio extraído com sucesso")

    # 2. Análise de Picos e Whisper
    peaks = analisar_energia_db(wav_path)
    if gerar_legendas:
        log(f"[2/5] Analisando decibéis e transcrevendo falas com Whisper IA ({whisper_model} + Silero VAD)...")
        if total_dur > 1800:
            log(f"  ℹ️ Vídeo longo detectado ({seg_para_hms(total_dur)}). Transcrição Whisper em andamento com progresso em tempo real...")
        if progress_callback:
            progress_callback(0.10, f"Whisper IA ({whisper_model})...")

        t_whisper_start = time.time()
        last_log_time = 0.0

        def cb_whisper(pct, sec):
            nonlocal last_log_time
            agora = time.time()
            if agora - last_log_time >= 2.5 or pct >= 99.9:
                last_log_time = agora
                elapsed = agora - t_whisper_start
                eta_str = ""
                if pct > 1.0:
                    restante = max(0.0, (elapsed / pct) * (100.0 - pct))
                    eta_str = f" | Restante est.: {seg_para_hms(restante)}"
                log(f"  [Whisper IA] {pct:.1f}% concluído ({seg_para_hms(sec)} de {seg_para_hms(total_dur)}){eta_str}")
            if progress_callback:
                prog_norm = 0.10 + (pct / 100.0) * 0.43
                progress_callback(prog_norm, f"Whisper IA: {pct:.0f}% ({seg_para_hms(sec)})")

        transcricao = transcrever_audio(
            wav_path,
            model_size=whisper_model,
            progress_callback=cb_whisper,
            log_callback=log
        )
        log(f"  ✓ Transcrição concluída: {len(transcricao)} falas identificadas com alta fidelidade.")
    else:
        log("[2/5] Mineração ultra-rápida por volume dB (transcrição Whisper desativada)...")
        log(f"  ✓ {len(peaks)} picos de volume identificados instantaneamente.")
        transcricao = []

    if progress_callback:
        progress_callback(0.53, "Transcrição e picos processados")

    # 3. Mineração com o Novo Cérebro Viral
    if progress_callback:
        progress_callback(0.55, "Minerando picos virais...")
    if gerar_legendas:
        log(f"[3/5] Avaliando Picos dB + Densidade WPM + Palavras de Impacto...")
    else:
        log(f"[3/5] Selecionando os {qtd_cortes} maiores picos de intensidade sonora...")
    cortes = minerar_cortes_cerebro(peaks, transcricao, total_dur, qtd=qtd_cortes, duracao_corte=dur_corte)
    log(f"  ✓ {len(cortes)} momentos de pico viral selecionados!")

    # 4. Processamento de Cada Corte
    log(f"[4/5] Renderizando cortes verticais via GPU AMD Radeon RX 7600 AMF...")
    resultados = []

    for idx, c in enumerate(cortes, 1):
        c_start = c["start"]
        c_dur = c["duration"]
        prefixo = f"corte_{idx:02d}_{limpar_string_arquivo(canal)}_{limpar_string_arquivo(video_path.stem)}"
        out_mp4 = pasta_saida / f"{prefixo}.mp4"
        out_txt = pasta_saida / f"{prefixo}.txt"
        ass_path = pasta_saida / f"{prefixo}.ass"
        srt_path = pasta_saida / f"{prefixo}.srt"

        # Rastreamento Facial YuNet ou Custom Crop
        webcam_info = ("SEM_WEBCAM", 0, 0, 0, 0)
        layout_final = layout_modo
        if custom_crop or layout_modo == "CUSTOM_SPLIT":
            layout_final = "CUSTOM_SPLIT"
        elif layout_modo in ["AUTO", "SPLIT_PRO"]:
            webcam_info = detectar_webcam_yunet(video_path, c_start, c_dur, orig_w, orig_h)
            if webcam_info[0] in ["WEBCAM_DIREITA", "WEBCAM_ESQUERDA"]:
                layout_final = "SPLIT_PRO"
            else:
                layout_final = "BLUR_BACKGROUND" if layout_modo == "AUTO" else "FULL_BLEED_ZOOM"
        elif layout_modo == "DUAL_FOCUS":
            layout_final = "DUAL_FOCUS"

        # Ganchos Virais
        hook_principal, opcoes_hooks = gerar_ganchos_virais(c["dialogue"], canal=canal, assunto=titulo)

        # Diálogos relativos para ASS
        if gerar_legendas:
            dialogos_rel = []
            for d in c["dialogue"]:
                dialogos_rel.append({
                    "start": max(0.0, d["start"] - c_start),
                    "end": min(c_dur, d["end"] - c_start),
                    "text": d["text"]
                })
            gerar_ass_mrbeast(dialogos_rel, hook_principal, ass_path, c_dur, RESOLUCOES[target_res]["w"], RESOLUCOES[target_res]["h"])
            gerar_srt_universal(dialogos_rel, srt_path)

        # Salva o arquivo TXT estruturado
        txt_content = gerar_texto_post_completo(
            canal=canal,
            titulo_live=titulo,
            hook_principal=hook_principal,
            opcoes_hooks=opcoes_hooks,
            dialogos=c["dialogue"] if gerar_legendas else [],
            c_start=c_start,
            c_dur=c_dur,
            layout_tipo=layout_final,
            arquivo_origem=str(video_path),
            numero_corte=idx
        )
        if custom_crop:
            import json as _json
            txt_content = f"# CUSTOM_CROP: {_json.dumps(custom_crop)}\n" + txt_content

        with open(out_txt, "w", encoding="utf-8-sig") as f:
            f.write(txt_content)

        # Renderização do Vídeo com progresso detalhado
        log(f"\n  [{idx}/{len(cortes)}] Processando '{prefixo}.mp4' ({c_dur:.1f}s | Layout: {layout_final} | Score: {c['score']:.1f})...")
        if progress_callback:
            prog_render = 0.55 + ((idx - 1) / max(1, len(cortes))) * 0.42
            progress_callback(prog_render, f"Renderizando corte {idx}/{len(cortes)}")

        t0 = time.time()
        sucesso = renderizar_video_corte(
            video_origem=video_path,
            saida_mp4=out_mp4,
            ass_path=ass_path if gerar_legendas else None,
            c_start=c_start,
            c_dur=c_dur,
            layout=layout_final,
            webcam_info=webcam_info,
            target_res=target_res,
            usar_ducking=usar_ducking,
            musica_nome=musica_nome,
            usar_sfx=usar_sfx,
            queimar_legendas=gerar_legendas,
            custom_crop=custom_crop
        )
        dt = time.time() - t0

        if sucesso and out_mp4.exists():
            resultados.append(out_mp4)
            if progress_callback:
                prog_render = 0.55 + (idx / max(1, len(cortes))) * 0.42
                progress_callback(prog_render, f"Corte {idx}/{len(cortes)} finalizado")
        else:
            log(f"     ❌ Falha ao renderizar {out_mp4.name}")

    # 5. Gera script local de recriação
    criar_recriar_bat_na_pasta(pasta_saida)
    if progress_callback:
        progress_callback(1.0, "Processamento concluído!")
    log(f"\n🎉 Mineração concluída! {len(resultados)} vídeos salvos em:")
    log(f"👉 {pasta_saida}")
    return resultados

def recriar_corte_a_partir_do_txt(caminho_txt: Path, target_res: str = "2K") -> bool:
    """
    Recria o corte quando o usuário altera o arquivo .TXT com progresso completo no terminal (CMD).
    """
    if not caminho_txt.exists():
        print(f"[ERRO] Arquivo não encontrado: {caminho_txt}", flush=True)
        return False

    print("=" * 65, flush=True)
    print(f"🔄 RECRIANDO VÍDEO A PARTIR DO TXT: {caminho_txt.name}", flush=True)
    print("=" * 65, flush=True)

    print("[*] [1/4] Lendo metadados e legendas editadas do arquivo TXT...", flush=True)
    metadados, hook_texto, falas_editadas = parse_arquivo_txt_companion(caminho_txt)

    raw_origem = metadados.get("ARQUIVO_ORIGEM", "").strip()
    video_origem = Path(raw_origem) if raw_origem else Path("")
    
    c_start = float(metadados.get("INICIO_CORTE", 0.0))
    c_dur = float(metadados.get("DURACAO", 40.0))
    layout_tipo = str(metadados.get("TIPO", "SPLIT_PRO")).upper()

    if not video_origem.exists():
        locais_busca = [
            caminho_txt.parent,
            caminho_txt.parent.parent,
            PROJECT_DIR,
            PROJECT_DIR / "videos",
            PROJECT_DIR / "gravacoes",
            PROJECT_DIR / "alanzoka",
            PROJECT_DIR / "Teste edit",
            Path(r"C:\DEV\Linux\streamlink\gravacoes"),
            Path(r"C:\DEV\Linux\streamlink\gravacoes\Twitch"),
            Path(r"C:\DEV\Linux\streamlink\gravacoes\Kick"),
            Path(r"B:\smartlink"),
            Path(r"B:\Samack Downloads")
        ]
        for loc in locais_busca:
            if video_origem.name:
                cand = loc / video_origem.name
                if cand.exists():
                    video_origem = cand
                    break

        # Busca por arquivo original local no diretório atual ou no diretório pai (ex: pastas de Hora_01)
        if not video_origem.exists():
            for p_dir in [caminho_txt.parent, caminho_txt.parent.parent]:
                if not p_dir.exists():
                    continue
                originais_locais = list(p_dir.glob("original_*.mp4"))
                if originais_locais:
                    video_origem = originais_locais[0]
                    break
                # Candidatos que não são cortes nem fatias temporárias
                cands = [
                    f for f in p_dir.glob("*.mp4")
                    if not f.name.lower().startswith("corte_")
                    and not f.name.lower().startswith("corte")
                    and not f.name.lower().startswith("slice_")
                    and not f.name.lower().startswith("temp_")
                ]
                if cands:
                    video_origem = cands[0]
                    break

        # Se não encontrou localmente, verifica se o vídeo veio do YouTube pelo ID no nome ou pasta
        if not video_origem.exists():
            texto_busca = f"{raw_origem} {caminho_txt.stem} {caminho_txt.parent.name} {metadados.get('TITULO_LIVE', '')}"
            m1 = re.search(r"yt_([a-zA-Z0-9_-]{11})", texto_busca)
            m2 = re.search(r"(?:watch\?v=|youtu\.be/|\[)([a-zA-Z0-9_-]{11})(?:\]|\&|\b|$)", texto_busca)
            yt_id = m1.group(1) if m1 else (m2.group(1) if m2 else None)
            
            if yt_id:
                yt_url = f"https://www.youtube.com/watch?v={yt_id}"
                print(f"[*] Vídeo bruto não encontrado localmente em '{raw_origem}'.", flush=True)
                print(f"[*] Baixando fatia original de {c_dur:.1f}s diretamente do YouTube ({yt_id}) via yt-dlp...", flush=True)
                slice_file = TEMP_DIR / f"slice_{yt_id}_{int(c_start)}_{int(c_dur)}.mp4"
                if not slice_file.exists():
                    end_slice = c_start + c_dur
                    cmd_ytdlp = [
                        "yt-dlp",
                        "--download-sections", f"*{c_start:.2f}-{end_slice:.2f}",
                        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                        "--merge-output-format", "mp4",
                        "-o", str(slice_file),
                        yt_url
                    ]
                    subprocess.run(cmd_ytdlp, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if slice_file.exists():
                    video_origem = slice_file
                    c_start = 0.0 # O trecho já foi baixado na posição exata!
                    print(f"  ✓ Trecho original obtido com sucesso: {slice_file.name}", flush=True)

        if not video_origem.exists():
            print(f"\n❌ [ERRO] O vídeo original de alta resolução não foi encontrado em '{raw_origem}'.", flush=True)
            print(f"   Certifique-se de que o arquivo original está na pasta ou corrija o caminho em '# ARQUIVO_ORIGEM:'.", flush=True)
            return False

    print(f"  ✓ Vídeo de origem: {video_origem.name} (Início: {c_start:.1f}s, Duração: {c_dur:.1f}s)", flush=True)
    print(f"  ✓ Layout selecionado: {layout_tipo} | Gancho: {hook_texto}", flush=True)

    cfg_res = RESOLUCOES.get(target_res, RESOLUCOES["2K"])
    target_w, target_h = cfg_res["w"], cfg_res["h"]

    queimar_legendas = bool(falas_editadas)
    ass_path = None
    if queimar_legendas:
        print("[*] [2/4] Gerando novo arquivo de legendas dinâmicas MrBeast...", flush=True)
        ass_path = caminho_txt.with_suffix(".ass")
        gerar_ass_mrbeast(falas_editadas, hook_texto, ass_path, c_dur, target_w, target_h)
        # Atualiza também o arquivo .SRT para visualização universal
        srt_path = caminho_txt.with_suffix(".srt")
        gerar_srt_universal(falas_editadas, srt_path)
    else:
        print("[*] [2/4] Vídeo limpo (sem legendas na tela)...", flush=True)

    print("[*] [3/4] Detectando posicionamento facial e enquadramento...", flush=True)
    out_mp4 = caminho_txt.with_suffix(".mp4")
    webcam_info = ("SEM_WEBCAM", 0, 0, 0, 0)
    custom_crop = None
    if metadados.get("CUSTOM_CROP"):
        try:
            import json as _json
            custom_crop = _json.loads(metadados["CUSTOM_CROP"])
            layout_tipo = "CUSTOM_SPLIT"
            print(f"  ✓ Layout Interativo Personalizado carregado do TXT!", flush=True)
        except Exception:
            pass

    if not custom_crop and "SPLIT" in layout_tipo:
        v_meta = obter_info_video(video_origem)
        webcam_info = detectar_webcam_yunet(video_origem, c_start, c_dur, v_meta["width"], v_meta["height"])
        print(f"  ✓ Detecção de Webcam: {webcam_info[0]}", flush=True)

    print(f"[*] [4/4] Renderizando vídeo em 2K Vertical via GPU AMD AMF...", flush=True)
    t0 = time.time()
    sucesso = renderizar_video_corte(
        video_origem=video_origem,
        saida_mp4=out_mp4,
        ass_path=ass_path,
        c_start=c_start,
        c_dur=c_dur,
        layout=layout_tipo,
        webcam_info=webcam_info,
        target_res=target_res,
        usar_ducking=False,
        queimar_legendas=queimar_legendas,
        custom_crop=custom_crop
    )
    dt = time.time() - t0

    if sucesso and out_mp4.exists():
        mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"\n🎉 VÍDEO RECRIADO COM SUCESSO EM {dt:.1f}s! ({mb:.1f} MB)", flush=True)
        print(f"👉 Arquivo pronto: {out_mp4.name}", flush=True)
        return True
    else:
        print(f"\n❌ Erro ao recriar o vídeo. O original foi preservado intacto.", flush=True)
        return False

def criar_recriar_bat_na_pasta(pasta: Path):
    """Cria recriar_corte.bat e ARRASTAR_TXT_AQUI_PARA_EDITAR.bat com unbuffered I/O para saída em tempo real no CMD."""
    conteudo = (
        "@echo off\r\n"
        "chcp 65001 >nul\r\n"
        "set \"PYTHONUNBUFFERED=1\"\r\n"
        "title Re-renderizar Corte IA via CMD (AMD GPU AMF)\r\n"
        "cd /d \"%~dp0\"\r\n"
        "\r\n"
        f"set \"PYTHON_EXE={VENV_PYTHON}\"\r\n"
        f"set \"MINERAR_PY={PROJECT_DIR}\\minerar_live.py\"\r\n"
        "\r\n"
        "if not \"%~1\"==\"\" goto COM_ARQUIVO\r\n"
        "\r\n"
        ":SEM_ARQUIVO\r\n"
        "echo =====================================================================\r\n"
        "echo   RE-RENDERIZAR CORTE IA A PARTIR DO ARQUIVO .TXT EDITADO\r\n"
        "echo =====================================================================\r\n"
        "echo Arraste o arquivo .txt para cima deste .bat ou digite o nome abaixo:\r\n"
        "echo.\r\n"
        "set /p \"TXT_FILE=Nome ou caminho do arquivo .txt: \"\r\n"
        "call \"%PYTHON_EXE%\" -u \"%MINERAR_PY%\" \"%~dp0%TXT_FILE%\"\r\n"
        "goto FIM\r\n"
        "\r\n"
        ":COM_ARQUIVO\r\n"
        "call \"%PYTHON_EXE%\" -u \"%MINERAR_PY%\" \"%~f1\"\r\n"
        "\r\n"
        ":FIM\r\n"
        "pause\r\n"
    )
    for nome_bat in ["ARRASTAR_TXT_AQUI_PARA_EDITAR.bat", "recriar_corte.bat"]:
        bat_path = pasta / nome_bat
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(conteudo)
