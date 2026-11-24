# -*- coding: utf-8 -*-
"""
Twitch GraphQL Client
Acesso de alta performance a clipes, vídeos (VODs), transmissões ao vivo e categorias da Twitch
Com suporte a bypass de restrição de idade (+18), idioma padrão Português e resolução de stream direto
"""

import time
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Optional, Any
import yt_dlp
from .config import CURRENT_CONFIG

GQL_URL = "https://gql.twitch.tv/gql"
DEFAULT_CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

# Cache de URLs diretas de stream (slug -> {url, expires_at})
STREAM_URL_CACHE: Dict[str, Dict[str, Any]] = {}
LIVE_URL_CACHE: Dict[str, Dict[str, Any]] = {}

def get_headers(auth_token: Optional[str] = None) -> Dict[str, str]:
    token = auth_token or CURRENT_CONFIG.get("twitch_auth_token", "")
    client_id = CURRENT_CONFIG.get("twitch_client_id") or DEFAULT_CLIENT_ID
    headers = {
        "Client-ID": client_id,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Referer": "https://www.twitch.tv/"
    }
    if token:
        token_clean = token.replace("OAuth ", "").strip()
        headers["Authorization"] = f"OAuth {token_clean}"
    return headers

def executar_gql(query: str, variables: Optional[Dict[str, Any]] = None, auth_token: Optional[str] = None) -> Dict[str, Any]:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    headers = get_headers(auth_token)
    req = urllib.request.Request(
        GQL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print(f"[TWITCH GQL HTTP {e.code}] {error_body}")
        return {"errors": [{"message": f"HTTP {e.code}: {error_body}"}]}
    except Exception as e:
        print(f"[TWITCH GQL ERROR] {e}")
        return {"errors": [{"message": str(e)}]}

def buscar_clipes_jogo(
    game_name: str,
    filtro_periodo: str = "LAST_WEEK",
    ordenar_por: str = "VIEWS_DESC",
    idiomas: Optional[List[str]] = None,
    limite: int = 50
) -> Dict[str, Any]:
    """
    Busca os maiores clipes (cortes virais) de um determinado jogo na Twitch.
    Padrão de idioma: Português (PT) caso não especificado.
    """
    valid_filters = {"LAST_DAY", "LAST_WEEK", "LAST_MONTH", "ALL_TIME", "TRENDING"}
    if filtro_periodo not in valid_filters:
        filtro_periodo = "LAST_WEEK"
        
    valid_sorts = {"VIEWS_DESC", "TRENDING"}
    if ordenar_por not in valid_sorts:
        ordenar_por = "VIEWS_DESC"

    criteria_parts = [
        f"filter: {filtro_periodo}",
        f"sort: {ordenar_por}"
    ]
    
    # Se idioma não for informado ou for vazio, aplica Português (PT) como padrão
    if not idiomas:
        idiomas = ["PT"]

    if idiomas and "ALL" not in [i.upper() for i in idiomas]:
        langs_str = ", ".join([i.upper() for i in idiomas])
        criteria_parts.append(f"languages: [{langs_str}]")
        
    criteria_str = f"criteria: {{ {', '.join(criteria_parts)} }}"

    query = f"""
    query GetGameClips($game: String!, $first: Int!) {{
      game(name: $game) {{
        id
        name
        boxArtURL(width: 285, height: 380)
        clips(first: $first, {criteria_str}) {{
          edges {{
            node {{
              id
              slug
              url
              title
              viewCount
              durationSeconds
              createdAt
              thumbnailURL
              language
              broadcaster {{
                id
                displayName
                login
                profileImageURL(width: 70)
              }}
              curator {{
                id
                displayName
                login
              }}
            }}
          }}
        }}
      }}
    }}
    """
    
    res = executar_gql(query, {"game": game_name, "first": min(max(limite, 1), 100)})
    
    if "errors" in res and not res.get("data", {}).get("game"):
        return {"sucesso": False, "erro": res["errors"][0].get("message", "Erro ao buscar clipes"), "clipes": []}
        
    game_data = res.get("data", {}).get("game")
    if not game_data:
        return {"sucesso": False, "erro": f"Jogo '{game_name}' não encontrado na Twitch", "clipes": []}

    raw_clips = (game_data.get("clips") or {}).get("edges", []) or []
    clipes_formatados = []
    
    for idx, item in enumerate(raw_clips, 1):
        n = item.get("node", {})
        broadcaster = n.get("broadcaster") or {}
        curator = n.get("curator") or {}
        thumb = n.get("thumbnailURL") or ""
        
        clipes_formatados.append({
            "ranking": idx,
            "id": n.get("id"),
            "slug": n.get("slug"),
            "url": n.get("url") or f"https://www.twitch.tv/{broadcaster.get('login', 'streamer')}/clip/{n.get('slug')}",
            "title": n.get("title", "Sem Título"),
            "views": n.get("viewCount", 0),
            "duration": n.get("durationSeconds", 0),
            "created_at": n.get("createdAt", ""),
            "thumbnail": thumb,
            "language": n.get("language", ""),
            "platform": "twitch",
            "type": "clip",
            "game_name": game_data.get("name"),
            "is_mature": False,
            "broadcaster": {
                "id": broadcaster.get("id"),
                "name": broadcaster.get("displayName", "Streamer"),
                "login": broadcaster.get("login", ""),
                "avatar": broadcaster.get("profileImageURL", "")
            },
            "curator": {
                "name": curator.get("displayName", "")
            }
        })
        
    return {
        "sucesso": True,
        "jogo": {
            "id": game_data.get("id"),
            "name": game_data.get("name"),
            "box_art": game_data.get("boxArtURL")
        },
        "total": len(clipes_formatados),
        "clipes": clipes_formatados
    }

def buscar_videos_jogo(
    game_name: str,
    ordenar_por: str = "VIEWS",
    idiomas: Optional[List[str]] = None,
    limite: int = 50
) -> Dict[str, Any]:
    """
    Busca os vídeos completos (VODs, transmissões passadas e destaques) da categoria na Twitch.
    Permite ranquear pelos vídeos mais assistidos da história daquela categoria.
    Padrão de idioma: Português (pt).
    """
    valid_sorts = {"VIEWS", "TIME", "TRENDING"}
    sort_val = ordenar_por if ordenar_por in valid_sorts else "VIEWS"

    # Define idioma padrão como Português caso não fornecido
    if not idiomas:
        idiomas = ["pt"]
        
    langs_param = None
    if idiomas and "ALL" not in [i.upper() for i in idiomas]:
        langs_param = [i.lower() for i in idiomas]

    query = """
    query GetGameVideos($game: String!, $first: Int!, $sort: VideoSort, $languages: [String!]) {
      game(name: $game) {
        id
        name
        boxArtURL(width: 285, height: 380)
        videos(first: $first, sort: $sort, languages: $languages) {
          edges {
            node {
              id
              title
              viewCount
              lengthSeconds
              publishedAt
              previewThumbnailURL(width: 440, height: 248)
              language
              owner {
                id
                displayName
                login
                profileImageURL(width: 70)
              }
            }
          }
        }
      }
    }
    """
    
    variables = {
        "game": game_name,
        "first": min(max(limite, 1), 80),
        "sort": sort_val,
        "languages": langs_param
    }
    
    res = executar_gql(query, variables)
    
    if "errors" in res and not res.get("data", {}).get("game"):
        return {"sucesso": False, "erro": res["errors"][0].get("message", "Erro ao buscar vídeos"), "videos": []}
        
    game_data = res.get("data", {}).get("game")
    if not game_data:
        return {"sucesso": False, "erro": f"Jogo '{game_name}' não encontrado", "videos": []}

    raw_videos = (game_data.get("videos") or {}).get("edges", []) or []
    videos_formatados = []
    
    for idx, item in enumerate(raw_videos, 1):
        node = item.get("node", {})
        owner = node.get("owner") or {}
        thumb = node.get("previewThumbnailURL") or ""
        
        videos_formatados.append({
            "ranking": idx,
            "id": node.get("id"),
            "slug": node.get("id"),
            "url": f"https://www.twitch.tv/videos/{node.get('id')}",
            "title": node.get("title") or "Vídeo Sem Título",
            "views": node.get("viewCount", 0),
            "duration": node.get("lengthSeconds", 0),
            "created_at": node.get("publishedAt", ""),
            "thumbnail": thumb,
            "language": node.get("language", ""),
            "platform": "twitch",
            "type": "video",
            "game_name": game_data.get("name"),
            "is_mature": False,
            "broadcaster": {
                "id": owner.get("id"),
                "name": owner.get("displayName", "Streamer"),
                "login": owner.get("login", ""),
                "avatar": owner.get("profileImageURL", "")
            },
            "curator": {
                "name": owner.get("displayName", "")
            }
        })
        
    return {
        "sucesso": True,
        "jogo": {
            "id": game_data.get("id"),
            "name": game_data.get("name"),
            "box_art": game_data.get("boxArtURL")
        },
        "total": len(videos_formatados),
        "videos": videos_formatados
    }

def buscar_lives_jogo(game_name: str, limite: int = 30) -> Dict[str, Any]:
    """Busca transmissões ao vivo da categoria"""
    query = """
    query GetGameLiveStreams($game: String!, $first: Int!) {
      game(name: $game) {
        id
        name
        boxArtURL(width: 285, height: 380)
        streams(first: $first) {
          edges {
            node {
              id
              title
              viewersCount
              createdAt
              previewImageURL(width: 440, height: 248)
              broadcaster {
                id
                displayName
                login
                profileImageURL(width: 70)
              }
            }
          }
        }
      }
    }
    """
    res = executar_gql(query, {"game": game_name, "first": min(max(limite, 1), 60)})
    
    if "errors" in res and not res.get("data", {}).get("game"):
        return {"sucesso": False, "erro": res["errors"][0].get("message", "Erro ao buscar transmissões ao vivo"), "lives": []}
        
    game_data = res.get("data", {}).get("game")
    if not game_data:
        return {"sucesso": False, "erro": f"Jogo '{game_name}' não encontrado", "lives": []}

    raw_streams = (game_data.get("streams") or {}).get("edges", []) or []
    lives = []
    
    for item in raw_streams:
        node = item.get("node", {})
        broadcaster = node.get("broadcaster") or {}
        preview = node.get("previewImageURL") or ""
        
        lives.append({
            "id": node.get("id"),
            "title": node.get("title") or "Live Sem Título",
            "viewers": node.get("viewersCount", 0),
            "created_at": node.get("createdAt", ""),
            "thumbnail": preview,
            "platform": "twitch",
            "game_name": game_data.get("name"),
            "streamer": {
                "id": broadcaster.get("id"),
                "name": broadcaster.get("displayName", "Streamer"),
                "login": broadcaster.get("login", ""),
                "avatar": broadcaster.get("profileImageURL", ""),
                "channel_url": f"https://www.twitch.tv/{broadcaster.get('login', '')}"
            }
        })
        
    return {
        "sucesso": True,
        "jogo": {
            "id": game_data.get("id"),
            "name": game_data.get("name"),
            "box_art": game_data.get("boxArtURL")
        },
        "total": len(lives),
        "lives": lives
    }

def buscar_top_jogos(limite: int = 30) -> List[Dict[str, Any]]:
    """Busca o catálogo dinâmico com os jogos mais assistidos no momento na Twitch"""
    query = """
    query GetTopGames($first: Int!) {
      games(first: $first) {
        edges {
          node {
            id
            name
            boxArtURL(width: 285, height: 380)
            viewersCount
          }
        }
      }
    }
    """
    res = executar_gql(query, {"first": limite})
    jogos = []
    try:
        edges = res.get("data", {}).get("games", {}).get("edges", [])
        for e in edges:
            n = e.get("node", {})
            jogos.append({
                "id": n.get("id"),
                "name": n.get("name"),
                "twitch_name": n.get("name"),
                "kick_slug": n.get("name", "").lower().replace(" ", "-").replace(":", "").replace("®", ""),
                "box_art": n.get("boxArtURL"),
                "viewers": n.get("viewersCount", 0),
                "badge": f"{n.get('viewersCount', 0):,} assistindo".replace(",", "."),
                "tags": ["Ao Vivo", "Popular"]
            })
    except Exception as e:
        print(f"[TWITCH TOP GAMES ERROR] {e}")
    return jogos

def pesquisar_jogos(termo: str, limite: int = 10) -> List[Dict[str, Any]]:
    """Pesquisa categorias e jogos na Twitch"""
    query = """
    query SearchGames($query: String!, $first: Int!) {
      searchCategories(query: $query, first: $first) {
        edges {
          node {
            id
            name
            boxArtURL(width: 140, height: 190)
          }
        }
      }
    }
    """
    res = executar_gql(query, {"query": termo, "first": limite})
    jogos = []
    try:
        edges = res.get("data", {}).get("searchCategories", {}).get("edges", [])
        for e in edges:
            node = e.get("node", {})
            jogos.append({
                "id": node.get("id"),
                "name": node.get("name"),
                "box_art": node.get("boxArtURL")
            })
    except Exception as e:
        print(f"[TWITCH SEARCH ERROR] {e}")
    return jogos

def resolver_url_stream(slug_ou_url: str) -> Optional[str]:
    """Resolve a URL direta do vídeo MP4 (1080p/Source) sem restrições de idade"""
    chave = slug_ou_url.split("/")[-1].split("?")[0]
    agora = time.time()
    
    if chave in STREAM_URL_CACHE:
        item = STREAM_URL_CACHE[chave]
        if item["expires_at"] > agora:
            return item["url"]
            
    target_url = slug_ou_url if slug_ou_url.startswith("http") else f"https://clips.twitch.tv/{slug_ou_url}"
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best[ext=mp4]/best"
    }
    
    token = CURRENT_CONFIG.get("twitch_auth_token")
    if token:
        ydl_opts["http_headers"] = {"Authorization": f"OAuth {token.replace('OAuth ', '').strip()}"}
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            stream_url = info.get("url")
            if stream_url:
                STREAM_URL_CACHE[chave] = {
                    "url": stream_url,
                    "expires_at": agora + 7200
                }
                return stream_url
    except Exception as e:
        print(f"[TWITCH RESOLVE ERROR] {slug_ou_url}: {e}")
        
    return None

def resolver_live_streamlink(canal_login: str) -> Optional[str]:
    """Resolve o fluxo de vídeo HLS direto (.m3u8) da live ao vivo sem anúncios"""
    canal_clean = canal_login.replace("https://www.twitch.tv/", "").replace("https://twitch.tv/", "").strip("/ ")
    agora = time.time()
    
    if canal_clean in LIVE_URL_CACHE:
        item = LIVE_URL_CACHE[canal_clean]
        if item["expires_at"] > agora:
            return item["url"]

    cmd = ["streamlink", "--stream-url", f"https://twitch.tv/{canal_clean}", "best"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if res.returncode == 0 and res.stdout.strip().startswith("http"):
            stream_url = res.stdout.strip()
            LIVE_URL_CACHE[canal_clean] = {
                "url": stream_url,
                "expires_at": agora + 300
            }
            return stream_url
    except Exception as e:
        print(f"[STREAMLINK LIVE RESOLVE ERROR] {canal_clean}: {e}")
        
    return None
