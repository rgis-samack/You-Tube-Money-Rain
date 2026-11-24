# -*- coding: utf-8 -*-
"""
MINERADOR AUTOMÁTICO DE LIVES E GAMEPLAYS (STREAMLINK + IA + GPU AMF)
Versão 2.0 Pro - Arquitetura Modular, Cérebro Viral Multi-Fator e Legendas MrBeast
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# Garante importação do módulo core
DIR_RAIZ = Path(__file__).resolve().parent
if str(DIR_RAIZ) not in sys.path:
    sys.path.insert(0, str(DIR_RAIZ))

from core.config import (
    PROJECT_DIR, VENV_PYTHON, STREAMLINK_EXE, GRAVACOES_DIR,
    limpar_string_arquivo
)
from core.pipeline import (
    processar_video_completo, recriar_corte_a_partir_do_txt
)

def menu():
    print("=" * 65)
    print("      MINERADOR AUTOMÁTICO DE LIVES 2.0 (Streamlink + IA)")
    print("      AMD Radeon RX 7600 AMF + Cérebro Viral Multi-Fator")
    print("=" * 65)
    print("[1] Minerar vídeo da pasta gravações ou vídeos locais")
    print("[2] Gravar e minerar live ao vivo (Twitch, Kick ou YouTube)")
    print("[3] Recriar/Atualizar vídeo a partir de arquivo TXT editado")
    print("[4] Abrir Interface Gráfica Moderna (GUI)")
    print("[5] Sair")
    print("=" * 65)

    opcao = input("Escolha uma opção [padrão 1]: ").strip() or "1"

    if opcao == "1":
        print("\nVídeos encontrados em 'gravacoes' e 'videos':")
        arquivos = list(GRAVACOES_DIR.glob("*.mp4")) + list((PROJECT_DIR / "videos").glob("*.mp4"))
        for idx, f in enumerate(arquivos, 1):
            mb = f.stat().st_size / (1024 * 1024)
            print(f"  [{idx}] {f.name} ({mb:.1f} MB)")

        escolha = input("\nDigite o número do vídeo ou o caminho completo: ").strip()
        if escolha.isdigit() and 1 <= int(escolha) <= len(arquivos):
            video_sel = arquivos[int(escolha) - 1]
        else:
            video_sel = Path(escolha.strip('"'))

        if not video_sel.exists():
            print("Erro: Arquivo não encontrado.")
            return

        leg = input("Deseja gerar legendas dinâmicas com Whisper? [S/n]: ").strip().lower()
        gerar_leg = leg != "n"

        print("\nEscolha o layout visual:")
        print("  [1] Split Screen Pro (Webcam Topo + Linha Estúdio + Jogo Base)")
        print("  [2] Dual Focus Viral (Gameplay 16:9 Topo Completo + Zoom de Ação Base)")
        print("  [3] Fundo Desfocado Moderno (Gameplay 16:9 + Blur)")
        lay_opt = input("Opção de layout [padrão 1]: ").strip() or "1"
        lay_map = {"1": "SPLIT_PRO", "2": "DUAL_FOCUS", "3": "BLUR_BACKGROUND"}
        layout_escolhido = lay_map.get(lay_opt, "SPLIT_PRO")

        stem = video_sel.stem
        canal = stem.split("_")[0].capitalize() if "_" in stem else "Streamer"
        pasta_saida = PROJECT_DIR / f"cortes_[{limpar_string_arquivo(canal)}]_[{limpar_string_arquivo(stem)}]"
        processar_video_completo(video_sel, pasta_saida, qtd_cortes=10, dur_corte=40.0, layout_modo=layout_escolhido, target_res="2K", gerar_legendas=gerar_leg)

    elif opcao == "2":
        url = input("Digite a URL da live (Twitch/Kick/YouTube): ").strip()
        if not url: return

        canal = "Streamer"
        if "twitch.tv" in url:
            canal = url.split("twitch.tv/")[-1].split("/")[0].capitalize()
        elif "kick.com" in url:
            canal = url.split("kick.com/")[-1].split("/")[0].capitalize()

        tempo_min = input("\nDeseja gravar por quantos minutos? (Ex: 15, 30) [vazio = até parar]: ").strip()
        data_tag = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        out_video = GRAVACOES_DIR / f"[{canal}]_[Live]_[{data_tag}].mp4"

        print(f"\nIniciando gravação com Streamlink (Melhor resolução disponível):")
        print(f"👉 {out_video}")
        cmd = [
            str(STREAMLINK_EXE), url, "best",
            "--twitch-disable-ads",
            "--twitch-low-latency",
            "-o", str(out_video)
        ]
        if tempo_min.isdigit():
            cmd += ["--stream-segmented-duration", f"{int(tempo_min)*60}s"]

        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            print("\nGravação finalizada.")

        if out_video.exists():
            pasta_saida = PROJECT_DIR / f"cortes_[{limpar_string_arquivo(canal)}]_[Live]"
            processar_video_completo(out_video, pasta_saida, qtd_cortes=10, dur_corte=40.0, layout_modo="SPLIT_PRO", target_res="2K")

    elif opcao == "3":
        caminho = input("\nArraste o arquivo .txt editado para cá: ").strip().strip('"')
        recriar_corte_a_partir_do_txt(Path(caminho))

    elif opcao == "4":
        subprocess.Popen([str(VENV_PYTHON), str(PROJECT_DIR / "gui_cortes.py")])

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg_path = Path(sys.argv[1].strip('"'))
        if arg_path.suffix.lower() == ".txt":
            recriar_corte_a_partir_do_txt(arg_path)
        elif arg_path.suffix.lower() in [".mp4", ".mkv", ".mov", ".ts", ".webm"]:
            stem = arg_path.stem
            canal = stem.split("_")[0].capitalize() if "_" in stem else "Streamer"
            pasta_saida = PROJECT_DIR / f"cortes_[{limpar_string_arquivo(canal)}]_[{limpar_string_arquivo(stem)}]"
            processar_video_completo(arg_path, pasta_saida, qtd_cortes=10, dur_corte=40.0, layout_modo="SPLIT_PRO", target_res="2K")
        else:
            menu()
    else:
        menu()
