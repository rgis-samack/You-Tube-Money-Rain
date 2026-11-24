# -*- coding: utf-8 -*-
"""
Processador Automático de Cortes Virais Pro
Lê vídeos baixados pelo Monitoramento LIVE, organiza pastas por categoria
e executa o pipeline do Cortes IA Pro (Whisper + YuNet + GPU AMF + Legendas MrBeast)
com suporte a:
1. Mineração em Lote por Hora (10 cortes por hora de vídeo com liberação incremental imediata)
2. Mineração Top Momentos Globais
3. Conversão Direta de Clipes Curtos em formato 9:16 Vertical
4. Emissão de progresso estruturado em tempo real (JSON) para a interface web
"""

import os
import sys
import math
import time
import json
import shutil
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

DIR_MONITORAMENTO = Path(__file__).resolve().parent.parent
PROJECT_DIR = DIR_MONITORAMENTO.parent

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(DIR_MONITORAMENTO) not in sys.path:
    sys.path.insert(0, str(DIR_MONITORAMENTO))

from core.config import (
    PROJECT_DIR, VENV_PYTHON, TEMP_DIR, RESOLUCOES, limpar_string_arquivo, seg_para_hms
)
from core.audio_analyzer import (
    extrair_audio_mono, extrair_audio_mono_slice, analisar_energia_db, minerar_cortes_cerebro
)
from core.vision import detectar_webcam_yunet
from core.subtitles import gerar_ass_mrbeast, gerar_srt_universal
from core.hook_generator import gerar_ganchos_virais, gerar_texto_post_completo
from core.renderer import obter_info_video, renderizar_video_corte
from core.pipeline import transcrever_audio, processar_video_completo, criar_recriar_bat_na_pasta


def emitir_status(stage: str, pct: float, msg: str, detail: str = "", hora: int = 1, total_horas: int = 1):
    """Emite evento de status estruturado em JSON via stdout para o backend capturar."""
    payload = {
        "stage": stage,
        "pct": round(max(0.0, min(100.0, float(pct))), 1),
        "msg": msg,
        "detail": detail,
        "hora": int(hora),
        "total_horas": int(total_horas),
        "timestamp": time.time()
    }
    print(f"[STATUS_JSON] {json.dumps(payload, ensure_ascii=False)}", flush=True)


def emitir_corte_pronto(corte_num: int, hora: int, titulo: str, arquivo: str, path: str, duracao: float, pasta: str):
    """Emite evento de corte pronto individual para visualização e acesso imediato na interface."""
    payload = {
        "corte_num": int(corte_num),
        "hora": int(hora),
        "titulo": titulo,
        "arquivo": arquivo,
        "path": str(path),
        "duracao": round(float(duracao), 1),
        "pasta": str(pasta),
        "timestamp": time.time()
    }
    print(f"[CUT_READY] {json.dumps(payload, ensure_ascii=False)}", flush=True)


def emitir_hora_concluida(hora: int, total_horas: int, cortes_gerados: int, pasta: str, msg: str):
    """Emite evento de bloco de 1 hora finalizado com caminho de acesso aos arquivos."""
    payload = {
        "hora": int(hora),
        "total_horas": int(total_horas),
        "cortes_gerados": int(cortes_gerados),
        "pasta": str(pasta),
        "msg": msg,
        "timestamp": time.time()
    }
    print(f"[HOUR_COMPLETED] {json.dumps(payload, ensure_ascii=False)}", flush=True)


def emitir_processo_completo(sucesso: bool, total_cortes: int, pasta: str, original: str, msg: str):
    """Emite evento de conclusão de todo o processamento de mineração e cortes."""
    payload = {
        "sucesso": bool(sucesso),
        "total_cortes": int(total_cortes),
        "pasta": str(pasta),
        "arquivo_original": str(original),
        "msg": msg,
        "timestamp": time.time()
    }
    print(f"[PROCESS_COMPLETED] {json.dumps(payload, ensure_ascii=False)}", flush=True)


