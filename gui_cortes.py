# -*- coding: utf-8 -*-
"""
CORTES STUDIO PRO - INTERFACE DE PROCESSAMENTO E EDICAO DE VIDEO
Design Microsoft Fluent 2 - Aceleracao por hardware AMD AMF (Radeon RX 7600)
"""

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import urllib.parse
import webbrowser

from PIL import Image
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES

# Garante importacao do core
DIR_RAIZ = Path(__file__).resolve().parent
if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

from core.config import (
    PROJECT_DIR, VENV_PYTHON, TEMP_DIR, SFX_DIR, MUSICAS_DIR,
    limpar_string_arquivo, seg_para_hms, hms_para_seg
)
from core.renderer import obter_info_video
from core.subtitles import parse_arquivo_txt_companion
from core.pipeline import processar_video_completo, recriar_corte_a_partir_do_txt

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AppCortesPro(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, arquivo_inicial: Path = None):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("Cortes Studio Pro - Processamento e Edicao de Video (GPU AMF)")
        self.geometry("1060x860")
        self.minsize(920, 640)

        # Paleta Microsoft Fluent 2 Dark
        self.configure(fg_color="#181818")

        self.caminho_video = None
        self.video_info = {"duration": 0.0, "width": 1920, "height": 1080, "fps": 60}
        self.pasta_saida_recente = None
        self.txt_atual = None

        # Carrega em cache as 6 imagens reais de enquadramento
        self.layout_ctk_images = {}
        caminho_base_layouts = DIR_RAIZ / "assets" / "layouts"
        for arq in [
            "layout_studio_interativo.png",
            "layout_split_screen.png",
            "layout_automatico.png",
            "layout_dual_focus.png",
            "layout_fundo_desfocado.png",
            "layout_tela_cheia.png"
        ]:
            p = caminho_base_layouts / arq
            if p.exists():
                try:
                    pil_img = Image.open(p)
                    self.layout_ctk_images[arq] = ctk.CTkImage(
                        light_image=pil_img,
                        dark_image=pil_img,
                        size=(162, 288)
                    )
                except Exception as e:
                    print(f"Aviso ao carregar imagem {arq}: {e}")

        self.criar_layout()

        # Drag & Drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.ao_soltar_arquivo)

        if arquivo_inicial and arquivo_inicial.exists():
            if arquivo_inicial.suffix.lower() == ".txt":
                self.carregar_txt_para_edicao(arquivo_inicial)
            else:
                self.carregar_caminho_video(arquivo_inicial)

    def criar_layout(self):
        # 1. Barra de Titulo Superior - Microsoft Fluent Header
        self.frame_topo = ctk.CTkFrame(self, corner_radius=8, fg_color="#202020", border_width=1, border_color="#2d2d2d")
        self.frame_topo.pack(fill="x", padx=16, pady=(14, 10))

        frame_header_content = ctk.CTkFrame(self.frame_topo, fg_color="transparent")
        frame_header_content.pack(fill="x", padx=16, pady=12)

        frame_header_left = ctk.CTkFrame(frame_header_content, fg_color="transparent")
        frame_header_left.pack(side="left", fill="both", expand=True)

        lbl_titulo = ctk.CTkLabel(
            frame_header_left,
            text="Cortes Studio Pro",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#ffffff"
        )
        lbl_titulo.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            frame_header_left,
            text="Edicao e processamento automatizado de cortes verticais (9:16) com aceleracao por hardware AMD AMF",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#9d9d9d"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Badge de Aceleracao por Hardware (Estilo Windows 11 Status Pill)
        lbl_hw_badge = ctk.CTkLabel(
            frame_header_content,
            text="AMD Radeon AMF H.264/HEVC",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#38bdf8",
            fg_color="#0f293d",
            corner_radius=4,
            padx=12,
            pady=4
        )
        lbl_hw_badge.pack(side="right", padx=(10, 0))

        # 2. Abas Principais (Estilo Microsoft Fluent Segmented Control)
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=8,
            fg_color="#202020",
            segmented_button_fg_color="#181818",
            segmented_button_selected_color="#0078d4",
            segmented_button_selected_hover_color="#1084d8",
            segmented_button_unselected_color="#252525",
            segmented_button_unselected_hover_color="#303030"
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        self.tab_gerador = self.tabview.add("Processamento de Video")
        self.tab_editor = self.tabview.add("Editor de Metadados e Legendas")

        self.montar_aba_gerador()
        self.montar_aba_editor()

    def montar_aba_gerador(self):
        # 1. Painel Inferior Fixo de Ação e Logs (SEMPRE visível e acessível em qualquer resolução)
        frame_bottom_action = ctk.CTkFrame(self.tab_gerador, fg_color="transparent")
        frame_bottom_action.pack(side="bottom", fill="x", padx=12, pady=(4, 8))

        self.btn_renderizar = ctk.CTkButton(
            frame_bottom_action,
            text="Iniciar Processamento (GPU AMF)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40,
            fg_color="#0078d4",
            hover_color="#1084d8",
            command=self.iniciar_processamento
        )
        self.btn_renderizar.pack(fill="x", pady=(0, 4))

        self.progressbar = ctk.CTkProgressBar(
            frame_bottom_action,
            progress_color="#0078d4",
            fg_color="#2b2b2b",
            height=6
        )
        self.progressbar.pack(fill="x", pady=(0, 4))
        self.progressbar.set(0)

        self.textbox_log = ctk.CTkTextbox(
            frame_bottom_action,
            height=100,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color="#141414",
            border_width=1,
            border_color="#2a2a2a",
            text_color="#d4d4d4"
        )
        self.textbox_log.pack(fill="x", pady=(0, 4))

        self.btn_abrir_pasta = ctk.CTkButton(
            frame_bottom_action,
            text="Abrir Pasta de Destino",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            state="disabled",
            fg_color="#2b2b2b",
            hover_color="#353535",
            border_width=1,
            border_color="#3d3d3d",
            text_color="#e0e0e0",
            height=30,
            command=self.abrir_pasta_saida
        )
        self.btn_abrir_pasta.pack(fill="x")

        # 2. Painel Superior Rolável de Configurações (Adaptação Fluida ao Redimensionar/Maximizar)
        self.scroll_gerador = ctk.CTkScrollableFrame(
            self.tab_gerador,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_gerador.pack(side="top", fill="both", expand=True, padx=4, pady=(2, 4))

        # 2.1. Arquivo de Entrada
        frame_arq = ctk.CTkFrame(self.scroll_gerador, corner_radius=6, fg_color="#252526", border_width=1, border_color="#333333")
        frame_arq.pack(fill="x", padx=12, pady=(4, 8))

        lbl_arq = ctk.CTkLabel(
            frame_arq,
            text="Arquivo de Origem:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#e5e5e5"
        )
        lbl_arq.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        self.entry_arquivo = ctk.CTkEntry(
            frame_arq,
            placeholder_text="Selecione ou arraste um arquivo de video (.mp4, .mkv, .mov, .ts)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            height=34
        )
        self.entry_arquivo.grid(row=1, column=0, padx=14, pady=(0, 6), sticky="ew")

        btn_sel = ctk.CTkButton(
            frame_arq,
            text="Procurar...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0078d4",
            hover_color="#1084d8",
            height=34,
            width=120,
            command=self.selecionar_arquivo
        )
        btn_sel.grid(row=1, column=1, padx=(0, 14), pady=(0, 6))

        self.lbl_info_video = ctk.CTkLabel(
            frame_arq,
            text="Nenhum arquivo de video carregado.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#888888"
        )
        self.lbl_info_video.grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))
        frame_arq.grid_columnconfigure(0, weight=1)

        # 2.2. Parâmetros de Mineração e Enquadramento
        frame_cfg = ctk.CTkFrame(self.scroll_gerador, corner_radius=6, fg_color="#252526", border_width=1, border_color="#333333")
        frame_cfg.pack(fill="x", padx=12, pady=(0, 8))
        frame_cfg.grid_columnconfigure((1, 3), weight=1)

        # Linha 0: Quantidade e Duração
        lbl_qtd = ctk.CTkLabel(
            frame_cfg,
            text="Quantidade de Cortes:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cccccc"
        )
        lbl_qtd.grid(row=0, column=0, padx=14, pady=(10, 4), sticky="w")

        self.combo_qtd = ctk.CTkComboBox(
            frame_cfg,
            values=[
                "1 corte",
                "3 cortes",
                "5 cortes",
                "10 cortes (Recomendado)",
                "15 cortes",
                "20 cortes",
                "25 cortes",
                "30 cortes"
            ],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            button_color="#333333",
            button_hover_color="#444444",
            height=30
        )
        self.combo_qtd.set("10 cortes (Recomendado)")
        self.combo_qtd.grid(row=0, column=1, padx=(0, 16), pady=(10, 4), sticky="ew")

        lbl_dur = ctk.CTkLabel(
            frame_cfg,
            text="Duração por Corte:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cccccc"
        )
        lbl_dur.grid(row=0, column=2, padx=(10, 8), pady=(10, 4), sticky="w")

        self.combo_dur = ctk.CTkComboBox(
            frame_cfg,
            values=["30 segundos", "40 segundos (Recomendado)", "60 segundos", "90 segundos", "180 segundos"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            button_color="#333333",
            button_hover_color="#444444",
            height=30
        )
        self.combo_dur.set("40 segundos (Recomendado)")
        self.combo_dur.grid(row=0, column=3, padx=(0, 14), pady=(10, 4), sticky="ew")

        # Linha 1: Layout Visual e Resolução de Saída
        lbl_lay = ctk.CTkLabel(
            frame_cfg,
            text="Formato e Enquadramento:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cccccc"
        )
        lbl_lay.grid(row=1, column=0, padx=14, pady=6, sticky="w")

        self.combo_layout = ctk.CTkComboBox(
            frame_cfg,
            values=[
                "Studio Interativo (Ajuste manual de câmera e tela no navegador)",
                "Split Screen (Webcam superior + Linha de estúdio + Jogo)",
                "Automático (Detecção inteligente de câmera facial)",
                "Dual Focus (Visão geral 16:9 + Foco de ação)",
                "Fundo Desfocado (16:9 central com preenchimento lateral)",
                "Tela Cheia 9:16 (Preenchimento total adaptativo)"
            ],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            button_color="#333333",
            button_hover_color="#444444",
            height=30
        )
        self.combo_layout.set("Studio Interativo (Ajuste manual de câmera e tela no navegador)")
        self.combo_layout.grid(row=1, column=1, padx=(0, 16), pady=6, sticky="ew")

        lbl_res = ctk.CTkLabel(
            frame_cfg,
            text="Resolução de Saída:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cccccc"
        )
        lbl_res.grid(row=1, column=2, padx=(10, 8), pady=6, sticky="w")

        self.combo_res = ctk.CTkComboBox(
            frame_cfg,
            values=[
                "2K Vertical (1080x1920 - Padrão)",
                "1080p Vertical (720x1280)",
                "4K Vertical (2160x3840)"
            ],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            button_color="#333333",
            button_hover_color="#444444",
            height=30
        )
        self.combo_res.set("2K Vertical (1080x1920 - Padrão)")
        self.combo_res.grid(row=1, column=3, padx=(0, 14), pady=6, sticky="ew")

        # Linha 2: Atalho para o Studio Web
        frame_studio_bar = ctk.CTkFrame(frame_cfg, fg_color="transparent")
        frame_studio_bar.grid(row=2, column=0, columnspan=4, padx=14, pady=(2, 6), sticky="ew")

        lbl_studio_hint = ctk.CTkLabel(
            frame_studio_bar,
            text="Selecione o formato abaixo para visualizar o enquadramento real que será aplicado na conversão:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#999999"
        )
        lbl_studio_hint.pack(side="left")

        self.btn_studio = ctk.CTkButton(
            frame_studio_bar,
            text="Abrir Studio Web",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2b2b2b",
            hover_color="#353535",
            border_width=1,
            border_color="#0078d4",
            text_color="#38bdf8",
            height=28,
            width=130,
            command=self.abrir_studio_web
        )
        self.btn_studio.pack(side="right")

        # Linha 3: Card de Visualização do Layout com IMAGEM REAL (Microsoft Fluent Technical Inspector)
        self.frame_preview_card = ctk.CTkFrame(
            frame_cfg,
            fg_color="#1a1a1a",
            border_width=1,
            border_color="#333333",
            corner_radius=6
        )
        self.frame_preview_card.grid(row=3, column=0, columnspan=4, padx=14, pady=(4, 10), sticky="ew")

        # Container da imagem de preview real (162x288 px - exata proporção 9:16)
        self.lbl_preview_img = ctk.CTkLabel(
            self.frame_preview_card,
            text="",
            image=None,
            width=165,
            height=292
        )
        self.lbl_preview_img.grid(row=0, column=0, rowspan=4, padx=(14, 16), pady=10, sticky="n")

        # Painel lateral com especificações e seletor rápido
        frame_preview_info = ctk.CTkFrame(self.frame_preview_card, fg_color="transparent")
        frame_preview_info.grid(row=0, column=1, rowspan=4, padx=(0, 14), pady=10, sticky="nsew")
        self.frame_preview_card.grid_columnconfigure(1, weight=1)

        self.lbl_preview_title = ctk.CTkLabel(
            frame_preview_info,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_preview_title.pack(anchor="w", pady=(0, 6))

        # Seletor rápido por botões (pills) em grade 2x3 (Evita sobreposição em qualquer largura de tela)
        frame_pills = ctk.CTkFrame(frame_preview_info, fg_color="transparent")
        frame_pills.pack(anchor="w", pady=(0, 8), fill="x")
        frame_pills.grid_columnconfigure((0, 1, 2), weight=1)

        self.pill_buttons = {}
        layouts_rapidos = [
            ("Studio Interativo", "Studio Interativo (Ajuste manual de câmera e tela no navegador)"),
            ("Split Screen", "Split Screen (Webcam superior + Linha de estúdio + Jogo)"),
            ("Automático", "Automático (Detecção inteligente de câmera facial)"),
            ("Dual Focus", "Dual Focus (Visão geral 16:9 + Foco de ação)"),
            ("Fundo Desfocado", "Fundo Desfocado (16:9 central com preenchimento lateral)"),
            ("Tela Cheia", "Tela Cheia 9:16 (Preenchimento total adaptativo)")
        ]

        for idx_p, (rotulo, val_completo) in enumerate(layouts_rapidos):
            r = idx_p // 3
            c = idx_p % 3
            btn_pill = ctk.CTkButton(
                frame_pills,
                text=rotulo,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                height=28,
                fg_color="#2b2b2b",
                hover_color="#383838",
                border_width=1,
                border_color="#3d3d3d",
                text_color="#cccccc",
                command=lambda v=val_completo: self.selecionar_formato_por_pill(v)
            )
            btn_pill.grid(row=r, column=c, padx=3, pady=3, sticky="ew")
            self.pill_buttons[rotulo] = btn_pill

        self.lbl_preview_desc = ctk.CTkLabel(
            frame_preview_info,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#a0a0a0",
            wraplength=540,
            justify="left"
        )
        self.lbl_preview_desc.pack(anchor="w", pady=(0, 8))

        self.lbl_preview_badge = ctk.CTkLabel(
            frame_preview_info,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#0078d4"
        )
        self.lbl_preview_badge.pack(anchor="w", pady=(0, 0))

        self.combo_layout.configure(command=self.atualizar_preview_layout)
        self.atualizar_preview_layout()

        # 2.3. Opções de Audio e Legendas
        frame_audio = ctk.CTkFrame(self.scroll_gerador, corner_radius=6, fg_color="#252526", border_width=1, border_color="#333333")
        frame_audio.pack(fill="x", padx=12, pady=(0, 8))

        self.chk_legendas = ctk.CTkCheckBox(
            frame_audio,
            text="Inserir legendas sincronizadas palavra por palavra no video (Whisper)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0078d4",
            hover_color="#1084d8",
            border_color="#444444"
        )
        self.chk_legendas.select()
        self.chk_legendas.grid(row=0, column=0, columnspan=2, padx=14, pady=(8, 4), sticky="w")

        lbl_whisper = ctk.CTkLabel(
            frame_audio,
            text="Modelo Whisper:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cccccc"
        )
        lbl_whisper.grid(row=0, column=2, padx=(10, 6), pady=(8, 4), sticky="w")

        self.combo_whisper_model = ctk.CTkComboBox(
            frame_audio,
            values=[
                "Medium (Alta Fidelidade)",
                "Small (Modo Rápido - 3x mais veloz)"
            ],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            button_color="#333333",
            button_hover_color="#444444",
            width=250,
            height=28
        )
        self.combo_whisper_model.set("Medium (Alta Fidelidade)")
        self.combo_whisper_model.grid(row=0, column=3, padx=(0, 14), pady=(8, 4), sticky="w")

        self.chk_ducking = ctk.CTkCheckBox(
            frame_audio,
            text="Atenuação automática de música de fundo durante a fala (Audio Ducking)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0078d4",
            hover_color="#1084d8",
            border_color="#444444"
        )
        self.chk_ducking.grid(row=1, column=0, columnspan=2, padx=14, pady=(2, 4), sticky="w")

        self.chk_sfx = ctk.CTkCheckBox(
            frame_audio,
            text="Efeito sonoro de transição no início de cada corte",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0078d4",
            hover_color="#1084d8",
            border_color="#444444"
        )
        self.chk_sfx.select()
        self.chk_sfx.grid(row=2, column=0, padx=14, pady=(2, 6), sticky="w")

        lbl_track = ctk.CTkLabel(
            frame_audio,
            text="Trilha sonora:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cccccc"
        )
        lbl_track.grid(row=2, column=2, padx=(10, 6), pady=(2, 6), sticky="w")

        self.combo_musica = ctk.CTkComboBox(
            frame_audio,
            values=["synthwave_energy.wav", "lofi_chill.wav"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            button_color="#333333",
            button_hover_color="#444444",
            width=230,
            height=28
        )
        self.combo_musica.set("synthwave_energy.wav")
        self.combo_musica.grid(row=2, column=3, padx=(0, 14), pady=(2, 6), sticky="w")

        lbl_whisper_tech = ctk.CTkLabel(
            frame_audio,
            text="✓ Filtro Vocal FFmpeg (85Hz-7.5kHz + Denoise) e Silero VAD ativos para eliminar deformações",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#38bdf8"
        )
        lbl_whisper_tech.grid(row=3, column=0, columnspan=4, padx=14, pady=(2, 8), sticky="w")

    def montar_aba_editor(self):
        # Seleção do TXT
        frame_txt = ctk.CTkFrame(self.tab_editor, corner_radius=6, fg_color="#252526", border_width=1, border_color="#333333")
        frame_txt.pack(fill="x", padx=12, pady=(10, 8))

        lbl_txt = ctk.CTkLabel(
            frame_txt,
            text="Arquivo de Metadados (.txt):",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#e5e5e5"
        )
        lbl_txt.grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        self.entry_txt_path = ctk.CTkEntry(
            frame_txt,
            placeholder_text="Arraste ou selecione o arquivo .txt do corte correspondente",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            height=34
        )
        self.entry_txt_path.grid(row=1, column=0, padx=14, pady=(0, 6), sticky="ew")

        btn_sel_txt = ctk.CTkButton(
            frame_txt,
            text="Procurar...",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0078d4",
            hover_color="#1084d8",
            height=34,
            width=120,
            command=self.selecionar_txt
        )
        btn_sel_txt.grid(row=1, column=1, padx=(0, 14), pady=(0, 6))

        self.lbl_info_txt = ctk.CTkLabel(
            frame_txt,
            text="Nenhum arquivo .txt carregado.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#888888"
        )
        self.lbl_info_txt.grid(row=2, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 10))
        frame_txt.grid_columnconfigure(0, weight=1)

        # Campos de Edição
        frame_campos = ctk.CTkFrame(self.tab_editor, corner_radius=6, fg_color="#252526", border_width=1, border_color="#333333")
        frame_campos.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        lbl_hook = ctk.CTkLabel(
            frame_campos,
            text="Título de Destaque Superior (Gancho visual no topo do vídeo):",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#cccccc"
        )
        lbl_hook.pack(anchor="w", padx=14, pady=(10, 4))

        self.entry_edit_hook = ctk.CTkEntry(
            frame_campos,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#1c1c1c",
            border_color="#3a3a3a",
            height=34
        )
        self.entry_edit_hook.pack(fill="x", padx=14, pady=(0, 8))

        lbl_leg = ctk.CTkLabel(
            frame_campos,
            text="Transcrição e Legendas Sincronizadas (Edite livremente as palavras e marcações de tempo):",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#cccccc"
        )
        lbl_leg.pack(anchor="w", padx=14, pady=(0, 4))

        self.textbox_edit_legendas = ctk.CTkTextbox(
            frame_campos,
            height=180,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#141414",
            border_width=1,
            border_color="#2a2a2a",
            text_color="#d4d4d4"
        )
        self.textbox_edit_legendas.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Ações do Editor
        frame_btns = ctk.CTkFrame(frame_campos, fg_color="transparent")
        frame_btns.pack(fill="x", padx=14, pady=(0, 10))

        self.btn_recriar_txt = ctk.CTkButton(
            frame_btns,
            text="Salvar Alterações e Recriar Vídeo (GPU AMF)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=38,
            fg_color="#0078d4",
            hover_color="#1084d8",
            command=self.recriar_video_pelo_editor
        )
        self.btn_recriar_txt.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_clipboard = ctk.CTkButton(
            frame_btns,
            text="Copiar Conteúdo",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=38,
            width=160,
            fg_color="#2b2b2b",
            hover_color="#353535",
            border_width=1,
            border_color="#3d3d3d",
            command=self.copiar_post_clipboard
        )
        btn_clipboard.pack(side="left", padx=(0, 10))

        btn_notepad = ctk.CTkButton(
            frame_btns,
            text="Abrir no Bloco de Notas",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=38,
            width=170,
            fg_color="#2b2b2b",
            hover_color="#353535",
            border_width=1,
            border_color="#3d3d3d",
            command=self.abrir_no_bloco_de_notas
        )
        btn_notepad.pack(side="left")

    def log(self, msg: str):
        msg_limpa = msg.replace("🚀", "").replace("⚡", "").replace("✓", "[OK]").replace("❌", "[ERRO]")
        def _update():
            self.textbox_log.insert("end", f"{msg_limpa}\n")
            self.textbox_log.see("end")
        self.after(0, _update)

    def atualizar_progresso(self, pct: float, msg: str = ""):
        def _update():
            self.progressbar.set(pct)
            if msg:
                self.btn_renderizar.configure(text=f"Processando: {msg} (GPU AMF)")
        self.after(0, _update)

    def ao_soltar_arquivo(self, event):
        data = event.data.strip()
        if data.startswith("{") and data.endswith("}"):
            data = data[1:-1]
        caminho = Path(data.strip('"'))
        if caminho.exists() and caminho.is_file():
            if caminho.suffix.lower() == ".txt":
                self.tabview.set("Editor de Metadados e Legendas")
                self.carregar_txt_para_edicao(caminho)
            else:
                self.tabview.set("Processamento de Video")
                self.carregar_caminho_video(caminho)

    def selecionar_arquivo(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione o arquivo de vídeo",
            filetypes=[("Vídeos", "*.mp4 *.mkv *.mov *.ts *.webm"), ("Todos", "*.*")]
        )
        if arquivo:
            self.carregar_caminho_video(Path(arquivo))

    def carregar_caminho_video(self, caminho: Path):
        self.caminho_video = caminho
        self.entry_arquivo.delete(0, "end")
        self.entry_arquivo.insert(0, str(caminho))

        info = obter_info_video(caminho)
        self.video_info = info
        dur_str = seg_para_hms(info["duration"])
        self.lbl_info_video.configure(
            text=f"Carregado: {caminho.name} | Formato: {info['width']}x{info['height']} @ {info['fps']}fps | Duração: {dur_str} ({info['duration']:.1f}s)",
            text_color="#38bdf8"
        )
        self.log(f"[INFO] Vídeo de origem carregado: {caminho.name}")

    def selecionar_txt(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione o arquivo .txt correspondente",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos", "*.*")]
        )
        if arquivo:
            self.carregar_txt_para_edicao(Path(arquivo))

    def carregar_txt_para_edicao(self, caminho_txt: Path):
        self.txt_atual = caminho_txt
        self.entry_txt_path.delete(0, "end")
        self.entry_txt_path.insert(0, str(caminho_txt))

        meta, hook, legendas = parse_arquivo_txt_companion(caminho_txt)
        self.entry_edit_hook.delete(0, "end")
        self.entry_edit_hook.insert(0, hook)

        self.textbox_edit_legendas.delete("1.0", "end")
        linhas_texto = []
        for leg in legendas:
            m_s, s_s = int(leg["start"] // 60), int(leg["start"] % 60)
            m_e, s_e = int(leg["end"] // 60), int(leg["end"] % 60)
            linhas_texto.append(f"[{m_s:02d}:{s_s:02d} - {m_e:02d}:{s_e:02d}] {leg['text']}")
        self.textbox_edit_legendas.insert("1.0", "\n".join(linhas_texto))

        origem = meta.get("ARQUIVO_ORIGEM", "Origem desconhecida")
        self.lbl_info_txt.configure(
            text=f"Carregado: {caminho_txt.name} | Origem: {Path(origem).name} | Duração: {meta.get('DURACAO', '40')}s",
            text_color="#38bdf8"
        )

    def abrir_no_bloco_de_notas(self):
        if self.txt_atual and self.txt_atual.exists():
            import subprocess
            subprocess.Popen(["notepad.exe", str(self.txt_atual)])

    def copiar_post_clipboard(self):
        if self.txt_atual and self.txt_atual.exists():
            with open(self.txt_atual, "r", encoding="utf-8-sig") as f:
                conteudo = f.read()
            self.clipboard_clear()
            self.clipboard_append(conteudo)
            messagebox.showinfo("Copiado", "Texto e metadados copiados para a área de transferência.")

    def recriar_video_pelo_editor(self):
        if not self.txt_atual or not self.txt_atual.exists():
            messagebox.showerror("Erro", "Selecione um arquivo .txt válido antes de continuar.")
            return

        novo_hook = self.entry_edit_hook.get().strip() or "MOMENTO EM DESTAQUE"
        novas_legendas = self.textbox_edit_legendas.get("1.0", "end").strip()

        # Atualiza o arquivo .txt
        meta, _, _ = parse_arquivo_txt_companion(self.txt_atual)
        with open(self.txt_atual, "w", encoding="utf-8-sig") as f:
            f.write("# METADADOS DE RENDERIZACAO (NAO ALTERE ESTAS LINHAS)\n")
            for k, v in meta.items():
                f.write(f"# {k}: {v}\n")
            f.write("\n")
            f.write("====================================================================\n")
            f.write("TITULO DO CORTE (GANCHO NO TOPO DO VIDEO):\n")
            f.write("====================================================================\n")
            f.write(f"{novo_hook}\n\n")
            f.write("====================================================================\n")
            f.write("LEGENDA DO POST (COPIAR E COLAR):\n")
            f.write("====================================================================\n")
            f.write("Confira esse momento da transmissão.\n\n#cortes #games #gta #shorts #reels #tiktok\n\n")
            f.write("====================================================================\n")
            f.write("LEGENDAS DO VÍDEO (SINCRONIZADAS):\n")
            f.write("====================================================================\n")
            f.write(f"{novas_legendas}\n")

        self.tabview.set("Processamento de Video")
        self.log(f"\n[INFO] Recriando vídeo com alterações de texto: {self.txt_atual.name}...")
        self.btn_renderizar.configure(state="disabled", text="Processando renderização...")
        self.progressbar.set(0.3)

        def worker():
            sucesso = recriar_corte_a_partir_do_txt(self.txt_atual)
            self.progressbar.set(1.0)
            self.btn_renderizar.configure(state="normal", text="Iniciar Processamento (GPU AMF)")
            if sucesso:
                self.log(f"[OK] Vídeo atualizado com sucesso!")
                messagebox.showinfo("Sucesso", "Vídeo recriado com sucesso com as novas legendas.")
            else:
                self.log(f"[ERRO] Falha ao recriar o vídeo.")
                messagebox.showerror("Erro", "Falha ao recriar o vídeo.")

        threading.Thread(target=worker, daemon=True).start()

    def abrir_studio_web(self):
        url = "http://127.0.0.1:8765/studio"
        if self.caminho_video and self.caminho_video.exists():
            url += f"?video={urllib.parse.quote(str(self.caminho_video))}"
        webbrowser.open(url)

    def abrir_pasta_saida(self):
        if self.pasta_saida_recente and self.pasta_saida_recente.exists():
            os.startfile(str(self.pasta_saida_recente))

    def selecionar_formato_por_pill(self, val_completo):
        self.combo_layout.set(val_completo)
        self.atualizar_preview_layout(val_completo)

    def atualizar_preview_layout(self, escolha=None):
        if not escolha:
            escolha = self.combo_layout.get()

        info_layouts = {
            "Studio Interativo": {
                "titulo": "Studio Interativo (Ajuste Manual CAM e DISPLAY)",
                "img": "layout_studio_interativo.png",
                "desc": "Permite posicionar e redimensionar individualmente as áreas de câmera e gameplay com controle interativo e pré-visualização em tempo real.",
                "badge": "Ajuste interativo no navegador | Proporção 9:16 personalizável | GPU AMF"
            },
            "Split Screen": {
                "titulo": "Split Screen (Webcam Superior + Linha de Estúdio + Exibição Inferior)",
                "img": "layout_split_screen.png",
                "desc": "Rastreia o apresentador via detecção facial (YuNet), enquadra a câmera no terço superior com divisória de estúdio e posiciona o conteúdo na base.",
                "badge": "Enquadramento automático facial | Retenção otimizada | Resolução 1080x1920"
            },
            "Automático": {
                "titulo": "Automático (Detecção Inteligente)",
                "img": "layout_automatico.png",
                "desc": "Analisa o vídeo de entrada. Caso haja rosto detectado, aplica Split Screen; se não houver câmera identificada, aplica Fundo Desfocado.",
                "badge": "Seleção automática de enquadramento | Decisão por análise de imagem"
            },
            "Dual Focus": {
                "titulo": "Dual Focus (Visão Geral 16:9 + Foco de Ação)",
                "img": "layout_dual_focus.png",
                "desc": "Preserva a visão panorâmica 16:9 completa no topo e amplia o centro de ação com zoom de alta resolução na metade inferior.",
                "badge": "Indicado para jogos de ação, FPS e simulação | Detalhe em dobro"
            },
            "Fundo Desfocado": {
                "titulo": "Fundo Desfocado (16:9 Central com Preenchimento Lateral)",
                "img": "layout_fundo_desfocado.png",
                "desc": "Posiciona o vídeo 16:9 centralizado na horizontal com o fundo preenchido pelo mesmo vídeo desfocado e escurecido.",
                "badge": "Enquadramento neutro | Formato padrão para conteúdo panorâmico"
            },
            "Tela Cheia": {
                "titulo": "Tela Cheia 9:16 (Preenchimento Total Adaptativo)",
                "img": "layout_tela_cheia.png",
                "desc": "Recorta o centro da imagem para ocupar 100% da tela do dispositivo móvel sem barras ou bordas pretas.",
                "badge": "Preenchimento 100% de tela | Zoom adaptativo de clímax"
            }
        }

        selected_info = info_layouts["Studio Interativo"]
        for k, v in info_layouts.items():
            if k in escolha:
                selected_info = v
                break

        # Atualiza a imagem de pré-visualização real
        if hasattr(self, 'lbl_preview_img') and selected_info["img"] in self.layout_ctk_images:
            self.lbl_preview_img.configure(image=self.layout_ctk_images[selected_info["img"]])

        if hasattr(self, 'lbl_preview_title'):
            self.lbl_preview_title.configure(text=selected_info["titulo"])
            self.lbl_preview_desc.configure(text=selected_info["desc"])
            self.lbl_preview_badge.configure(text=selected_info["badge"])

        # Destaca o botão pill selecionado
        if hasattr(self, 'pill_buttons'):
            for rotulo, btn in self.pill_buttons.items():
                if rotulo in escolha:
                    btn.configure(fg_color="#0078d4", text_color="#ffffff", border_color="#1084d8")
                else:
                    btn.configure(fg_color="#2b2b2b", text_color="#cccccc", border_color="#3d3d3d")

    def iniciar_processamento(self):
        if not self.caminho_video or not self.caminho_video.exists():
            caminho_digitado = self.entry_arquivo.get().strip().strip('"')
            if caminho_digitado and Path(caminho_digitado).exists():
                self.carregar_caminho_video(Path(caminho_digitado))
            else:
                messagebox.showerror("Erro", "Selecione um arquivo de vídeo válido antes de iniciar.")
                return

        lay_raw = self.combo_layout.get()
        if "Studio Interativo" in lay_raw or "Personalizado" in lay_raw:
            self.log("[INFO] Abrindo Studio de Enquadramento no navegador...")
            self.abrir_studio_web()
            return
        elif "Split Screen" in lay_raw or "Split" in lay_raw:
            lay_modo = "SPLIT_PRO"
        elif "Dual Focus" in lay_raw or "Dual" in lay_raw:
            lay_modo = "DUAL_FOCUS"
        elif "Fundo Desfocado" in lay_raw or "Desfocado" in lay_raw:
            lay_modo = "BLUR_BACKGROUND"
        elif "Tela Cheia" in lay_raw:
            lay_modo = "FULL_BLEED_ZOOM"
        else:
            lay_modo = "AUTO"

        self.btn_renderizar.configure(state="disabled", text="Processando cortes e renderizando via GPU AMF...")
        self.btn_abrir_pasta.configure(state="disabled")
        self.progressbar.set(0.05)

        # Mapeamento de Quantidade
        qtd_map = {
            "1 corte": 1,
            "3 cortes": 3,
            "5 cortes": 5,
            "10 cortes (Recomendado)": 10,
            "10 cortes (Padrão)": 10,
            "15 cortes": 15,
            "20 cortes": 20,
            "25 cortes": 25,
            "30 cortes": 30
        }
        qtd_raw = self.combo_qtd.get()
        qtd = qtd_map.get(qtd_raw)
        if qtd is None:
            try:
                qtd = int(qtd_raw.split()[0])
            except Exception:
                qtd = 10

        # Mapeamento de Duração
        dur_map = {
            "30 segundos": 30.0, "30s (Rápido)": 30.0,
            "40 segundos (Recomendado)": 40.0, "40s (Padrão Viral)": 40.0,
            "60 segundos": 60.0, "60s (1 Minuto)": 60.0,
            "90 segundos": 90.0, "90s (Reels)": 90.0,
            "180 segundos": 180.0, "180s (Shorts Max)": 180.0
        }
        dur = dur_map.get(self.combo_dur.get(), 40.0)

        # Resolução de Saída (Garante que self.combo_res existe e não lança erro)
        res_raw = self.combo_res.get() if hasattr(self, 'combo_res') else "2K"
        target_res = "4K" if "4K" in res_raw else ("1080p" if "1080p" in res_raw else "2K")

        usar_ducking = bool(self.chk_ducking.get())
        usar_sfx = bool(self.chk_sfx.get())
        musica_nome = self.combo_musica.get()
        gerar_legendas = bool(self.chk_legendas.get())
        whisper_raw = self.combo_whisper_model.get().lower() if hasattr(self, 'combo_whisper_model') else "medium"
        whisper_model = "small" if "small" in whisper_raw else "medium"

        stem = self.caminho_video.stem
        canal = stem.split("_")[0].capitalize() if "_" in stem else "Streamer"
        pasta_saida = PROJECT_DIR / f"cortes_[{limpar_string_arquivo(canal)}]_[{limpar_string_arquivo(stem)}]"
        self.pasta_saida_recente = pasta_saida

        def worker():
            try:
                res = processar_video_completo(
                    video_path=self.caminho_video,
                    pasta_saida=pasta_saida,
                    qtd_cortes=qtd,
                    dur_corte=dur,
                    layout_modo=lay_modo,
                    target_res=target_res,
                    usar_ducking=usar_ducking,
                    musica_nome=musica_nome,
                    usar_sfx=usar_sfx,
                    gerar_legendas=gerar_legendas,
                    log_callback=self.log,
                    progress_callback=self.atualizar_progresso,
                    whisper_model=whisper_model
                )
                self.progressbar.set(1.0)
                self.btn_abrir_pasta.configure(state="normal")
                messagebox.showinfo("Sucesso", f"Processamento concluído com sucesso.\n{len(res)} segmentos gerados em:\n{pasta_saida}")
            except Exception as e:
                self.log(f"[ERRO] Ocorreu um erro no processamento: {e}")
                messagebox.showerror("Erro", f"Ocorreu um erro: {e}")
            finally:
                self.btn_renderizar.configure(state="normal", text="Iniciar Processamento (GPU AMF)")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    arq = Path(sys.argv[1].strip('"')) if len(sys.argv) > 1 and Path(sys.argv[1].strip('"')).exists() else None
    app = AppCortesPro(arquivo_inicial=arq)
    app.mainloop()
