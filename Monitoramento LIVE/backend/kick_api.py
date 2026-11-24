# -*- coding: utf-8 -*-
"""
Kick API Client
Acesso a categorias, clipes e transmissões ao vivo da Kick.com
Com suporte a resolução direta de m3u8/mp4
"""

import time
import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any
import yt_dlp
from .config import CURRENT_CONFIG

KICK_BASE = "https://kick.com"
KICK_STREAM_CACHE: Dict[str, Dict[str, Any]] = {}

def get_kick_headers() -> Dict[str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://kick.com/"
    }
    token = CURRENT_CONFIG.get("kick_auth_token")
    if token:
        headers["Authorization"] = f"Bearer {token.replace('Bearer ', '').strip()}"
    return headers

def buscar_clipes_jogo_kick(
    categoria_slug: str,
    filtro_periodo: str = "week",
    ordenar_por: str = "view",
    limite: int = 50
) -> Dict[str, Any]:
    """Busca os maiores clipes de uma categoria na Kick"""
    time_map = {
        "LAST_DAY": "day", "LAST_WEEK": "week", "LAST_MONTH": "month", "ALL_TIME": "all",
        "day": "day", "week": "week", "month": "month", "all": "all"
    }
    time_val = time_map.get(filtro_periodo, "week")
    
    sort_map = {
        "VIEWS_DESC": "view", "TRENDING": "view", "view": "view", "date": "date"
    }
    sort_val = sort_map.get(ordenar_por, "view")
    
    url = f"{KICK_BASE}/api/v2/categories/{categoria_slug}/clips?sort={sort_val}&time={time_val}"
    headers = get_kick_headers()
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_clips = data.get("clips", [])
            
            clipes_formatados = []
            for item in raw_clips[:limite]:
                channel = item.get("channel") or {}
                creator = item.get("creator") or {}
                cat = item.get("category") or {}
                video_url = item.get("video_url") or item.get("clip_url")
                
                clipes_formatados.append({
                    "id": item.get("id"),
                    "slug": item.get("id"),
                    "url": f"https://kick.com/{channel.get('slug', 'streamer')}?clip={item.get('id')}",
                    "stream_url": video_url,
                    "title": item.get("title") or "Clipe Kick",
                    "views": item.get("views") or item.get("view_count", 0),
                    "duration": item.get("duration", 0),
                    "created_at": item.get("created_at", ""),
                    "thumbnail": item.get("thumbnail_url", ""),
                    "language": "PT/EN",
                    "platform": "kick",
                    "game_name": cat.get("name", categoria_slug),
                    "is_mature": False,
                    "broadcaster": {
                        "id": str(channel.get("id", "")),
                        "name": channel.get("username", "Streamer"),
                        "login": channel.get("slug", ""),
                        "avatar": channel.get("profile_picture", "")
                    },
                    "curator": {
                        "name": creator.get("username", "")
                    }
                })
                
            return {
                "sucesso": True,
                "jogo": {
                    "id": categoria_slug,
                    "name": categoria_slug.replace("-", " ").title(),
                    "box_art": ""
                },
                "total": len(clipes_formatados),
                "clipes": clipes_formatados
            }
    except urllib.error.HTTPError as e:
        print(f"[KICK API HTTP {e.code}] {e}")
        return {"sucesso": False, "erro": f"Erro HTTP {e.code} da Kick", "clipes": []}
    except Exception as e:
        print(f"[KICK API ERROR] {e}")
        return {"sucesso": False, "erro": str(e), "clipes": []}

