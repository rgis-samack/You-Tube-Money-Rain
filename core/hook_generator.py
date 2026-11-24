# -*- coding: utf-8 -*-
"""
GERADOR DE GANCHOS VIRAIS, TÍTULOS E COPYWRITING MULTIPLATAFORMA
Analisa diálogos, áudio, categoria e nome do arquivo para classificar o nicho (Música, Podcast, Educativo, Games ou Geral).
Gera análise detalhada do enquadramento (crop) e pacotes otimizados para YouTube Shorts, TikTok e Kwai
com rotação de títulos, descrições e hashtags filtradas por corte.
"""

import re
from typing import List, Dict, Any, Tuple
from core.content_classifier import (
    identificar_nicho_conteudo,
    descrever_enquadramento_crop,
    extrair_entidade_e_titulo,
    gerar_pacote_multiplataforma,
    filtrar_hashtags_dinamicas
)

def gerar_ganchos_virais(
    dialogos: List[Dict[str, Any]],
    canal: str = "Streamer",
    assunto: str = "Geral"
) -> Tuple[str, List[str]]:
    """
    Gera o gancho principal e opções de ganchos alternativos adaptados ao nicho e às falas transcritas.
    """
    nicho = identificar_nicho_conteudo(assunto, canal)
    artista, tema = extrair_entidade_e_titulo(assunto if assunto != "Geral" else canal)
    texto_completo = " ".join(d.get("text", "") for d in dialogos).lower()
    
    # 1. Tenta extrair a frase de maior impacto falada
    gancho_fala = None
    if dialogos:
        candidatas = [d["text"].strip() for d in dialogos if 4 <= len(d["text"].split()) <= 8]
        if candidatas:
            melhor = candidatas[0]
            clean = re.sub(r"[^\w\s\?!]", "", melhor).strip().upper()
            if len(clean) > 8:
                gancho_fala = clean

    opcoes = []
    if gancho_fala:
        opcoes.append(gancho_fala)
        
    if "MUSICA" in nicho:
        opcoes.append(f"{artista.upper()} - MOMENTO MAIS EMOCIONANTE DO SHOW!")
        opcoes.append(f"ESSA MÚSICA MACHUCA O CORAÇÃO! 💔 | {artista}")
        opcoes.append(f"QUEM NUNCA SOFREU OUVINDO ESSA? 🎶")
        opcoes.append(f"O REFRÃO QUE FEZ TODO MUNDO CANTAR JUNTO!")
    elif "CIENCIA" in nicho:
        opcoes.append(f"O SACANI EXPLICOU ISSO DE UMA FORMA SURREAL! 🌌")
        opcoes.append(f"O MISTÉRIO DO UNIVERSO QUE A CIÊNCIA DESCOBRIU!")
        opcoes.append(f"VOCÊ SABIA DISSO?! A VERDADE DO NOSSO ESPAÇO!")
    elif "HISTORIA" in nicho or "GUERRA" in nicho:
        opcoes.append(f"O RELATO REAL DO FRONT QUE NINGUÉM MOSTRA! 🪖")
        opcoes.append(f"A DURA REALIDADE DO COMBATE NA UCRÂNIA!")
        opcoes.append(f"ELE CONTOU O QUE REALMENTE ACONTECE NA GUERRA!")
    elif "PODCAST" in nicho:
        opcoes.append(f"A REVELAÇÃO QUE DEIXOU TODO MUNDO SEM PALAVRAS!")
        opcoes.append(f"VOCÊ CONCORDA COM ISSO?! O DEBATE PEGOU FOGO!")
        opcoes.append(f"A HISTÓRIA QUE NUNCA TINHA SIDO CONTADA ANTES!")
    elif "GAMES" in nicho:
        if any(k in texto_completo for k in ["policia", "tiro", "fuga"]):
            opcoes.append(f"A FUGA MAIS INSANA DO {artista.upper()}!")
        else:
            opcoes.append(f"A JOGADA MAIS SURREAL DO {artista.upper()}!")
        opcoes.append(f"A REAÇÃO DELE FOI A MELHOR DA LIVE!")
        opcoes.append(f"VOCÊ NÃO VAI ACREDITAR NO QUE ROLOU!")
    elif "CINEMA" in nicho or "FILME" in nicho:
        opcoes.append(f"A CENA MAIS ÉPICA DA HISTÓRIA DO CINEMA! 🎬")
        opcoes.append(f"O MOMENTO QUE FEZ A SALA INTEIRA GRITAR! 🔥")
        opcoes.append(f"IMPOSSÍVEL NÃO SE ARREPIAR COM ESSA CENA! 😱")
        opcoes.append(f"O SACRIFÍCIO MAIS EMOCIONANTE DE TODOS! 💔")
    else:
        opcoes.append(f"ESSE MOMENTO VAI MUDAR SEU DIA!")
        opcoes.append(f"VOCÊ NÃO VAI ACREDITAR NO QUE ACONTECEU!")
        opcoes.append(f"O FINAL DESSE VÍDEO FOI SURPREENDENTE!")

    vistos = set()
    opcoes_finais = []
    for op in opcoes:
        if op not in vistos:
            vistos.add(op)
            opcoes_finais.append(op)
            
    hook_principal = opcoes_finais[0]
    return hook_principal, opcoes_finais[:4]