def criar_script_arrastar_bat(pasta: Path):
    """Cria script batch nativo para arrastar o .txt e re-editar no CMD com GPU AMF."""
    criar_recriar_bat_na_pasta(pasta)


def processar_clipe_curto(
    video_path: Path,
    pasta_saida: Path,
    canal: str,
    titulo: str,
    categoria: str,
    plataforma: str = "Twitch",
    views: str = "",
    ranking: Any = "",
    target_res: str = "1080p",
    layout_modo: str = "SPLIT_PRO"
) -> bool:
    """Processa um clipe curto (até 90 segundos) transformando-o integralmente em corte 9:16."""
    pasta_saida.mkdir(parents=True, exist_ok=True)
    v_meta = obter_info_video(video_path)
    total_dur = v_meta["duration"]
    orig_w, orig_h = v_meta["width"], v_meta["height"]

    emitir_status("audio_extract", 15.0, "Extraindo áudio mono 16kHz do clipe...", f"Duração: {total_dur:.1f}s", 1, 1)

    wav_path = TEMP_DIR / f"{video_path.stem}_mono.wav"
    if not extrair_audio_mono(video_path, wav_path):
        emitir_status("error", 0, "❌ Falha ao extrair áudio do clipe.")
        return False

    emitir_status("whisper", 30.0, "Transcrevendo falas com Whisper IA...", "Gerando timestamps por palavra", 1, 1)
    
    def cb_whisper(pct, sec):
        emitir_status("whisper", 30.0 + (pct * 0.25), f"Transcrevendo com Whisper: {pct:.0f}%", f"{sec:.1f}s de {total_dur:.1f}s", 1, 1)

    transcricao = transcrever_audio(wav_path, progress_callback=cb_whisper)
    emitir_status("whisper", 55.0, f"Transcrição concluída: {len(transcricao)} falas identificadas.")

    emitir_status("vision", 60.0, "Rastreando webcam do streamer com YuNet...", "Anti-cutscene com suavização EMA", 1, 1)
    webcam_info = detectar_webcam_yunet(video_path, 0.0, total_dur, orig_w, orig_h)
    layout_final = layout_modo
    if webcam_info[0] in ["WEBCAM_DIREITA", "WEBCAM_ESQUERDA"]:
        layout_final = "SPLIT_PRO"
    else:
        layout_final = "BLUR_BACKGROUND"

    hook_principal, opcoes_hooks = gerar_ganchos_virais(transcricao, canal=canal, assunto=titulo)

    prefixo = f"corte_01_[{limpar_string_arquivo(canal, 20)}]_[{limpar_string_arquivo(titulo, 30)}]"
    out_mp4 = pasta_saida / f"{prefixo}.mp4"
    out_txt = pasta_saida / f"{prefixo}.txt"
    ass_path = pasta_saida / f"{prefixo}.ass"
    srt_path = pasta_saida / f"{prefixo}.srt"

    res_w = RESOLUCOES[target_res]["w"]
    res_h = RESOLUCOES[target_res]["h"]
    gerar_ass_mrbeast(transcricao, hook_principal, ass_path, total_dur, res_w, res_h)
    gerar_srt_universal(transcricao, srt_path)

    txt_content = gerar_texto_post_completo(
        canal=canal,
        titulo_live=titulo,
        hook_principal=hook_principal,
        opcoes_hooks=opcoes_hooks,
        c_start=0.0,
        c_dur=total_dur,
        layout_tipo=layout_final,
        arquivo_origem=str(video_path),
        dialogos=transcricao,
        plataforma=plataforma,
        categoria=categoria,
        views=views,
        ranking=ranking,
        resolucao=target_res,
        fps=v_meta.get("fps", 60)
    )
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write(txt_content)

    criar_script_arrastar_bat(pasta_saida)
    criar_recriar_bat_na_pasta(pasta_saida)

    emitir_status("rendering", 75.0, f"Renderizando corte vertical em {target_res} via GPU AMF...", f"Layout: {layout_final}", 1, 1)
    render_ok = renderizar_video_corte(
        video_origem=video_path,
        saida_mp4=out_mp4,
        ass_path=ass_path,
        c_start=0.0,
        c_dur=total_dur,
        layout=layout_final,
        webcam_info=webcam_info,
        target_res=target_res,
        usar_ducking=False,
        musica_nome="synthwave_energy.wav",
        usar_sfx=True
    )

    if render_ok and out_mp4.exists():
        emitir_corte_pronto(1, 1, f"Corte 01 - {titulo}", out_mp4.name, str(out_mp4), total_dur, str(pasta_saida))
        emitir_hora_concluida(1, 1, 1, str(pasta_saida), f"Clipe concluído e salvo com sucesso em {pasta_saida.name}")
        emitir_processo_completo(True, 1, str(pasta_saida), str(video_path), "Processamento do clipe finalizado!")
        return True
    
    emitir_status("error", 0, "❌ Falha ao renderizar corte do clipe.")
    return False