def buscar_lives_jogo_kick(categoria_slug: str, limite: int = 30) -> Dict[str, Any]:
    """Busca streamers ao vivo na categoria na Kick"""
    headers = get_kick_headers()
    lives = []
    
    # Busca em português e inglês
    for lang in ['pt', 'en', 'es']:
        url = f"{KICK_BASE}/stream/livestreams/{lang}?subcategory={categoria_slug}"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                for item in items:
                    chan = item.get("channel", {})
                    user = chan.get("user", {})
                    thumb_obj = item.get("thumbnail") or {}
                    thumb_url = thumb_obj.get("src") or ""
                    
                    lives.append({
                        "id": str(item.get("id")),
                        "title": item.get("session_title") or "Live Kick",
                        "viewers": item.get("viewer_count") or item.get("viewers", 0),
                        "created_at": item.get("created_at", ""),
                        "thumbnail": thumb_url,
                        "playback_url": chan.get("playback_url"), # URL direta HLS da transmissão ao vivo!
                        "platform": "kick",
                        "game_name": categoria_slug.replace("-", " ").title(),
                        "streamer": {
                            "id": str(chan.get("id")),
                            "name": user.get("username") or chan.get("slug", "Streamer"),
                            "login": chan.get("slug", ""),
                            "avatar": user.get("profilepic") or "",
                            "channel_url": f"https://kick.com/{chan.get('slug', '')}"
                        }
                    })
                    if len(lives) >= limite:
                        break
        except Exception as e:
            pass
        if len(lives) >= limite:
            break

    # Ordena por visualizadores
    lives.sort(key=lambda x: x.get("viewers", 0), reverse=True)

    return {
        "sucesso": True,
        "jogo": {
            "id": categoria_slug,
            "name": categoria_slug.replace("-", " ").title(),
            "box_art": ""
        },
        "total": len(lives),
        "lives": lives
    }

def buscar_top_categorias_kick(limite: int = 30) -> List[Dict[str, Any]]:
    """Busca categorias mais populares na Kick"""
    url = f"{KICK_BASE}/api/v1/subcategories"
    headers = get_kick_headers()
    resultados = []
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            for item in items[:limite]:
                banner = item.get("banner", {}).get("url") or ""
                resultados.append({
                    "id": item.get("slug"),
                    "name": item.get("name"),
                    "twitch_name": item.get("name"),
                    "kick_slug": item.get("slug"),
                    "box_art": banner,
                    "viewers": item.get("viewers", 0),
                    "badge": f"{item.get('viewers', 0):,} assistindo".replace(",", "."),
                    "tags": item.get("tags") or ["Kick Ao Vivo"]
                })
    except Exception as e:
        print(f"[KICK TOP CATEGORIES ERROR] {e}")
    return resultados

def pesquisar_categorias_kick(termo: str, limite: int = 10) -> List[Dict[str, Any]]:
    """Pesquisa subcategorias/jogos na Kick"""
    url = f"{KICK_BASE}/api/v1/subcategories"
    headers = get_kick_headers()
    resultados = []
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("data", [])
            termo_lower = termo.lower()
            
            for item in items:
                name = item.get("name", "")
                slug = item.get("slug", "")
                if termo_lower in name.lower() or termo_lower in slug:
                    banner = item.get("banner", {}).get("url") or ""
                    resultados.append({
                        "id": slug,
                        "name": name,
                        "box_art": banner,
                        "viewers": item.get("viewers", 0)
                    })
                    if len(resultados) >= limite:
                        break
    except Exception as e:
        print(f"[KICK CATEGORIES SEARCH ERROR] {e}")
    return resultados

def resolver_url_stream_kick(clip_id_ou_url: str) -> Optional[str]:
    """Resolve stream URL do clipe na Kick"""
    chave = clip_id_ou_url.split("clip=")[-1].split("/")[-1].split("?")[0]
    agora = time.time()
    
    if chave in KICK_STREAM_CACHE:
        item = KICK_STREAM_CACHE[chave]
        if item["expires_at"] > agora:
            return item["url"]
            
    if ".m3u8" in clip_id_ou_url or ".mp4" in clip_id_ou_url:
        return clip_id_ou_url
        
    target_url = clip_id_ou_url if clip_id_ou_url.startswith("http") else f"https://kick.com/video?clip={chave}"
    ydl_opts = {"quiet": True, "no_warnings": True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            stream_url = info.get("url")
            if stream_url:
                KICK_STREAM_CACHE[chave] = {
                    "url": stream_url,
                    "expires_at": agora + 7200
                }
                return stream_url
    except Exception as e:
        print(f"[KICK RESOLVE ERROR] {clip_id_ou_url}: {e}")
        
    return None
