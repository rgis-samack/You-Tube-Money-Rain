# -*- coding: utf-8 -*-
"""
FastAPI Backend Server - Monitoramento LIVE
API unificada para Twitch, Kick, Transmissões Ao Vivo (Lives), Clipes e Processador de Cortes IA
"""

import os
import sys
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

import httpx
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .config import CURRENT_CONFIG, carregar_config, salvar_config, PROJECT_DIR
from .twitch_api import (
    buscar_clipes_jogo, buscar_videos_jogo, buscar_lives_jogo, buscar_top_jogos,
    pesquisar_jogos, resolver_url_stream, resolver_live_streamlink
)
from .kick_api import (
    buscar_clipes_jogo_kick, buscar_lives_jogo_kick, buscar_top_categorias_kick,
    pesquisar_categorias_kick, resolver_url_stream_kick
)
from .download_manager import GERENCIADOR
from .studio_service import extrair_snapshots_video, listar_videos_disponiveis, resolver_caminho_video

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(
    title="Monitoramento LIVE",
    description="Interface Profissional de Monitoramento e Download de Clipes e Lives (Twitch & Kick)",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Catálogo Expandido de 24 Jogos Principais
FEATURED_GAMES = [
    {
        "id": "gta6",
        "name": "Grand Theft Auto VI",
        "twitch_name": "Grand Theft Auto VI",
        "kick_slug": "grand-theft-auto-vi",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/1867279146_IGDB-285x380.jpg",
        "badge": "Mais Esperado",
        "tags": ["Ação", "Mundo Aberto", "Tiro"]
    },
    {
        "id": "gta5",
        "name": "Grand Theft Auto V",
        "twitch_name": "Grand Theft Auto V",
        "kick_slug": "grand-theft-auto-v",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/32982_IGDB-285x380.jpg",
        "badge": "Top Streamers",
        "tags": ["GTA RP", "Ação", "Comédia"]
    },
    {
        "id": "csgo",
        "name": "Counter-Strike 2 (CS:GO)",
        "twitch_name": "Counter-Strike",
        "kick_slug": "counter-strike-2",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/32399-285x380.jpg",
        "badge": "Competitivo",
        "tags": ["FPS", "Tático", "Clutches"]
    },
    {
        "id": "cod",
        "name": "Call of Duty®: Warzone",
        "twitch_name": "Call of Duty: Warzone",
        "kick_slug": "call-of-duty-warzone",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/512710-285x380.jpg",
        "badge": "Battle Royale",
        "tags": ["FPS", "Guerra", "Warzone"]
    },
    {
        "id": "pubg",
        "name": "PUBG BATTLEGROUNDS",
        "twitch_name": "PUBG: BATTLEGROUNDS",
        "kick_slug": "pubg-battlegrounds",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/493057-285x380.jpg",
        "badge": "Sobrevivência",
        "tags": ["Battle Royale", "Estratégia"]
    },
    {
        "id": "farcry6",
        "name": "Far Cry 6",
        "twitch_name": "Far Cry 6",
        "kick_slug": "far-cry-6",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/518692_IGDB-285x380.jpg",
        "badge": "Aventura Solo",
        "tags": ["História", "Exploração"]
    },
    {
        "id": "valorant",
        "name": "VALORANT",
        "twitch_name": "VALORANT",
        "kick_slug": "valorant",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/516575-285x380.jpg",
        "badge": "Riot Games",
        "tags": ["FPS Tático", "Heróis", "Esports"]
    },
    {
        "id": "fortnite",
        "name": "Fortnite",
        "twitch_name": "Fortnite",
        "kick_slug": "fortnite",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/33214-285x380.jpg",
        "badge": "Battle Royale",
        "tags": ["Construção", "Multiplayer", "Viral"]
    },
    {
        "id": "minecraft",
        "name": "Minecraft",
        "twitch_name": "Minecraft",
        "kick_slug": "minecraft",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/27471_IGDB-285x380.jpg",
        "badge": "Sandbox",
        "tags": ["Criatividade", "Sobrevivência"]
    },
    {
        "id": "lol",
        "name": "League of Legends",
        "twitch_name": "League of Legends",
        "kick_slug": "league-of-legends",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/21779-285x380.jpg",
        "badge": "MOBA",
        "tags": ["Estratégia", "Competitivo", "Ranked"]
    },
    {
        "id": "fc25",
        "name": "EA Sports FC 25",
        "twitch_name": "EA Sports FC 25",
        "kick_slug": "ea-sports-fc-25",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/143106037-285x380.jpg",
        "badge": "Futebol",
        "tags": ["Esportes", "Ultimate Team"]
    },
    {
        "id": "apex",
        "name": "Apex Legends",
        "twitch_name": "Apex Legends",
        "kick_slug": "apex-legends",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/511224-285x380.jpg",
        "badge": "FPS Dinâmico",
        "tags": ["Battle Royale", "Movimento"]
    },
    {
        "id": "dota2",
        "name": "Dota 2",
        "twitch_name": "Dota 2",
        "kick_slug": "dota-2",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/29595-285x380.jpg",
        "badge": "Valve Esports",
        "tags": ["MOBA", "Estratégia"]
    },
    {
        "id": "roblox",
        "name": "Roblox",
        "twitch_name": "Roblox",
        "kick_slug": "roblox",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/26936-285x380.jpg",
        "badge": "Comunidade",
        "tags": ["Minigames", "RP"]
    },
    {
        "id": "wow",
        "name": "World of Warcraft",
        "twitch_name": "World of Warcraft",
        "kick_slug": "world-of-warcraft",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/18122-285x380.jpg",
        "badge": "MMORPG",
        "tags": ["Raids", "PvP", "Fantasia"]
    },
    {
        "id": "rust",
        "name": "Rust",
        "twitch_name": "Rust",
        "kick_slug": "rust",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/263490_IGDB-285x380.jpg",
        "badge": "Hardcore",
        "tags": ["Sobrevivência", "PVP", "Base"]
    },
    {
        "id": "r6",
        "name": "Tom Clancy's Rainbow Six Siege",
        "twitch_name": "Tom Clancy's Rainbow Six Siege",
        "kick_slug": "tom-clancys-rainbow-six-siege",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/460630_IGDB-285x380.jpg",
        "badge": "FPS Tático",
        "tags": ["Destruição", "Invasão"]
    },
    {
        "id": "eldenring",
        "name": "Elden Ring",
        "twitch_name": "Elden Ring",
        "kick_slug": "elden-ring",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/512953_IGDB-285x380.jpg",
        "badge": "Soulslike",
        "tags": ["RPG", "Desafio", "Mundo Aberto"]
    },
    {
        "id": "dbd",
        "name": "Dead by Daylight",
        "twitch_name": "Dead by Daylight",
        "kick_slug": "dead-by-daylight",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/491487-285x380.jpg",
        "badge": "Terror",
        "tags": ["Assassino", "Sobreviventes"]
    },
    {
        "id": "rocketleague",
        "name": "Rocket League",
        "twitch_name": "Rocket League",
        "kick_slug": "rocket-league",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/30921-285x380.jpg",
        "badge": "Carros e Bola",
        "tags": ["Futebol", "Competitivo"]
    },
    {
        "id": "justchatting",
        "name": "Just Chatting",
        "twitch_name": "Just Chatting",
        "kick_slug": "just-chatting",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/509658-285x380.jpg",
        "badge": "Conversas",
        "tags": ["IRL", "Reações", "Podcast"]
    },
    {
        "id": "overwatch2",
        "name": "Overwatch 2",
        "twitch_name": "Overwatch 2",
        "kick_slug": "overwatch-2",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/515025-285x380.jpg",
        "badge": "Hero Shooter",
        "tags": ["FPS", "Equipe", "Habilidades"]
    },
    {
        "id": "tarkov",
        "name": "Escape from Tarkov",
        "twitch_name": "Escape from Tarkov",
        "kick_slug": "escape-from-tarkov",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/491931_IGDB-285x380.jpg",
        "badge": "Hardcore Extraction",
        "tags": ["Loot", "Sobrevivência", "Tático"]
    },
    {
        "id": "rdr2",
        "name": "Red Dead Redemption 2",
        "twitch_name": "Red Dead Redemption 2",
        "kick_slug": "red-dead-redemption-2",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/493924_IGDB-285x380.jpg",
        "badge": "Faroeste Épico",
        "tags": ["História", "Mundo Aberto", "Cowboy"]
    },
    {
        "id": "dayz",
        "name": "DayZ",
        "twitch_name": "DayZ",
        "kick_slug": "dayz",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/65632_IGDB-285x380.jpg",
        "badge": "Apocalipse Zumbi",
        "tags": ["Sobrevivência", "PVP", "Militar"]
    },
    {
        "id": "cyberpunk",
        "name": "Cyberpunk 2077",
        "twitch_name": "Cyberpunk 2077",
        "kick_slug": "cyberpunk-2077",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/65876_IGDB-285x380.jpg",
        "badge": "Futurista",
        "tags": ["RPG", "Ação", "Night City"]
    },
    {
        "id": "bg3",
        "name": "Baldur's Gate 3",
        "twitch_name": "Baldur's Gate 3",
        "kick_slug": "baldurs-gate-3",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/512534-285x380.jpg",
        "badge": "GOTY",
        "tags": ["RPG", "Turnos", "Fantasia"]
    },
    {
        "id": "deadlock",
        "name": "Deadlock",
        "twitch_name": "Deadlock",
        "kick_slug": "deadlock",
        "box_art": "https://static-cdn.jtvnw.net/ttv-boxart/1614555304-285x380.jpg",
        "badge": "Novo da Valve",
        "tags": ["MOBA Shooter", "Competitivo"]
    }
]

# Modelos Pydantic
class DownloadRequest(BaseModel):
    clip_id: str
    titulo: str
    streamer: str
    jogo: str
    url: str
    platform: str = "twitch"
    thumbnail: str = ""
    views: Optional[Any] = ""
    ranking: Optional[Any] = None
    gerar_cortes: bool = False
    modo_mineracao: str = "por_hora"
    cortes_por_hora: int = 10
    layout_modo: str = "SPLIT_PRO"
    whisper_model: Optional[str] = "medium"

class BatchDownloadRequest(BaseModel):
    clips: List[DownloadRequest]
    gerar_cortes: bool = False
    modo_mineracao: str = "por_hora"
    cortes_por_hora: int = 10
    layout_modo: str = "SPLIT_PRO"
    whisper_model: Optional[str] = "medium"

class ActionPathRequest(BaseModel):
    caminho: Optional[str] = None

class SettingsUpdate(BaseModel):
    download_dir: Optional[str] = None
    twitch_auth_token: Optional[str] = None
    kick_auth_token: Optional[str] = None
    bypass_18_plus: Optional[bool] = None
    auto_cortes_padrao: Optional[bool] = None

class SnapshotsRequest(BaseModel):
    video_path: str
    qtd_frames: Optional[int] = 8

class RenderStudioRequest(BaseModel):
    video_path: str
    custom_crop: dict
    qtd_cortes: Optional[int] = 10
    dur_corte: Optional[float] = 40.0
    target_res: Optional[str] = "2K"
    gerar_legendas: Optional[bool] = True
    usar_ducking: Optional[bool] = False
    musica_nome: Optional[str] = "synthwave_energy.wav"
    usar_sfx: Optional[bool] = True
    whisper_model: Optional[str] = "medium"

@app.get("/", response_class=HTMLResponse)
async def index_page():
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Interface em inicialização... Recarregue a página em instantes.</h1>"

@app.get("/studio", response_class=HTMLResponse)
async def studio_page():
    studio_file = TEMPLATES_DIR / "studio.html"
    if studio_file.exists():
        with open(studio_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Studio em inicialização... Recarregue a página em instantes.</h1>"

@app.get("/api/studio/videos")
async def api_studio_videos():
    return {"sucesso": True, "videos": listar_videos_disponiveis()}

@app.post("/api/studio/snapshots")
async def api_studio_snapshots(req: SnapshotsRequest):
    resolved = resolver_caminho_video(req.video_path)
    if not resolved or not resolved.exists():
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")
    dados = extrair_snapshots_video(resolved, qtd_frames=req.qtd_frames or 8)
    return dados

@app.post("/api/studio/render")
async def api_studio_render(req: RenderStudioRequest):
    resolved = resolver_caminho_video(req.video_path)
    if not resolved or not resolved.exists():
        raise HTTPException(status_code=404, detail="Vídeo não encontrado.")
    
    task_id = GERENCIADOR.adicionar_tarefa_studio(
        video_path=resolved,
        custom_crop=req.custom_crop,
        qtd_cortes=req.qtd_cortes or 10,
        dur_corte=req.dur_corte or 40.0,
        target_res=req.target_res or "2K",
        gerar_legendas=req.gerar_legendas if req.gerar_legendas is not None else True,
        usar_ducking=req.usar_ducking if req.usar_ducking is not None else False,
        musica_nome=req.musica_nome or "synthwave_energy.wav",
        usar_sfx=req.usar_sfx if req.usar_sfx is not None else True,
        whisper_model=req.whisper_model or "medium"
    )
    return {"sucesso": True, "task_id": task_id}

@app.get("/api/games")
async def get_featured_games():
    """Retorna o catálogo de jogos em destaque"""
    return {"sucesso": True, "games": FEATURED_GAMES}

@app.get("/api/games/top")
async def get_top_games_dynamic(platform: str = Query("twitch", regex="^(twitch|kick)$")):
    """Busca em tempo real os jogos mais assistidos do momento na Twitch ou Kick"""
    if platform == "twitch":
        jogos = buscar_top_jogos(limite=30)
    else:
        jogos = buscar_top_categorias_kick(limite=30)
    return {"sucesso": True, "platform": platform, "games": jogos}

@app.get("/api/clips")
async def get_clips(
    platform: str = Query("twitch"),
    game: str = Query("Grand Theft Auto VI"),
    period: str = Query("LAST_WEEK"),
    sort: str = Query("VIEWS_DESC"),
    languages: Optional[str] = Query("PT"),
    limit: int = Query(50, ge=1, le=100)
):
    """Busca os clipes mais assistidos da categoria. Padrão de idioma: Português (PT)."""
    platform_str = str(platform) if not hasattr(platform, 'default') else "twitch"
    game_str = str(game) if not hasattr(game, 'default') else "Grand Theft Auto VI"
    period_str = str(period) if not hasattr(period, 'default') else "LAST_WEEK"
    sort_str = str(sort) if not hasattr(sort, 'default') else "VIEWS_DESC"
    limit_int = int(limit) if isinstance(limit, int) else 50
    
    langs_list = None
    if isinstance(languages, str) and languages.strip() and languages.strip().upper() != "ALL":
        langs_list = [l.strip().upper() for l in languages.split(",") if l.strip()]

    if platform_str == "twitch":
        resultado = buscar_clipes_jogo(
            game_name=game_str,
            filtro_periodo=period_str,
            ordenar_por=sort_str,
            idiomas=langs_list,
            limite=limit_int
        )
    else:
        slug = game_str
        for g in FEATURED_GAMES:
            if (g["name"].lower() == game_str.lower() or 
                g["twitch_name"].lower() == game_str.lower() or 
                g["kick_slug"].lower() == game_str.lower()):
                slug = g["kick_slug"]
                break
        else:
            slug = game_str.lower().replace(" ", "-").replace(":", "").replace("®", "")

        resultado = buscar_clipes_jogo_kick(
            categoria_slug=slug,
            filtro_periodo=period_str,
            ordenar_por=sort_str,
            limite=limit_int
        )

    return resultado

@app.get("/api/videos")
async def get_videos(
    platform: str = Query("twitch"),
    game: str = Query("Grand Theft Auto V"),
    sort: str = Query("VIEWS"),
    languages: Optional[str] = Query("PT"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Busca os vídeos completos e VODs mais assistidos da categoria.
    Padrão de idioma: PT (Português) para monitoramento de métricas e ranking.
    """
    platform_str = str(platform) if not hasattr(platform, 'default') else "twitch"
    game_str = str(game) if not hasattr(game, 'default') else "Grand Theft Auto V"
    sort_str = str(sort) if not hasattr(sort, 'default') else "VIEWS"
    limit_int = int(limit) if isinstance(limit, int) else 50
    
    langs_list = None
    if isinstance(languages, str) and languages.strip() and languages.strip().upper() != "ALL":
        langs_list = [l.strip().lower() for l in languages.split(",") if l.strip()]

    if platform_str == "twitch":
        resultado = buscar_videos_jogo(
            game_name=game_str,
            ordenar_por=sort_str,
            idiomas=langs_list,
            limite=limit_int
        )
    else:
        slug = game_str
        for g in FEATURED_GAMES:
            if (g["name"].lower() == game_str.lower() or 
                g["twitch_name"].lower() == game_str.lower() or 
                g["kick_slug"].lower() == game_str.lower()):
                slug = g["kick_slug"]
                break
        else:
            slug = game_str.lower().replace(" ", "-").replace(":", "").replace("®", "")
            
        resultado = buscar_clipes_jogo_kick(
            categoria_slug=slug,
            filtro_periodo="ALL_TIME",
            ordenar_por="VIEWS_DESC",
            limite=limit_int
        )

    return resultado

@app.get("/api/streams")
async def get_live_streams(
    platform: str = Query("twitch"),
    game: str = Query("Grand Theft Auto VI"),
    limit: int = Query(30, ge=1, le=60)
):
    """
    Busca quem está transmitindo ao vivo (fazendo live) deste jogo no momento!
    Permite assistir transmissões ao vivo sem interrupção.
    """
    platform_str = str(platform) if not hasattr(platform, 'default') else "twitch"
    game_str = str(game) if not hasattr(game, 'default') else "Grand Theft Auto VI"
    limit_int = int(limit) if isinstance(limit, int) else 30

    if platform_str == "twitch":
        resultado = buscar_lives_jogo(game_name=game_str, limite=limit_int)
    else:
        slug = game_str
        for g in FEATURED_GAMES:
            if (g["name"].lower() == game_str.lower() or 
                g["twitch_name"].lower() == game_str.lower() or 
                g["kick_slug"].lower() == game_str.lower()):
                slug = g["kick_slug"]
                break
        else:
            slug = game_str.lower().replace(" ", "-").replace(":", "").replace("®", "")
        resultado = buscar_lives_jogo_kick(categoria_slug=slug, limite=limit_int)

    return resultado

@app.get("/api/stream/live")
async def get_live_stream_url(
    channel: str = Query(...),
    platform: str = Query("twitch")
):
    """Resolve o fluxo de vídeo HLS ao vivo (.m3u8) para reproduzir a live no player nativo"""
    if platform == "twitch":
        stream_url = resolver_live_streamlink(channel)
        if not stream_url:
            # Fallback para embed oficial se o streamlink não estiver disponível
            return {
                "sucesso": True,
                "is_embed": True,
                "embed_url": f"https://player.twitch.tv/?channel={channel}&parent=localhost&parent=127.0.0.1&muted=false"
            }
        return {"sucesso": True, "stream_url": stream_url, "is_embed": False}
    else:
        # Kick
        return {"sucesso": True, "stream_url": channel, "is_embed": False}

@app.get("/api/search/games")
async def search_games(
    q: str = Query(..., min_length=1),
    platform: str = Query("twitch")
):
    """Pesquisa rápida de jogos e categorias"""
    if platform == "twitch":
        results = pesquisar_jogos(q, limite=12)
    else:
        results = pesquisar_categorias_kick(q, limite=12)
    return {"sucesso": True, "termo": q, "resultados": results}

@app.get("/api/stream/proxy")
async def stream_proxy(url: str = Query(...)):
    """
    Proxy de streaming HLS e vídeo para contornar restrições de CORS
    impostas pelo CloudFront da Twitch e servidores CDN externos.
    """
    client = httpx.AsyncClient(follow_redirects=True, timeout=20.0)
    try:
        req = client.build_request("GET", url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.twitch.tv/"
        })
        resp = await client.send(req, stream=True)
        
        content_type = resp.headers.get("content-type", "application/octet-stream")
        
        # Se for playlist HLS m3u8, reescreve os segmentos para passarem pelo proxy CORS
        if "mpegurl" in content_type.lower() or url.endswith(".m3u8") or ".m3u8?" in url:
            content_bytes = await resp.aread()
            await client.aclose()
            
            text = content_bytes.decode("utf-8", errors="ignore")
            base_url = url.rsplit("/", 1)[0]
            
            new_lines = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    if stripped.startswith("http://") or stripped.startswith("https://"):
                        seg_url = f"/api/stream/proxy?url={urllib.parse.quote(stripped)}"
                    else:
                        full_seg = f"{base_url}/{stripped}"
                        seg_url = f"/api/stream/proxy?url={urllib.parse.quote(full_seg)}"
                    new_lines.append(seg_url)
                else:
                    new_lines.append(line)
                    
            modified_text = "\n".join(new_lines)
            return Response(
                content=modified_text,
                media_type="application/vnd.apple.mpegurl",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, OPTIONS",
                    "Cache-Control": "no-cache"
                }
            )
            
        async def stream_generator():
            try:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()
                
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS"
        }
        if "content-length" in resp.headers:
            headers["Content-Length"] = resp.headers["content-length"]
            
        return StreamingResponse(
            stream_generator(),
            media_type=content_type,
            headers=headers
        )
    except Exception as e:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Erro no proxy de stream: {e}")

@app.get("/api/clip/stream")
async def get_clip_stream(
    url: str = Query(...),
    platform: str = Query("twitch")
):
    """
    Resolve o fluxo direto do vídeo de clipe ou VOD (sem censura)
    com roteamento CORS via proxy e fallback infalível para player embed.
    """
    embed_url = ""
    is_vod = "/videos/" in url
    
    if platform == "twitch":
        if is_vod:
            vod_id = url.split("/videos/")[-1].split("?")[0]
            embed_url = f"https://player.twitch.tv/?video={vod_id}&parent=localhost&parent=127.0.0.1&muted=false"
        else:
            clip_slug = url.split("/clip/")[-1].split("?")[0] if "/clip/" in url else url.split("/")[-1].split("?")[0]
            embed_url = f"https://clips.twitch.tv/embed?clip={clip_slug}&parent=localhost&parent=127.0.0.1&muted=false"

        stream_url = resolver_url_stream(url)
    else:
        stream_url = resolver_url_stream_kick(url)
        channel_slug = url.split("kick.com/")[-1].split("/")[0] if "kick.com/" in url else "kick"
        embed_url = f"https://player.kick.com/{channel_slug}?muted=false"

    # Se for fluxo HLS .m3u8, roteia pelo proxy CORS local para reproduzir no player nativo sem travamento
    proxied_url = ""
    if stream_url:
        if ".m3u8" in stream_url:
            proxied_url = f"/api/stream/proxy?url={urllib.parse.quote(stream_url)}"
        else:
            proxied_url = stream_url

    return {
        "sucesso": True,
        "stream_url": proxied_url or stream_url or "",
        "raw_stream_url": stream_url or "",
        "embed_url": embed_url,
        "is_embed": not bool(stream_url)
    }

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    """
    Inicia download individual com opção de gerar cortes com IA e
    organizar a pasta por categoria.
    """
    task_id = GERENCIADOR.adicionar_download(
        clip_id=req.clip_id,
        titulo=req.titulo,
        streamer=req.streamer,
        jogo=req.jogo,
        url_clipe=req.url,
        platform=req.platform,
        thumbnail=req.thumbnail,
        views=str(req.views or ""),
        ranking=req.ranking,
        gerar_cortes=req.gerar_cortes,
        modo_mineracao=req.modo_mineracao,
        cortes_por_hora=req.cortes_por_hora,
        layout_modo=req.layout_modo
    )
    msg = f"Download de '{req.titulo}' iniciado."
    if req.gerar_cortes:
        if req.modo_mineracao == "por_hora":
            msg += f" Mineração em lote ativa: gerando {req.cortes_por_hora} cortes por hora de vídeo com liberação imediata!"
        else:
            msg += f" Mineração dos {req.cortes_por_hora} melhores momentos globais ativada!"
    return {"sucesso": True, "task_id": task_id, "mensagem": msg}

@app.post("/api/download/batch")
async def start_batch_download(req: BatchDownloadRequest):
    """
    Inicia download em lote com opção de gerar cortes automáticos
    organizados por categoria para cada um deles.
    """
    task_ids = []
    for item in req.clips:
        tid = GERENCIADOR.adicionar_download(
            clip_id=item.clip_id,
            titulo=item.titulo,
            streamer=item.streamer,
            jogo=item.jogo,
            url_clipe=item.url,
            platform=item.platform,
            thumbnail=item.thumbnail,
            views=str(item.views or ""),
            ranking=item.ranking,
            gerar_cortes=req.gerar_cortes,
            modo_mineracao=req.modo_mineracao,
            cortes_por_hora=req.cortes_por_hora,
            layout_modo=req.layout_modo
        )
        task_ids.append(tid)
    return {"sucesso": True, "total": len(task_ids), "task_ids": task_ids, "gerar_cortes": req.gerar_cortes}

@app.get("/api/downloads")
async def list_downloads():
    """Retorna o status em tempo real de todas as tarefas de download e cortes"""
    tarefas = GERENCIADOR.listar_tarefas()
    pasta = str(GERENCIADOR.get_pasta_destino())
    return {"sucesso": True, "pasta_destino": pasta, "total": len(tarefas), "tarefas": tarefas}

@app.post("/api/downloads/{task_id}/open-folder")
async def open_download_folder(task_id: str, req: ActionPathRequest = ActionPathRequest()):
    ok = GERENCIADOR.abrir_na_pasta(task_id, pasta_custom=req.caminho)
    return {"sucesso": ok}

@app.post("/api/downloads/{task_id}/play-local")
async def play_downloaded_file(task_id: str, req: ActionPathRequest = ActionPathRequest()):
    ok = GERENCIADOR.reproduzir_local(task_id, arquivo_custom=req.caminho)
    return {"sucesso": ok}

@app.post("/api/downloads/{task_id}/send-to-miner")
async def send_to_miner_editor(task_id: str):
    ok = GERENCIADOR.enviar_para_minerador(task_id)
    return {"sucesso": ok}

@app.post("/api/downloads/{task_id}/cancel")
async def cancel_download_task(task_id: str):
    ok = GERENCIADOR.cancelar_download(task_id)
    return {"sucesso": ok}

@app.get("/api/settings")
async def get_settings():
    cfg = carregar_config()
    token_tw = cfg.get("twitch_auth_token", "")
    token_kc = cfg.get("kick_auth_token", "")
    return {
        "sucesso": True,
        "download_dir": cfg.get("download_dir"),
        "twitch_auth_token_set": bool(token_tw),
        "twitch_auth_token_preview": f"{token_tw[:4]}...{token_tw[-4:]}" if len(token_tw) > 8 else "",
        "kick_auth_token_set": bool(token_kc),
        "bypass_18_plus": cfg.get("bypass_18_plus", True),
        "auto_cortes_padrao": cfg.get("auto_cortes_padrao", False)
    }

@app.post("/api/settings")
async def update_settings(update: SettingsUpdate):
    cfg = carregar_config()
    if update.download_dir is not None:
        p = Path(update.download_dir)
        p.mkdir(parents=True, exist_ok=True)
        cfg["download_dir"] = str(p.resolve())
    if update.twitch_auth_token is not None:
        cfg["twitch_auth_token"] = update.twitch_auth_token.strip()
    if update.kick_auth_token is not None:
        cfg["kick_auth_token"] = update.kick_auth_token.strip()
    if update.bypass_18_plus is not None:
        cfg["bypass_18_plus"] = update.bypass_18_plus
    if update.auto_cortes_padrao is not None:
        cfg["auto_cortes_padrao"] = update.auto_cortes_padrao
        
    salvar_config(cfg)
    return {"sucesso": True, "config": cfg}