def processar_video_por_horas(
    video_path: Path,
    pasta_saida_raiz: Path,
    canal: str,
    titulo: str,
    categoria: str,
    plataforma: str = "Twitch",
    views: str = "",
    ranking: Any = "",
    cortes_por_hora: int = 10,
    dur_corte: float = 40.0,
    target_res: str = "1080p",
    layout_modo: str = "SPLIT_PRO"
) -> bool:
    """
    Mineração em Lote por Hora:
    Divide o vídeo em blocos de 1 hora (0h-1h, 1h-2h, ...).
    Para cada hora:
      1. Extrai slice de áudio de 1h
      2. Transcreve com Whisper reportando progresso em tempo real
      3. Minera os 10 melhores momentos daquela hora
      4. Renderiza os 10 cortes 9:16 com GPU AMF e legendas animadas
      5. Salva na subpasta Hora_XX com .txt, .srt, .ass e .bat
      6. Notifica IMEDIATAMENTE a cada corte e a cada hora finalizada!
    """
    pasta_saida_raiz.mkdir(parents=True, exist_ok=True)
    v_meta = obter_info_video(video_path)
    total_dur = v_meta["duration"]
    orig_w, orig_h = v_meta["width"], v_meta["height"]

    total_horas = max(1, math.ceil(total_dur / 3600.0))
    peso_hora = 100.0 / total_horas
    todos_cortes_gerados = []

    emitir_status(
        "starting_hours",
        2.0,
        f"Iniciando mineração por blocos de 1 hora ({total_horas} blocos no total)",
        f"Total: {seg_para_hms(total_dur)} • {cortes_por_hora} cortes por hora planejados",
        1,
        total_horas
    )

    for h_idx in range(total_horas):
        hora_num = h_idx + 1
        start_h = h_idx * 3600.0
        end_h = min(total_dur, (h_idx + 1) * 3600.0)
        dur_h = end_h - start_h

        if dur_h < 60.0 and h_idx > 0:
            print(f"[CORTES PROC] Bloco final muito curto ({dur_h:.1f}s), finalizando mineração.")
            break

        pasta_hora = pasta_saida_raiz / f"Hora_{hora_num:02d}"
        pasta_hora.mkdir(parents=True, exist_ok=True)
        criar_script_arrastar_bat(pasta_hora)
        criar_recriar_bat_na_pasta(pasta_hora)

        base_pct = h_idx * peso_hora

        # 1. Extração rápida de áudio mono da hora (apenas 2 segundos via seek)
        emitir_status(
            "audio_extract",
            base_pct + (peso_hora * 0.05),
            f"Extraindo áudio da Hora {hora_num}/{total_horas}...",
            f"Intervalo: {seg_para_hms(start_h)} até {seg_para_hms(end_h)} ({dur_h/60:.1f} min)",
            hora_num,
            total_horas
        )

        wav_hora = TEMP_DIR / f"{video_path.stem}_hora_{hora_num:02d}.wav"
        if not extrair_audio_mono_slice(video_path, wav_hora, start_h, dur_h):
            emitir_status("error", base_pct, f"Erro ao extrair áudio da Hora {hora_num}.", "", hora_num, total_horas)
            continue

        # 2. Análise de Picos e Whisper com Progresso em Tempo Real
        emitir_status(
            "whisper",
            base_pct + (peso_hora * 0.10),
            f"Transcrevendo falas com Whisper IA (Hora {hora_num}/{total_horas})...",
            "Mapeando vocabulário e entonação",
            hora_num,
            total_horas
        )

        def cb_whisper_hora(pct_w, current_sec):
            p_global = base_pct + (peso_hora * 0.10) + ((pct_w / 100.0) * (peso_hora * 0.35))
            emitir_status(
                "whisper",
                p_global,
                f"Transcrevendo com Whisper: {pct_w:.0f}% (Hora {hora_num}/{total_horas})",
                f"{seg_para_hms(current_sec)} de {seg_para_hms(dur_h)}",
                hora_num,
                total_horas
            )

        transcricao_raw = transcrever_audio(wav_hora, progress_callback=cb_whisper_hora)
        
        # Ajusta timestamps das falas adicionando o deslocamento start_h
        transcricao = []
        for t in transcricao_raw:
            transcricao.append({
                "start": t["start"] + start_h,
                "end": t["end"] + start_h,
                "text": t["text"]
            })

        peaks_raw = analisar_energia_db(wav_hora)
        peaks = [(p_sec + start_h, p_db) for (p_sec, p_db) in peaks_raw]

        # 3. Mineração dos 10 Melhores Momentos da Hora com o Cérebro Viral
        emitir_status(
            "mining",
            base_pct + (peso_hora * 0.48),
            f"Minerando os {cortes_por_hora} melhores momentos da Hora {hora_num}...",
            f"Analisando {len(peaks)} picos de dB e {len(transcricao)} falas",
            hora_num,
            total_horas
        )

        cortes_hora = minerar_cortes_cerebro(
            peaks=peaks,
            transcricao=transcricao,
            duracao_total=end_h,
            qtd=cortes_por_hora,
            duracao_corte=dur_corte
        )

        # Fallback de segurança se não houver cortes suficientes
        if not cortes_hora:
            cortes_hora = []
            passo = max(dur_corte * 1.5, dur_h / max(1, cortes_por_hora))
            for i in range(cortes_por_hora):
                ini_fallback = start_h + (i * passo)
                if ini_fallback + dur_corte <= end_h:
                    cortes_hora.append({
                        "start": ini_fallback,
                        "end": ini_fallback + dur_corte,
                        "duration": dur_corte,
                        "dialogue": [d for d in transcricao if ini_fallback <= d["start"] <= ini_fallback + dur_corte],
                        "score": 75.0 - i,
                        "motivo": f"Momento selecionado por cadência na Hora {hora_num}"
                    })

        # 4. Renderização e Liberação Incremental dos Cortes da Hora
        cortes_gerados_nesta_hora = []
        peso_render_corte = (peso_hora * 0.50) / max(1, len(cortes_hora))

        for c_idx, c in enumerate(cortes_hora, 1):
            pct_corte_render = base_pct + (peso_hora * 0.50) + ((c_idx - 1) * peso_render_corte)
            c_start = c["start"]
            c_dur = c["duration"]

            emitir_status(
                "rendering",
                pct_corte_render,
                f"Renderizando Corte {c_idx}/{len(cortes_hora)} da Hora {hora_num} (GPU AMF)...",
                f"Posição: {seg_para_hms(c_start)} • Score: {c.get('score', 80):.0f}",
                hora_num,
                total_horas
            )

            prefixo = f"corte_{c_idx:02d}_hora_{hora_num:02d}_[{limpar_string_arquivo(canal, 15)}]_[{limpar_string_arquivo(titulo, 25)}]"
            out_mp4 = pasta_hora / f"{prefixo}.mp4"
            out_txt = pasta_hora / f"{prefixo}.txt"
            ass_path = pasta_hora / f"{prefixo}.ass"
            srt_path = pasta_hora / f"{prefixo}.srt"

            # Rastreamento Facial YuNet
            webcam_info = ("SEM_WEBCAM", 0, 0, 0, 0)
            layout_final = layout_modo
            if layout_modo in ["AUTO", "SPLIT_PRO"]:
                webcam_info = detectar_webcam_yunet(video_path, c_start, c_dur, orig_w, orig_h)
                if webcam_info[0] in ["WEBCAM_DIREITA", "WEBCAM_ESQUERDA"]:
                    layout_final = "SPLIT_PRO"
                else:
                    layout_final = "BLUR_BACKGROUND"

            # Ganchos e Legendas MrBeast
            dialogos_corte = c.get("dialogue", [])
            hook_principal, opcoes_hooks = gerar_ganchos_virais(dialogos_corte, canal=canal, assunto=titulo)

            # Legendas com timestamps relativos ao corte
            dialogos_rel = []
            for d in dialogos_corte:
                dialogos_rel.append({
                    "start": max(0.0, d["start"] - c_start),
                    "end": min(c_dur, d["end"] - c_start),
                    "text": d["text"]
                })

            res_w = RESOLUCOES[target_res]["w"]
            res_h = RESOLUCOES[target_res]["h"]
            gerar_ass_mrbeast(dialogos_rel, hook_principal, ass_path, c_dur, res_w, res_h)
            gerar_srt_universal(dialogos_rel, srt_path)

            txt_content = gerar_texto_post_completo(
                canal=canal,
                titulo_live=titulo,
                hook_principal=hook_principal,
                opcoes_hooks=opcoes_hooks,
                c_start=c_start,
                c_dur=c_dur,
                layout_tipo=layout_final,
                arquivo_origem=str(video_path),
                dialogos=dialogos_corte,
                plataforma=plataforma,
                categoria=categoria,
                views=views,
                ranking=ranking,
                resolucao=target_res,
                fps=v_meta.get("fps", 60),
                numero_corte=c_idx
            )
            with open(out_txt, "w", encoding="utf-8") as f:
                f.write(txt_content)

            # Renderiza corte acelerado por GPU AMF
            render_ok = renderizar_video_corte(
                video_origem=video_path,
                saida_mp4=out_mp4,
                ass_path=ass_path,
                c_start=c_start,
                c_dur=c_dur,
                layout=layout_final,
                webcam_info=webcam_info,
                target_res=target_res,
                usar_ducking=False,
                musica_nome="synthwave_energy.wav",
                usar_sfx=True
            )

            if render_ok and out_mp4.exists():
                cortes_gerados_nesta_hora.append(out_mp4)
                todos_cortes_gerados.append(out_mp4)
                # NOTIFICAÇÃO IMEDIATA DO CORTE PRONTO
                emitir_corte_pronto(
                    corte_num=c_idx,
                    hora=hora_num,
                    titulo=f"Hora {hora_num} - Corte {c_idx:02d}",
                    arquivo=out_mp4.name,
                    path=str(out_mp4),
                    duracao=c_dur,
                    pasta=str(pasta_hora)
                )

        # 5. Notifica Conclusão da Hora (Acesso Imediato aos Arquivos!)
        resumo_hora = pasta_hora / "resumo_hora.txt"
        with open(resumo_hora, "w", encoding="utf-8") as f:
            f.write(f"MONITORAMENTO LIVE — HORA {hora_num:02d} DE {total_horas:02d}\n")
            f.write(f"Canal: {canal} | Jogo: {categoria} | Título: {titulo}\n")
            f.write(f"Trecho: {seg_para_hms(start_h)} até {seg_para_hms(end_h)}\n")
            f.write(f"Cortes Gerados: {len(cortes_gerados_nesta_hora)}\n")
            for c_f in cortes_gerados_nesta_hora:
                f.write(f" • {c_f.name}\n")

        emitir_hora_concluida(
            hora=hora_num,
            total_horas=total_horas,
            cortes_gerados=len(cortes_gerados_nesta_hora),
            pasta=str(pasta_hora),
            msg=f"✅ Hora {hora_num}/{total_horas} concluída! {len(cortes_gerados_nesta_hora)} cortes salvos e liberados em {pasta_hora.name}"
        )

    # 6. Finalização Geral
    sucesso_total = len(todos_cortes_gerados) > 0
    resumo_geral = pasta_saida_raiz / "resumo_geral_mineracao.txt"
    with open(resumo_geral, "w", encoding="utf-8") as f:
        f.write(f"MONITORAMENTO LIVE — RESUMO GERAL DE MINERAÇÃO EM LOTE\n")
        f.write(f"Canal: {canal} | Jogo: {categoria} | Plataforma: {plataforma}\n")
        f.write(f"Duração Total: {seg_para_hms(total_dur)}\n")
        f.write(f"Total de Horas Analisadas: {total_horas}\n")
        f.write(f"Total de Cortes Verticais 9:16 Gerados: {len(todos_cortes_gerados)}\n")
        f.write(f"Pasta Raiz: {pasta_saida_raiz}\n")

    emitir_processo_completo(
        sucesso=sucesso_total,
        total_cortes=len(todos_cortes_gerados),
        pasta=str(pasta_saida_raiz),
        original=str(video_path),
        msg=f"🎉 Mineração completa finalizada! {len(todos_cortes_gerados)} cortes virais salvos em {pasta_saida_raiz.name}"
    )
    return sucesso_total


