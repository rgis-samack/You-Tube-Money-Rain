# 🚀 MONITORAMENTO LIVE — TWITCH & KICK PRO 2.0

Interface gráfica desktop de padrão **Microsoft Fluent 2** projetada para:
1. **Monitoramento e Reprodução de Lives Ao Vivo** (saiba quem está transmitindo o jogo agora e assista com 1 clique).
2. **Catálogo de Jogos Expandido** (como na Twitch, com capas em alta definição e busca ao vivo).
3. **Download e Reprodução de Clipes Sem Censura (+18 Bypass)**.
4. **Gerador Automático de Cortes IA Organizados por Categoria do Jogo**.

---

## 🌟 O que há de novo na Versão 2.0

### 1. 🎮 Catálogo de Jogos Expandido
- Mais de 20 dos maiores jogos do mundo já configurados com capas oficiais em alta definição:
  - **GTA 6, GTA 5 (GTA RP), CS:GO / CS2, Warzone, PUBG, Far Cry 6, Valorant, Fortnite, Minecraft, League of Legends, EA FC 25, Apex Legends, Dota 2, Roblox, WoW, Rust, Rainbow Six, Elden Ring, Dead by Daylight, Rocket League, Just Chatting.**
- Botão **"🔄 Atualizar Mais Populares"**: consulta em tempo real o diretório global da Twitch e da Kick e atualiza o carrossel com os jogos que têm mais público no exato momento.

### 2. ✂️ Clipes Virais & 📹 Vídeos Completos como Visão Padrão (Sem forçar Lives)
Ao clicar em qualquer categoria do catálogo (como em `twitch.tv/directory/following/games`):
- A interface **NÃO** exibe canais ao vivo por padrão, abrindo diretamente em:
  1. **`✂️ Clipes & Cortes Populares`** (`clips?range=7d`): cortes virais da última semana ranqueados por visualizações.
  2. **`📹 Vídeos & VODs Completos`** (`videos/all`): transmissões passadas e destaques históricos da categoria ranqueados pelos mais vistos.
  3. **`🔴 Canais Ao Vivo`** (Aba secundária para quando você desejar especificamente ver transmissões em tempo real).

### 3. 🏆 Telemetria de Ranqueamento & Visualizações em Destaque
- **Badges de Ranking Oficiais**:
  - 🥇 `#1 Mais Visto` (Destaque Dourado brilhante)
  - 🥈 `#2` (Prata)
  - 🥉 `#3` (Bronze)
  - `#{rank}` (Fluent Teal Acrílico para as demais posições)
- **Métricas Visuais**:
  - Visualizações exibidas de forma clara tanto na thumbnail quanto na linha de telemetria (`👁️ 195,5 mil visualizações • #1 no ranking`).
  - Duração formatada (`MM:SS` ou `HH:MM:SS`) e data relativa (`ontem`, `anteontem`, `há X dias`).

### 4. 🇧🇷 Padrão em Português do Brasil (PT)
- Todas as consultas da plataforma (clipes, vídeos e pesquisas) vêm filtradas por padrão em **Português do Brasil (`PT`)**.
- Permite alternar rapidamente para `🌐 Todos os Idiomas`, `🇺🇸 English` ou `🇪🇸 Español`.

### 5. ✂️ Pergunta de Confirmação & Organização de Pastas
Ao clicar em **"⬇ Baixar"** ou **"⬇ Baixar Selecionados (Lote)"**, uma janela de diálogo amigável pergunta:
> *"Deseja que o robô faça cortes verticais automáticos (1080×1920) com legendas dinâmicas MrBeast e enquadramento de webcam para o(s) vídeo(s) que você está baixando?"*
> - **`[ ✂️ Sim, gerar cortes com IA ]`**
> - **`[ ⬇️ Não, apenas baixar o original ]`**
> - Opção *"Lembrar minha escolha nas próximas vezes"*.

#### 📁 Estrutura de Pastas por Plataforma e Streamer
Independente de você baixar 1 vídeo ou 10 vídeos em lote, cada plataforma e cada streamer possui sua pasta exclusiva para nunca misturar os conteúdos:

```
gravacoes/ (ou pasta configurada)
├── 📂 Twitch/
│   ├── 📁 PaulinhoLOKObr/
│   │   ├── 🎥 [Grand_Theft_Auto_VI]_[base_militar].mp4       <-- Sem cortes: salvo direto no streamer
│   │   └── 📂 [Grand_Theft_Auto_V]_[Melhores_Momentos]/     <-- Com cortes: pasta dedicada do conteúdo
│   │       ├── 🎥 original_[PaulinhoLOKObr]_[Melhores_Momentos].mp4
│   │       ├── ✂️ corte_01_[PaulinhoLOKObr]_[Melhores_Momentos].mp4
│   │       ├── 📄 corte_01_[PaulinhoLOKObr]_[Melhores_Momentos].txt
│   │       └── 📝 resumo_processamento.txt
│   └── 📁 alanzoka/
│       └── 🎥 [Grand_Theft_Auto_VI]_[que_isso_mandy].mp4
└── 📂 Kick/
    └── 📁 paulinholoko/
        └── 🎥 [Grand_Theft_Auto_V]_[Policial_Doido].mp4
```

---

## 🚀 Como Iniciar

Dê dois cliques no inicializador na raiz:
```cmd
MONITORAMENTO_LIVE.bat
```
Ou dentro da pasta:
```cmd
cd "Monitoramento LIVE"
INICIAR_MONITORAMENTO.bat
```

A interface abrirá automaticamente no modo **Janela Nativa de Aplicativo** sem barra de endereços de navegador.