def gerar_texto_post_completo(
    canal: str,
    titulo_live: str,
    hook_principal: str,
    opcoes_hooks: List[str],
    dialogos: List[Dict[str, Any]],
    c_start: float = 0.0,
    c_dur: float = 40.0,
    layout_tipo: str = "FULL_BLEED_ZOOM",
    arquivo_origem: str = "",
    plataforma: str = "Twitch",
    categoria: str = "Geral",
    views: Any = "",
    ranking: Any = "",
    resolucao: str = "1080p",
    fps: Any = "60",
    numero_corte: int = 1,
    **kwargs
) -> str:
    """
    Gera o arquivo TXT estruturado e compatível com o parser de recriação via CMD (ARRASTAR_TXT_AQUI_PARA_EDITAR.bat),
    trazendo a análise detalhada do enquadramento/crop e cópias personalizadas para YouTube Shorts, TikTok e Kwai
    com rotação garantida de títulos, descrições e hashtags filtradas por corte.
    """
    m_ini, s_ini = int(c_start // 60), int(c_start % 60)
    c_fim = c_start + c_dur
    m_fim, s_fim = int(c_fim // 60), int(c_fim % 60)
    
    # Gera dados de nicho e plataformas com rotação dinâmica
    nome_ref = arquivo_origem if arquivo_origem else titulo_live
    pacote = gerar_pacote_multiplataforma(
        titulo_ou_arquivo=nome_ref,
        categoria=categoria,
        layout_tipo=layout_tipo,
        c_start=c_start,
        c_dur=c_dur,
        numero_corte=numero_corte
    )
    
    info_crop = pacote["info_crop"]
    nicho = pacote["nicho"]
    
    txt_lines = [
        f"# METADADOS DE RENDERIZACAO (NAO ALTERE ESTAS LINHAS)",
        f"# PLATAFORMA: {plataforma}",
        f"# CANAL: {canal}",
        f"# CATEGORIA: {categoria}",
        f"# TITULO_LIVE: {titulo_live}",
        f"# ARQUIVO_ORIGEM: {arquivo_origem}",
        f"# INICIO_CORTE: {c_start:.2f}",
        f"# DURACAO: {c_dur:.2f}",
        f"# TIPO: {layout_tipo}",
        f"# VIEWS: {views}",
        f"# RANKING: {ranking}",
        f"",
        f"====================================================================",
        f"📊 MÉTRICAS DO VÍDEO MONITORADO ({plataforma.upper()}):",
        f"====================================================================",
        f"• Plataforma de Origem: {plataforma}",
        f"• Nicho Identificado: {nicho}",
        f"• Streamer / Canal / Artista: {pacote['artista']}",
        f"• Categoria / Tema: {pacote['tema']}",
        f"• Título Original: {titulo_live}",
        f"• Corte: #{numero_corte:02d}",
        f"• Posição no Ranking: {f'#{ranking} Mais Visto' if ranking else 'Destaque'}",
        f"• Visualizações: {views if views else 'Monitorado via Live'}",
        f"• Duração do Corte: {c_dur:.1f} segundos (Trecho: {m_ini:02d}:{s_ini:02d} até {m_fim:02d}:{s_fim:02d})",
        f"• Resolução de Saída: {resolucao} @ {fps}fps (GPU AMF Vertical 9:16)",
        f"",
        f"====================================================================",
        f"🎬 ANÁLISE DE ENQUADRAMENTO E CROP (9:16 VERTICAL):",
        f"====================================================================",
        f"• Layout Aplicado: {info_crop['nome']}",
        f"• Proporção: {info_crop['proporcao']}",
        f"• Área Cortada (Crop): {info_crop['area_crop']}",
        f"• Dinâmica Visual: {info_crop['detalhes']}",
        f"",
        f"====================================================================",
        f"TITULO DO CORTE (GANCHO NO TOPO DO VIDEO):",
        f"====================================================================",
        f"{hook_principal}",
        f"",
        f"OPÇÕES ALTERNATIVAS DE TÍTULOS (SE QUISER TROCAR, COPIE UMA ABAIXO PARA CIMA):",
    ]
    for idx, op in enumerate(opcoes_hooks, 1):
        txt_lines.append(f"  Opção {idx}: {op}")
    
    txt_lines.extend([
        f"",
        f"====================================================================",
        f"1. YOUTUBE SHORTS (TÍTULO < 50 CARACTERES + DESCRIÇÃO SEO):",
        f"====================================================================",
        f"TÍTULO DO SHORTS: {pacote['shorts']['titulo']}",
        f"",
        f"DESCRIÇÃO / COPY:",
        f"{pacote['shorts']['descricao']}",
        f"",
        f"====================================================================",
        f"2. TIKTOK (COPY DE RETENÇÃO + CTA DE COMENTÁRIOS + TAGS):",
        f"====================================================================",
        f"{pacote['tiktok']['copy']}",
        f"",
        f"====================================================================",
        f"3. KWAI (APELO EMOCIONAL / STATUS WHATSAPP + TAGS):",
        f"====================================================================",
        f"{pacote['kwai']['copy']}",
        f"",
        f"====================================================================",
        f"LEGENDAS DO VÍDEO (VOCÊ PODE EDITAR QUALQUER PALAVRA LIVREMENTE):",
        f"Dica 1: Edite falas erradas, adicione emojis ou mude o tempo das frases.",
        f"Dica 2: Para re-renderizar, basta arrastar este arquivo .txt para o CMD",
        f"        ou dar dois cliques em 'ARRASTAR_TXT_AQUI_PARA_EDITAR.bat'!",
        f"====================================================================",
    ])

    if dialogos:
        for d in dialogos:
            rel_ini = max(0.0, d.get("start", 0.0) - c_start)
            rel_fim = min(c_dur, d.get("end", rel_ini + 1.5) - c_start)
            dm_s, ds_s = int(rel_ini // 60), int(rel_ini % 60)
            dm_e, ds_e = int(rel_fim // 60), int(rel_fim % 60)
            txt_lines.append(f"[{dm_s:02d}:{ds_s:02d} - {dm_e:02d}:{ds_e:02d}] {d.get('text', '').strip()}")
    else:
        txt_lines.append(f"[00:00 - 00:{int(c_dur):02d}] {hook_principal}")

    return "\n".join(txt_lines) + "\n"