def executar_processamento_cortes(
    video_baixado: Path,
    pasta_destino_raiz: Path,
    plataforma: str = "Twitch",
    categoria: str = "Geral",
    streamer: str = "Streamer",
    titulo: str = "Video",
    views: str = "",
    ranking: Any = "",
    modo: str = "por_hora", # "por_hora" ou "top_geral"
    cortes_por_hora: int = 10,
    target_res: str = "1080p",
    layout_modo: str = "SPLIT_PRO"
) -> Dict[str, Any]:
    """
    Coordena a organização e disparo da mineração inteligente com feedback em tempo real.
    """
    plat_clean = "Twitch" if str(plataforma).lower() == "twitch" else "Kick"
    streamer_clean = limpar_string_arquivo(streamer or "Streamer", 25)
    cat_clean = limpar_string_arquivo(categoria or "Geral", 30)
    titulo_clean = limpar_string_arquivo(titulo or "Video", 35)

    pasta_organizada = pasta_destino_raiz / plat_clean / streamer_clean / f"[{cat_clean}]_[{titulo_clean}]"
    pasta_organizada.mkdir(parents=True, exist_ok=True)

    arquivo_original_final = pasta_organizada / f"original_[{streamer_clean}]_[{titulo_clean}].mp4"
    if video_baixado.exists() and video_baixado != arquivo_original_final:
        try:
            shutil.move(str(video_baixado), str(arquivo_original_final))
        except Exception:
            shutil.copy2(str(video_baixado), str(arquivo_original_final))

    v_meta = obter_info_video(arquivo_original_final)
    duracao = v_meta.get("duration", 0.0)

    print("=" * 65, flush=True)
    print(f"🎬 MONITORAMENTO LIVE — PIPELINE DE CORTES IA", flush=True)
    print(f"Plataforma: {plat_clean} | Streamer: {streamer_clean}", flush=True)
    print(f"Jogo: {cat_clean} | Título: {titulo_clean}", flush=True)
    print(f"Duração: {duracao:.1f}s ({seg_para_hms(duracao)}) | Modo: {modo}", flush=True)
    print(f"Pasta de Saída: {pasta_organizada}", flush=True)
    print("=" * 65, flush=True)

    if duracao <= 90.0:
        # Clipe curto: renderiza como corte vertical individual completo
        sucesso = processar_clipe_curto(
            video_path=arquivo_original_final,
            pasta_saida=pasta_organizada,
            canal=streamer_clean,
            titulo=titulo_clean,
            categoria=cat_clean,
            plataforma=plat_clean,
            views=views,
            ranking=ranking,
            target_res=target_res,
            layout_modo=layout_modo
        )
    elif modo == "top_geral":
        # Mineração Top Geral (Melhores Momentos do Vídeo Todo)
        emitir_status("starting_global", 5.0, "Iniciando análise dos melhores momentos globais...", f"Total: {seg_para_hms(duracao)}", 1, 1)
        cortes = processar_video_completo(
            video_path=arquivo_original_final,
            pasta_saida=pasta_organizada,
            info_video={"canal": streamer_clean, "titulo": titulo_clean},
            qtd_cortes=cortes_por_hora,
            dur_corte=40.0,
            layout_modo=layout_modo,
            target_res=target_res
        )
        sucesso = len(cortes) > 0
        criar_script_arrastar_bat(pasta_organizada)
        emitir_processo_completo(sucesso, len(cortes), str(pasta_organizada), str(arquivo_original_final), f"Mineração concluída com {len(cortes)} cortes!")
    else:
        # Modo Padrão: Mineração em Lote por Hora (10 cortes por hora com liberação incremental imediata)
        sucesso = processar_video_por_horas(
            video_path=arquivo_original_final,
            pasta_saida_raiz=pasta_organizada,
            canal=streamer_clean,
            titulo=titulo_clean,
            categoria=cat_clean,
            plataforma=plat_clean,
            views=views,
            ranking=ranking,
            cortes_por_hora=cortes_por_hora,
            dur_corte=40.0,
            target_res=target_res,
            layout_modo=layout_modo
        )

    return {
        "sucesso": sucesso,
        "pasta_organizada": str(pasta_organizada),
        "arquivo_original": str(arquivo_original_final),
        "duracao": duracao
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Processador Automático de Cortes Virais")
    parser.add_argument("--video", required=True, help="Caminho do vídeo baixado")
    parser.add_argument("--output-dir", required=True, help="Diretório raiz de destino")
    parser.add_argument("--plataforma", default="Twitch", help="Plataforma de streaming (Twitch ou Kick)")
    parser.add_argument("--categoria", default="Geral", help="Categoria do jogo")
    parser.add_argument("--streamer", default="Streamer", help="Nome do streamer")
    parser.add_argument("--titulo", default="Clipe", help="Título do vídeo")
    parser.add_argument("--views", default="", help="Métrica de visualizações do vídeo")
    parser.add_argument("--ranking", default="", help="Posição no ranking dos mais vistos")
    parser.add_argument("--modo", default="por_hora", choices=["por_hora", "top_geral"], help="Modo de mineração")
    parser.add_argument("--cortes-por-hora", type=int, default=10, help="Quantidade de cortes por bloco de 1 hora")
    parser.add_argument("--target-res", default="1080p", help="Resolução alvo (1080p ou 2K)")
    parser.add_argument("--layout", default="SPLIT_PRO", help="Layout vertical (SPLIT_PRO, BLUR_BACKGROUND, etc.)")

    args = parser.parse_args()
    res = executar_processamento_cortes(
        video_baixado=Path(args.video),
        pasta_destino_raiz=Path(args.output_dir),
        plataforma=args.plataforma,
        categoria=args.categoria,
        streamer=args.streamer,
        titulo=args.titulo,
        views=args.views,
        ranking=args.ranking,
        modo=args.modo,
        cortes_por_hora=args.cortes_por_hora,
        target_res=args.target_res,
        layout_modo=args.layout
    )
    print(f"[RESULTADO_FINAL] {json.dumps(res, ensure_ascii=False)}", flush=True)
