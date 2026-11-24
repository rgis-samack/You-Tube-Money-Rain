# -*- coding: utf-8 -*-
"""
GERADOR DE LEGENDAS DINÂMICAS DE ALTA RETENÇÃO (ESTILO OPUS CLIP / MRBEAST)
- Zero Emojis nas legendas do vídeo (elimina caixas pretas e glifos corrompidos)
- Posicionamento no Terço Inferior (Alignment 2) para não obstruir gameplay / webcam
- Agrupamento ultrafluido de 2 a 3 palavras por bloco (ritmo perfeito para Shorts/TikTok)
- Temporização proporcional ao comprimento das palavras (máxima fluidez de leitura)
- Compatibilidade 100% com arquivos .TXT editáveis e recriação instantânea
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .config import hms_para_seg

def remover_todos_emojis(texto: str) -> str:
    """
    Remove completamente qualquer emoji, pictograma ou símbolo especial
    que corrompe a renderização em fontes de vídeo (como Arial Black).
    """
    if not texto:
        return ""
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010ffff"  # Todos os caracteres suplementares (emojis Unicode)
        "\u2600-\u26ff"          # Símbolos diversos
        "\u2700-\u27bf"          # Dingbats
        "\u2300-\u23ff"          # Técnicos diversos
        "\u2b50-\u2b55"          # Estrelas e círculos
        "\u200d"                 # Zero-width joiner
        "\ufe0e-\ufe0f"          # Variation selectors
        "]+",
        flags=re.UNICODE
    )
    limpo = emoji_pattern.sub("", texto)
    # Remove espaços duplos residuais
    return re.sub(r"\s+", " ", limpo).strip()

def agrupar_palavras_fluidas(palavras: List[str]) -> List[List[str]]:
    """
    Agrupa palavras em blocos fluidos de 2 a 3 palavras para leitura dinâmica perfeita.
    Evita blocos longos cansativos e nunca deixa 1 palavra isolada no final.
    """
    n = len(palavras)
    if n <= 3:
        return [palavras]
    clusters = []
    i = 0
    while i < n:
        restante = n - i
        if restante == 4:
            clusters.append(palavras[i:i+2])
            i += 2
        elif restante >= 3:
            clusters.append(palavras[i:i+3])
            i += 3
        else:
            clusters.append(palavras[i:])
            break
    return clusters

def gerar_ass_mrbeast(
    dialogos: List[Dict[str, Any]],
    hook_text: str,
    ass_path: Path,
    duracao_total: float,
    target_w: int = 1440,
    target_h: int = 2560,
    cor_destaque: str = "&H0000FFFF" # Amarelo neon de alta retenção
) -> None:
    """
    Gera legendas ASS dinâmicas no estilo MrBeast/Opus Clip:
    - Posicionamento no Terço Inferior (Alignment=2) para não atrapalhar o jogo/streamer
    - Blocos de 2 a 3 palavras com sincronia proporcional por tamanho de termo
    - Zero emojis para renderização limpa e profissional
    - Contorno preto espesso (Outline 6) e sombra zero para visual ultra-nítido
    """
    f_hook = int(target_h * 0.032) # Título do gancho no topo
    f_sub = int(target_h * 0.033)  # Tamanho ideal de leitura mobile (84px em 2K)
    
    m_v_hook = int(target_h * 0.040) # Margem superior para o gancho
    m_v_sub = int(target_h * 0.160)  # Margem inferior (410px em 2K) -> Terço Inferior, acima da UI do TikTok

    # Limpa emojis do gancho no topo
    hook_limpo = remover_todos_emojis(hook_text).upper()

    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {target_w}
PlayResY: {target_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookTopo,Arial Black,{f_hook},&H0000FFFF,&H00000000,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,6,0,8,30,30,{m_v_hook},1
Style: SubNorm,Arial Black,{f_sub},&H00FFFFFF,&H00000000,&H00000000,&H90000000,-1,0,0,0,100,100,2,0,1,6,0,2,40,40,{m_v_sub},1
Style: SubHighlight,Arial Black,{f_sub+2},{cor_destaque},&H00000000,&H00000000,&H90000000,-1,0,0,0,102,102,2,0,1,6,0,2,40,40,{m_v_sub},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [ass_header]

    # Gancho no Topo permanente (limpo de emojis)
    if hook_limpo:
        lines.append(f"Dialogue: 1,0:00:00.00,0:00:{int(duracao_total):02d}.00,HookTopo,,0,0,0,,{hook_limpo}\n")

    # Palavras-chave que ativam destaque em amarelo neon
    PALAVRAS_DESTAQUE = {
        "CARA", "MANO", "OLHA", "MORREU", "POLÍCIA", "POLICIA", "GTA", "NÃO", "NAO",
        "KKK", "DEDO", "PIA", "TIRO", "LOUCO", "MEU", "DEUS", "VAI", "ISSO", "NUNCA",
        "SALVAR", "ENTRA", "FUGIR", "BUG", "SURREAL", "JOGO", "TUDO", "AGORA"
    }

    # Processamento dinâmico das falas com fluidez proporcional
    for d in dialogos:
        ini = max(0.0, float(d.get("start", 0.0)))
        fim = min(duracao_total, float(d.get("end", ini + 1.5)))
        texto_raw = d.get("text", "").strip()
        texto_sem_emoji = remover_todos_emojis(texto_raw)
        
        if not texto_sem_emoji or fim <= ini:
            continue

        palavras = texto_sem_emoji.split()
        if not palavras:
            continue

        # Agrupamento fluido de 2 a 3 palavras por bloco
        clusters = agrupar_palavras_fluidas(palavras)
        
        # Distribuição de tempo proporcional ao comprimento dos caracteres de cada cluster
        total_chars = sum(len(" ".join(cl)) for cl in clusters)
        tempo_total_fala = fim - ini
        t_cursor = ini

        for cl in clusters:
            cl_texto = " ".join(cl).upper()
            cl_chars = max(1, len(cl_texto))
            
            dur_cl = (cl_chars / total_chars) * tempo_total_fala if total_chars > 0 else (tempo_total_fala / len(clusters))
            # Garante limites mínimos e máximos por cluster para não piscar
            dur_cl = max(0.35, dur_cl)
            
            c_ini = t_cursor
            c_fim = min(fim, c_ini + dur_cl)
            t_cursor = c_fim

            s_str = f"0:{int(c_ini//60):02d}:{c_ini%60:05.2f}"
            e_str = f"0:{int(c_fim//60):02d}:{c_fim%60:05.2f}"

            # Destaque se o bloco contiver termo de impacto ou pontuação forte
            tem_impacto = any(p.strip(".,!?") in PALAVRAS_DESTAQUE for p in cl_texto.split()) or "?" in cl_texto or "!" in cl_texto
            estilo = "SubHighlight" if tem_impacto else "SubNorm"

            lines.append(f"Dialogue: 0,{s_str},{e_str},{estilo},,0,0,0,,{cl_texto}\n")

    ass_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def parse_arquivo_txt_companion(caminho_txt: Path) -> Tuple[Dict[str, str], str, List[Dict[str, Any]]]:
    """
    Parser universal de arquivo .TXT:
    Lê os metadados, título do gancho e legendas editadas pelo usuário.
    Limpa automaticamente quaisquer emojis digitados ou colados no TXT para o vídeo.
    Suporta tanto texto com timestamps [00:00 - 00:05] quanto texto livre.
    """
    if not caminho_txt.exists():
        return {}, "", []

    with open(caminho_txt, "r", encoding="utf-8-sig") as f:
        linhas = f.readlines()

    metadados = {}
    linhas_hook = []
    linhas_legendas_brutas = []
    secao_atual = None

    for line in linhas:
        l = line.strip()
        if not l:
            continue

        if l.startswith("#"):
            match = re.match(r"#\s*([A-Z_]+)\s*:\s*(.*)", l)
            if match:
                metadados[match.group(1)] = match.group(2).strip()
            continue

        if "MÉTRICAS DO VÍDEO" in l.upper() or "METRICAS DO VIDEO" in l.upper():
            secao_atual = "METRICAS"
            continue
        elif "TITULO DO CORTE" in l.upper() or "TITULO:" in l.upper() or "GANCHO NO TOPO" in l.upper():
            secao_atual = "HOOK"
            continue
        elif "OPÇÕES ALTERNATIVAS" in l.upper() or "OPCOES ALTERNATIVAS" in l.upper():
            secao_atual = "ALT_HOOKS"
            continue
        elif "LEGENDA DO POST" in l.upper() or "LEGENDA:" in l.upper():
            secao_atual = "POST"
            continue
        elif "LEGENDAS DO V" in l.upper() or "FALAS" in l.upper() or "LEGENDAS DO CORTE" in l.upper():
            secao_atual = "LEGENDAS"
            continue
        elif (
            l.startswith("===")
            or "VOCÊ PODE EDITAR" in l.upper()
            or "VOCE PODE EDITAR" in l.upper()
            or "COPIAR E COLAR" in l.upper()
            or "DICA" in l.upper()
            or "AO SALVAR" in l.upper()
            or "RECRIAR_CORTE" in l.upper()
            or "ARRASTAR" in l.upper()
            or "CLIQUES EM" in l.upper()
            or "PARA RE-RENDERIZAR" in l.upper()
            or "METADADOS DE RENDERIZACAO" in l.upper()
        ):
            continue

        if secao_atual == "HOOK":
            linhas_hook.append(l)
        elif secao_atual == "LEGENDAS":
            linhas_legendas_brutas.append(l)

    hook_final = " ".join(linhas_hook).strip() if linhas_hook else ""
    hook_final = remover_todos_emojis(hook_final)
    dur_total = float(metadados.get("DURACAO", 40.0))

    legendas = []
    for idx, l in enumerate(linhas_legendas_brutas):
        m = re.match(r"\[?(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})\]?[:\s-]*(.*)", l)
        if m:
            s_ini = hms_para_seg(m.group(1))
            s_fim = hms_para_seg(m.group(2))
            txt = remover_todos_emojis(m.group(3).strip())
            legendas.append({"start": s_ini, "end": s_fim, "text": txt})
        else:
            n = len(linhas_legendas_brutas)
            slot = dur_total / max(1, n)
            txt = remover_todos_emojis(l)
            legendas.append({"start": idx * slot, "end": min(dur_total, (idx + 1) * slot), "text": txt})

    return metadados, hook_final, legendas

def gerar_srt_universal(dialogos: List[Dict[str, Any]], srt_path: Path):
    """Gera o arquivo de legenda no formato padrão universal .SRT para CapCut, Premiere e players."""
    lines = []
    for idx, d in enumerate(dialogos, 1):
        ini = d.get("start", 0.0)
        fim = d.get("end", ini + 1.5)
        txt = d.get("text", "").strip()
        if not txt:
            continue
        
        h_i, rem_i = divmod(int(ini), 3600)
        m_i, s_i = divmod(rem_i, 60)
        ms_i = int((ini - int(ini)) * 1000)
        
        h_f, rem_f = divmod(int(fim), 3600)
        m_f, s_f = divmod(rem_f, 60)
        ms_f = int((fim - int(fim)) * 1000)
        
        time_str = f"{h_i:02d}:{m_i:02d}:{s_i:02d},{ms_i:03d} --> {h_f:02d}:{m_f:02d}:{s_f:02d},{ms_f:03d}"
        lines.append(f"{idx}\n{time_str}\n{txt}\n\n")
        
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(srt_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
