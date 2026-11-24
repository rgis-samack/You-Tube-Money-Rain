# -*- coding: utf-8 -*-
"""
Gerenciador de Downloads Concorrente para Clipes e Vídeos de Twitch e Kick
Com suporte a:
1. Organização por Plataforma > Streamer > Conteúdo
2. Feedback e streaming de etapas em tempo real (Download, Whisper, YuNet, AMF, Legendas)
3. Mineração em Lote por Hora (10 cortes por hora de vídeo com acesso imediato aos arquivos)
4. Cancelamento instantâneo via taskkill de subprocessos
"""

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
import re
import time
import json
import shutil
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from .config import CURRENT_CONFIG, carregar_config, PROJECT_DIR

DIR_MONITORAMENTO = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

def sanitizar_nome(texto: str, max_len: int = 40) -> str:
    s = re.sub(r'[\\/*?:"<>|]', "", str(texto)).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:max_len]

class GerenciadorDownloads:
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tarefas: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        
    def get_pasta_destino(self) -> Path:
        cfg = carregar_config()
        caminho = Path(cfg.get("download_dir", ""))
        if not caminho.exists():
            try:
                caminho.mkdir(parents=True, exist_ok=True)
            except Exception:
                caminho = DIR_MONITORAMENTO / "downloads"
                caminho.mkdir(parents=True, exist_ok=True)
        return caminho

    def _preparar_tarefa_publica(self, tarefa: Dict[str, Any]) -> Dict[str, Any]:
        """Copia o dicionário da tarefa removendo objetos não serializáveis como Popen."""
        copia = dict(tarefa)
        copia.pop("processo", None)
        return copia

    def listar_tarefas(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [self._preparar_tarefa_publica(t) for t in list(self.tarefas.values())[::-1]]

    def obter_status_tarefa(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            tarefa = self.tarefas.get(task_id)
            return self._preparar_tarefa_publica(tarefa) if tarefa else None

    def adicionar_download(
        self,
        clip_id: str,
        titulo: str,
        streamer: str,
        jogo: str,
        url_clipe: str,
        platform: str = "twitch",
        thumbnail: str = "",
        views: Any = "",
        ranking: Any = None,
        gerar_cortes: bool = False,
        modo_mineracao: str = "por_hora",
        cortes_por_hora: int = 10,
        layout_modo: str = "SPLIT_PRO"
    ) -> str:
        task_id = f"{platform}_{clip_id}"
        
        with self.lock:
            if task_id in self.tarefas and self.tarefas[task_id]["status"] in ["queued", "downloading", "processing_cuts"]:
                return task_id
                
            streamer_clean = sanitizar_nome(streamer or "Streamer", 20)
            titulo_clean = sanitizar_nome(titulo or "Video", 35)

            pasta_base = self.get_pasta_destino()
            pasta_temp_download = pasta_base / "temp_downloads"
            pasta_temp_download.mkdir(parents=True, exist_ok=True)
            arquivo_temporario = pasta_temp_download / f"temp_{streamer_clean}_{titulo_clean}.mp4"
            
            tarefa = {
                "id": task_id,
                "clip_id": clip_id,
                "titulo": titulo,
                "streamer": streamer,
                "jogo": jogo,
                "url": url_clipe,
                "platform": platform,
                "thumbnail": thumbnail,
                "views": str(views or ""),
                "ranking": ranking,
                "gerar_cortes": gerar_cortes,
                "modo_mineracao": modo_mineracao,
                "cortes_por_hora": cortes_por_hora,
                "layout_modo": layout_modo,
                "status": "queued",
                "stage": "queued",
                "progress": 0,
                "speed": "--",
                "eta": "--",
                "total_bytes": 0,
                "downloaded_bytes": 0,
                "detalhe_status": "Na fila de downloads...",
                "caminho_arquivo": str(arquivo_temporario),
                "pasta_organizada": "",
                "cortes_prontos": [],
                "horas_concluidas": [],
                "logs": [],
                "processo": None,
                "cortes_gerados": False,
                "erro": "",
                "created_at": time.time()
            }
            self.tarefas[task_id] = tarefa

        self.executor.submit(self._executar_download, task_id)
        return task_id

    def _executar_download(self, task_id: str):
        with self.lock:
            tarefa = self.tarefas.get(task_id)
            if not tarefa:
                return
            tarefa["status"] = "downloading"
            tarefa["stage"] = "downloading"
            tarefa["detalhe_status"] = "Iniciando download com yt-dlp..."
            
        caminho_temp = Path(tarefa["caminho_arquivo"])
        url = tarefa["url"]
        gerar_cortes = tarefa.get("gerar_cortes", False)
        
        def ydl_progress_hook(d):
            if tarefa.get("status") == "cancelled":
                raise Exception("Cancelado pelo usuário")

            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0
                
                pct = 0.0
                if total > 0:
                    pct = round((downloaded / total) * 100.0, 1)
                elif "_percent_str" in d:
                    try:
                        clean_pct = d["_percent_str"].replace("%", "").strip()
                        pct = float(clean_pct)
                    except Exception:
                        pct = 50.0
                        
                speed_str = f"{speed / (1024*1024):.1f} MB/s" if speed else "--"
                eta_str = f"{int(eta)}s" if eta else "--"
                
                # Se for gerar cortes, o download ocupa os primeiros 20% da barra geral
                progresso_geral = round(pct * 0.20, 1) if gerar_cortes else pct

                with self.lock:
                    tarefa["progress"] = progresso_geral
                    tarefa["speed"] = speed_str
                    tarefa["eta"] = eta_str
                    tarefa["total_bytes"] = total
                    tarefa["downloaded_bytes"] = downloaded
                    tarefa["detalhe_status"] = f"Baixando vídeo original: {pct:.1f}% ({speed_str}) • Restante: {eta_str}"

        ydl_opts = {
            "outtmpl": str(caminho_temp.with_suffix("")),
            "format": "best[ext=mp4]/best",
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [ydl_progress_hook],
            "merge_output_format": "mp4",
        }
        
        cfg = carregar_config()
        token = cfg.get("twitch_auth_token")
        if "twitch.tv" in url and token:
            ydl_opts["http_headers"] = {"Authorization": f"OAuth {token.replace('OAuth ', '').strip()}"}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            if not caminho_temp.exists():
                prefix = caminho_temp.stem
                encontrados = list(caminho_temp.parent.glob(f"{prefix}*"))
                if encontrados:
                    caminho_temp = encontrados[0]

            plat_clean = "Twitch" if str(tarefa.get("platform", "twitch")).lower() == "twitch" else "Kick"
            streamer_clean = sanitizar_nome(tarefa["streamer"] or "Streamer", 25)
            cat_clean = sanitizar_nome(tarefa["jogo"] or "Geral", 30)
            titulo_clean = sanitizar_nome(tarefa["titulo"] or "Video", 35)
            pasta_raiz = self.get_pasta_destino()

            # Cria pasta da plataforma e dentro dela a pasta do streamer
            pasta_streamer = pasta_raiz / plat_clean / streamer_clean
            pasta_streamer.mkdir(parents=True, exist_ok=True)

            if gerar_cortes:
                # 1. Move para a pasta organizada do conteúdo
                pasta_video_organizada = pasta_streamer / f"[{cat_clean}]_[{titulo_clean}]"
                pasta_video_organizada.mkdir(parents=True, exist_ok=True)
                arquivo_orig_final = pasta_video_organizada / f"original_[{streamer_clean}]_[{titulo_clean}].mp4"

                if caminho_temp.exists():
                    shutil.move(str(caminho_temp), str(arquivo_orig_final))

                with self.lock:
                    tarefa["status"] = "processing_cuts"
                    tarefa["stage"] = "starting_ia"
                    tarefa["progress"] = 20.0
                    tarefa["speed"] = "Iniciando IA..."
                    tarefa["eta"] = "Processando"
                    tarefa["caminho_arquivo"] = str(arquivo_orig_final)
                    tarefa["pasta_organizada"] = str(pasta_video_organizada)
                    tarefa["detalhe_status"] = "Download finalizado! Inicializando Cortes IA e GPU AMF..."

                # 2. Dispara processador de cortes via Popen com leitura linha-a-linha de stdout
                script_processor = DIR_MONITORAMENTO / "backend" / "cortes_processor.py"
                cmd = [
                    str(VENV_PYTHON), "-u", str(script_processor),
                    "--video", str(arquivo_orig_final),
                    "--output-dir", str(pasta_raiz),
                    "--plataforma", plat_clean,
                    "--categoria", cat_clean,
                    "--streamer", streamer_clean,
                    "--titulo", titulo_clean,
                    "--views", str(tarefa.get("views") or ""),
                    "--ranking", str(tarefa.get("ranking") or ""),
                    "--modo", str(tarefa.get("modo_mineracao") or "por_hora"),
                    "--cortes-por-hora", str(tarefa.get("cortes_por_hora") or 10),
                    "--layout", str(tarefa.get("layout_modo") or "SPLIT_PRO")
                ]

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                with self.lock:
                    tarefa["processo"] = proc

                # Loop de leitura e parsing de eventos em tempo real
                for raw_line in iter(proc.stdout.readline, ""):
                    line = raw_line.strip()
                    if not line:
                        continue

                    with self.lock:
                        tarefa["logs"].append(line)
                        if len(tarefa["logs"]) > 25:
                            tarefa["logs"].pop(0)

                    if "[STATUS_JSON]" in line:
                        try:
                            idx = line.find("[STATUS_JSON]") + len("[STATUS_JSON]")
                            data = json.loads(line[idx:].strip())
                            with self.lock:
                                tarefa["stage"] = data.get("stage", "processing_cuts")
                                p_ia = data.get("pct", 0.0)
                                # 20% a 98% da barra geral
                                tarefa["progress"] = round(20.0 + (p_ia * 0.78), 1)
                                tarefa["detalhe_status"] = data.get("msg", "")
                                if data.get("detail"):
                                    tarefa["speed"] = data.get("detail")
                        except Exception:
                            pass

                    elif "[CUT_READY]" in line:
                        try:
                            idx = line.find("[CUT_READY]") + len("[CUT_READY]")
                            data = json.loads(line[idx:].strip())
                            with self.lock:
                                tarefa["cortes_prontos"].append(data)
                                tarefa["pasta_organizada"] = data.get("pasta", tarefa["pasta_organizada"])
                                tarefa["detalhe_status"] = f"✅ Novo corte pronto: {data.get('titulo')}"
                        except Exception:
                            pass

                    elif "[HOUR_COMPLETED]" in line:
                        try:
                            idx = line.find("[HOUR_COMPLETED]") + len("[HOUR_COMPLETED]")
                            data = json.loads(line[idx:].strip())
                            with self.lock:
                                tarefa["horas_concluidas"].append(data)
                                tarefa["pasta_organizada"] = data.get("pasta", tarefa["pasta_organizada"])
                                tarefa["detalhe_status"] = data.get("msg", "")
                        except Exception:
                            pass

                    elif "[PROCESS_COMPLETED]" in line:
                        try:
                            idx = line.find("[PROCESS_COMPLETED]") + len("[PROCESS_COMPLETED]")
                            data = json.loads(line[idx:].strip())
                            with self.lock:
                                tarefa["status"] = "completed"
                                tarefa["stage"] = "completed"
                                tarefa["progress"] = 100
                                tarefa["speed"] = "Cortes Prontos!"
                                tarefa["eta"] = "Concluído"
                                tarefa["detalhe_status"] = data.get("msg", "Mineração e cortes 100% concluídos!")
                                tarefa["cortes_gerados"] = True
                        except Exception:
                            pass

                proc.wait()

                with self.lock:
                    if tarefa.get("status") not in ["cancelled", "completed"]:
                        if proc.returncode == 0:
                            tarefa["status"] = "completed"
                            tarefa["stage"] = "completed"
                            tarefa["progress"] = 100
                            tarefa["speed"] = "Pronto!"
                            tarefa["eta"] = "0s"
                            tarefa["detalhe_status"] = f"Concluído com sucesso! {len(tarefa.get('cortes_prontos', []))} cortes gerados."
                            tarefa["cortes_gerados"] = True
                        else:
                            tarefa["status"] = "error"
                            tarefa["stage"] = "error"
                            tarefa["detalhe_status"] = "Erro durante o processamento de cortes IA."

            else:
                # O usuário optou por NÃO fazer cortes: salva diretamente dentro da pasta do streamer
                arquivo_final = pasta_streamer / f"[{cat_clean}]_[{titulo_clean}].mp4"

                if caminho_temp.exists():
                    shutil.move(str(caminho_temp), str(arquivo_final))

                with self.lock:
                    tarefa["status"] = "completed"
                    tarefa["stage"] = "completed"
                    tarefa["progress"] = 100
                    tarefa["speed"] = "Baixado"
                    tarefa["eta"] = "0s"
                    tarefa["caminho_arquivo"] = str(arquivo_final)
                    tarefa["pasta_organizada"] = str(pasta_streamer)
                    tarefa["detalhe_status"] = f"Download concluído! Arquivo salvo em {pasta_streamer.name}"
                    tarefa["cortes_gerados"] = False

            print(f"[DOWNLOAD + ORGANIZAÇÃO OK] {tarefa.get('caminho_arquivo')}")
            
        except Exception as e:
            with self.lock:
                if tarefa.get("status") != "cancelled":
                    tarefa["status"] = "error"
                    tarefa["stage"] = "error"
                    tarefa["erro"] = str(e)
                    tarefa["detalhe_status"] = f"Erro: {str(e)}"
            print(f"[DOWNLOAD ERRO] {task_id}: {e}")

    def cancelar_download(self, task_id: str) -> bool:
        with self.lock:
            tarefa = self.tarefas.get(task_id)
            if not tarefa:
                return False
            tarefa["status"] = "cancelled"
            tarefa["stage"] = "cancelled"
            tarefa["detalhe_status"] = "Operação cancelada pelo usuário."
            
            proc = tarefa.get("processo")
            if proc and proc.poll() is None:
                try:
                    subprocess.run(f"taskkill /F /T /PID {proc.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            return True

    def abrir_na_pasta(self, task_id: str, pasta_custom: Optional[str] = None) -> bool:
        if pasta_custom and Path(pasta_custom).exists():
            subprocess.Popen(f'explorer.exe "{pasta_custom}"', shell=True)
            return True

        tarefa = self.obter_status_tarefa(task_id)
        if not tarefa: return False
        
        pasta_org = Path(tarefa.get("pasta_organizada", ""))
        caminho_arq = Path(tarefa.get("caminho_arquivo", ""))
        
        if pasta_org.exists():
            subprocess.Popen(f'explorer.exe "{pasta_org}"', shell=True)
            return True
        elif caminho_arq.exists():
            subprocess.Popen(f'explorer.exe /select,"{caminho_arq}"', shell=True)
            return True
        elif caminho_arq.parent.exists():
            subprocess.Popen(f'explorer.exe "{caminho_arq.parent}"', shell=True)
            return True
        return False

    def reproduzir_local(self, task_id: str, arquivo_custom: Optional[str] = None) -> bool:
        if arquivo_custom and Path(arquivo_custom).exists():
            os.startfile(str(arquivo_custom))
            return True

        tarefa = self.obter_status_tarefa(task_id)
        if not tarefa: return False
        caminho = Path(tarefa.get("caminho_arquivo", ""))
        if caminho.exists():
            os.startfile(str(caminho))
            return True
        return False

    def enviar_para_minerador(self, task_id: str) -> bool:
        tarefa = self.obter_status_tarefa(task_id)
        if not tarefa: return False
        caminho = Path(tarefa.get("caminho_arquivo", ""))
        if not caminho.exists():
            return False
            
        gui_script = PROJECT_DIR / "gui_cortes.py"
        if gui_script.exists():
            subprocess.Popen([str(VENV_PYTHON), str(gui_script), str(caminho)])
            return True
        return False

    def adicionar_tarefa_studio(
        self,
        video_path: Path,
        custom_crop: dict,
        qtd_cortes: int = 10,
        dur_corte: float = 40.0,
        target_res: str = "2K",
        gerar_legendas: bool = True,
        usar_ducking: bool = False,
        musica_nome: str = "synthwave_energy.wav",
        usar_sfx: bool = True,
        whisper_model: str = "medium"
    ) -> str:
        with self.lock:
            task_id = f"studio_{int(time.time() * 1000)}"
            stem = video_path.stem
            streamer = stem.split("_")[0] if "_" in stem else "Streamer"
            
            pasta_saida = video_path.parent / f"cortes_[Studio]_[{sanitizar_nome(stem, 25)}]"
            pasta_saida.mkdir(parents=True, exist_ok=True)

            tarefa = {
                "id": task_id,
                "clip_id": task_id,
                "titulo": f"Studio: {video_path.name}",
                "streamer": streamer,
                "jogo": "Cortes IA Pro Studio",
                "url": str(video_path),
                "platform": "Studio",
                "thumbnail": "",
                "views": "",
                "ranking": "",
                "gerar_cortes": True,
                "modo_mineracao": "top_geral",
                "cortes_por_hora": qtd_cortes,
                "layout_modo": "CUSTOM_SPLIT",
                "custom_crop": custom_crop,
                "status": "downloading",
                "stage": "rendering",
                "progress": 5.0,
                "speed": "GPU AMF Ativa",
                "eta": "Processando",
                "total_bytes": video_path.stat().st_size if video_path.exists() else 0,
                "downloaded_bytes": 0,
                "detalhe_status": "Iniciando renderização de cortes com Crop Customizado...",
                "caminho_arquivo": str(video_path),
                "pasta_organizada": str(pasta_saida),
                "cortes_prontos": [],
                "horas_concluidas": [],
                "logs": ["Iniciando Studio de Cortes IA Pro (GPU AMF)..."],
                "processo": None,
                "cortes_gerados": False,
                "erro": "",
                "created_at": time.time()
            }
            self.tarefas[task_id] = tarefa

        def run_studio():
            try:
                from core.pipeline import processar_video_completo

                def prog_log(msg: str):
                    with self.lock:
                        tarefa["logs"].append(msg)
                        if len(tarefa["logs"]) > 25:
                            tarefa["logs"].pop(0)
                        tarefa["detalhe_status"] = msg
                        if "Renderizando" in msg or "Processando" in msg:
                            tarefa["stage"] = "rendering"
                        elif "Whisper" in msg or "Transcrevendo" in msg:
                            tarefa["stage"] = "transcribing"

                def prog_update(pct_0_a_1: float, msg: str = ""):
                    with self.lock:
                        tarefa["progress"] = round(pct_0_a_1 * 100.0, 1)
                        if msg:
                            tarefa["detalhe_status"] = msg

                cortes = processar_video_completo(
                    video_path=video_path,
                    pasta_saida=pasta_saida,
                    qtd_cortes=qtd_cortes,
                    dur_corte=dur_corte,
                    layout_modo="CUSTOM_SPLIT",
                    target_res=target_res,
                    usar_ducking=usar_ducking,
                    musica_nome=musica_nome,
                    usar_sfx=usar_sfx,
                    gerar_legendas=gerar_legendas,
                    log_callback=prog_log,
                    progress_callback=prog_update,
                    custom_crop=custom_crop,
                    whisper_model=whisper_model
                )

                with self.lock:
                    tarefa["status"] = "completed"
                    tarefa["stage"] = "completed"
                    tarefa["progress"] = 100.0
                    tarefa["cortes_prontos"] = [c.name for c in cortes]
                    tarefa["cortes_gerados"] = True
                    tarefa["detalhe_status"] = f"Sucesso! {len(cortes)} cortes salvos em {pasta_saida.name}"
            except Exception as e:
                import traceback
                traceback.print_exc()
                with self.lock:
                    tarefa["status"] = "error"
                    tarefa["erro"] = str(e)
                    tarefa["detalhe_status"] = f"Erro no processamento: {e}"
                    tarefa["logs"].append(f"[ERRO CRÍTICO] {e}")

        th = threading.Thread(target=run_studio, daemon=True)
        th.start()
        return task_id

# Instância global
GERENCIADOR = GerenciadorDownloads(max_workers=3)
