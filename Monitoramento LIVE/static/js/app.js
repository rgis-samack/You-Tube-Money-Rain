/**
 * MONITORAMENTO LIVE - APLICAÇÃO CLIENTE 2.0
 * Microsoft Fluent 2 + Twitch/Kick Dark Cinema
 * Gerenciamento de Clipes, Transmissões Ao Vivo (Lives),
 * Player Sem Censura e Gerador Automático de Cortes IA Organizados por Categoria
 */

// Estado Global da Aplicação
const State = {
  platform: 'twitch', // 'twitch' | 'kick'
  currentTab: 'clips', // 'clips' | 'videos' | 'lives'
  featuredGames: [],
  currentGame: null,
  period: 'LAST_WEEK', // LAST_DAY | LAST_WEEK | LAST_MONTH | ALL_TIME
  language: 'PT', // Padrão: Português do Brasil
  sort: 'VIEWS_DESC',
  bypass18: true,
  batchMode: false,
  selectedClips: new Map(),
  clips: [],
  videos: [],
  lives: [],
  currentPlayingMedia: null,
  pendingDownloadAction: null, // armazena clipe(s) para confirmação de cortes
  rememberCutsChoice: null, // true | false | null
  downloadsInterval: null
};

// Formatação Auxiliar
function getRankingBadge(idx, ranking) {
  const rank = ranking || (idx + 1);
  if (rank === 1) {
    return `<span class="ranking-badge rank-1" title="Top 1 Mais Visto">🥇 #1 Mais Visto</span>`;
  } else if (rank === 2) {
    return `<span class="ranking-badge rank-2" title="Top 2 Mais Visto">🥈 #2</span>`;
  } else if (rank === 3) {
    return `<span class="ranking-badge rank-3" title="Top 3 Mais Visto">🥉 #3</span>`;
  } else {
    return `<span class="ranking-badge rank-other" title="Posição no ranking">#${rank}</span>`;
  }
}

// Formatação Auxiliar
function formatViews(views) {
  if (!views) return '0 views';
  const num = parseInt(views);
  if (num >= 1000000) return (num / 1000000).toFixed(1).replace('.', ',') + ' mi visualizações';
  if (num >= 1000) return (num / 1000).toFixed(1).replace('.', ',') + ' mil visualizações';
  return `${num} visualizações`;
}

function formatLiveViewers(viewers) {
  const num = parseInt(viewers || 0);
  if (num >= 1000000) return (num / 1000000).toFixed(1).replace('.', ',') + ' mi espectadores';
  if (num >= 1000) return (num / 1000).toFixed(1).replace('.', ',') + ' mil espectadores';
  return `${num} espectadores`;
}

function formatDuration(sec) {
  const total = parseInt(sec || 0);
  if (total <= 0) return '0:00';
  
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  
  if (h > 0) {
    return `${h}:${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  }
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

function formatDurationHuman(sec) {
  const total = parseInt(sec || 0);
  if (total <= 0) return '0s';
  
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  
  if (h > 0) {
    return `${h}h ${m > 0 ? m + 'min' : ''}`.trim();
  }
  if (m > 0) {
    return `${m}min ${s > 0 ? s + 's' : ''}`.trim();
  }
  return `${s}s`;
}

function formatTimeAgo(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffHours = Math.floor((now - date) / (1000 * 60 * 60));
  if (diffHours < 24) return `há ${diffHours || 1} horas`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return 'ontem';
  if (diffDays === 2) return 'anteontem';
  return `há ${diffDays} dias`;
}

// Notificações Toast
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = 'toast';
  const icon = type === 'success' ? '✅' : type === 'warning' ? '⚠️' : type === 'error' ? '❌' : 'ℹ️';
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Inicialização da Página
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await loadFeaturedGames();
  await loadSettings();
  startDownloadsPolling();
});

// Event Listeners Globais
function setupEventListeners() {
  // Troca de Plataforma (Twitch / Kick)
  document.querySelectorAll('.platform-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const plat = e.currentTarget.dataset.platform;
      switchPlatform(plat);
    });
  });

  // Alternador de Abas: Clipes & Cortes vs Vídeos VODs vs Lives Ao Vivo
  document.querySelectorAll('.content-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.content-tab').forEach(t => t.classList.remove('active'));
      e.currentTarget.classList.add('active');
      State.currentTab = e.currentTarget.dataset.tab;
      
      const periodWrap = document.getElementById('period-pills-wrap');
      const sortSelect = document.getElementById('sort-select');
      if (State.currentTab === 'lives') {
        if (periodWrap) periodWrap.style.display = 'none';
        if (sortSelect) sortSelect.style.display = 'none';
      } else if (State.currentTab === 'videos') {
        if (periodWrap) periodWrap.style.display = 'none';
        if (sortSelect) {
          sortSelect.style.display = 'block';
          sortSelect.innerHTML = `
            <option value="VIEWS" selected>🔥 Mais Visualizados (Ranking Geral)</option>
            <option value="TIME">🕒 Mais Recentes</option>
            <option value="TRENDING">⚡ Em Alta (Trending)</option>
          `;
          State.sort = 'VIEWS';
        }
      } else {
        if (periodWrap) periodWrap.style.display = 'flex';
        if (sortSelect) {
          sortSelect.style.display = 'block';
          sortSelect.innerHTML = `
            <option value="VIEWS_DESC" selected>🔥 Mais Visualizados (Ranking)</option>
            <option value="TRENDING">⚡ Em Alta (Trending)</option>
          `;
          State.sort = 'VIEWS_DESC';
        }
      }

      fetchCurrentTabContent();
    });
  });

  // Alternador do Modo Bypass 18+
  const bypassPill = document.getElementById('bypass-pill');
  if (bypassPill) {
    bypassPill.addEventListener('click', () => {
      State.bypass18 = !State.bypass18;
      updateBypassUI();
      renderContentGrid();
      showToast(State.bypass18 ? 'Modo Sem Censura (+18 Liberado) Ativo' : 'Avisos de Conteúdo 18+ Ativados', 'info');
    });
  }

  // Busca Rápida no Topo
  const searchInput = document.getElementById('search-input');
  const searchDropdown = document.getElementById('search-dropdown');
  let searchTimeout = null;

  searchInput.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    const q = e.target.value.trim();
    if (q.length < 2) {
      searchDropdown.style.display = 'none';
      return;
    }
    searchTimeout = setTimeout(async () => {
      try {
        const resp = await fetch(`/api/search/games?q=${encodeURIComponent(q)}&platform=${State.platform}`);
        const data = await resp.json();
        renderSearchDropdown(data.resultados || []);
      } catch (err) {
        console.error('Erro na pesquisa:', err);
      }
    }, 280);
  });

  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
      searchDropdown.style.display = 'none';
    }
  });

  // Botões de Período (24h, 7d, 30d, all)
  document.querySelectorAll('.period-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.period-pill').forEach(b => b.classList.remove('active'));
      e.currentTarget.classList.add('active');
      State.period = e.currentTarget.dataset.period;
      if (State.currentTab === 'clips') fetchCurrentTabContent();
    });
  });

  // Filtros
  document.getElementById('lang-select')?.addEventListener('change', (e) => {
    State.language = e.target.value;
    fetchCurrentTabContent();
  });

  document.getElementById('sort-select')?.addEventListener('change', (e) => {
    State.sort = e.target.value;
    if (State.currentTab === 'clips' || State.currentTab === 'videos') fetchCurrentTabContent();
  });

  document.getElementById('btn-refresh-content')?.addEventListener('click', () => {
    fetchCurrentTabContent();
    showToast('Atualizando conteúdo...', 'info');
  });

  // Botão Atualizar Mais Populares
  document.getElementById('btn-load-top-games')?.addEventListener('click', loadTopGamesDynamic);

  // Modo Seleção em Lote
  const btnBatch = document.getElementById('btn-batch-toggle');
  if (btnBatch) {
    btnBatch.addEventListener('click', () => {
      State.batchMode = !State.batchMode;
      btnBatch.classList.toggle('active', State.batchMode);
      document.body.classList.toggle('batch-mode-active', State.batchMode);
      updateBatchUI();
    });
  }

  // Barra Flutuante de Seleção em Lote
  document.getElementById('btn-batch-download')?.addEventListener('click', () => {
    const clipsArray = Array.from(State.selectedClips.values());
    if (clipsArray.length === 0) return;
    solicitarConfirmacaoCortes(clipsArray, true);
  });
  document.getElementById('btn-batch-clear')?.addEventListener('click', clearBatchSelection);

  // Modal de Confirmação de Cortes
  document.getElementById('btn-confirm-yes-cuts')?.addEventListener('click', () => responderConfirmacaoCortes('auto_cuts'));
  document.getElementById('btn-confirm-no-cuts')?.addEventListener('click', () => responderConfirmacaoCortes('download_only'));
  document.getElementById('btn-confirm-studio')?.addEventListener('click', () => responderConfirmacaoCortes('studio'));

  // Drawer de Downloads
  document.getElementById('btn-open-downloads')?.addEventListener('click', openDownloadsDrawer);
  document.getElementById('btn-close-drawer')?.addEventListener('click', closeDownloadsDrawer);

  // Modal de Configurações
  document.getElementById('btn-open-settings')?.addEventListener('click', openSettingsModal);
  document.getElementById('btn-close-settings')?.addEventListener('click', closeSettingsModal);
  document.getElementById('btn-save-settings')?.addEventListener('click', saveSettings);

  // Modal do Player
  document.getElementById('player-close-btn')?.addEventListener('click', closePlayerModal);
  document.getElementById('player-switch-mode-btn')?.addEventListener('click', togglePlayerMode);
  document.getElementById('player-download-btn')?.addEventListener('click', () => {
    if (State.currentPlayingMedia) {
      solicitarConfirmacaoCortes(State.currentPlayingMedia, false);
    }
  });
  document.getElementById('player-miner-btn')?.addEventListener('click', () => {
    if (State.currentPlayingMedia) {
      executarDownloadFinal(State.currentPlayingMedia, true, false);
    }
  });
}

// Troca de Plataforma
function switchPlatform(platform) {
  State.platform = platform;
  
  document.querySelectorAll('.platform-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.platform === platform);
  });

  const indicator = document.getElementById('platform-indicator');
  if (indicator) indicator.textContent = platform.toUpperCase();

  if (platform === 'kick') {
    document.documentElement.style.setProperty('--accent-active', 'var(--kick-green)');
    document.documentElement.style.setProperty('--accent-glow', 'var(--kick-green-glow)');
  } else {
    document.documentElement.style.setProperty('--accent-active', 'var(--twitch-purple)');
    document.documentElement.style.setProperty('--accent-glow', 'var(--twitch-purple-glow)');
  }

  showToast(`Plataforma alterada para ${platform.toUpperCase()}`, 'info');
  fetchCurrentTabContent();
}

// Carregar Catálogo de Jogos
async function loadFeaturedGames() {
  try {
    const resp = await fetch('/api/games');
    const data = await resp.json();
    State.featuredGames = data.games || [];
    renderGamesShelf();

    if (State.featuredGames.length > 0) {
      selectGame(State.featuredGames[0]);
    }
  } catch (err) {
    console.error('Erro ao carregar jogos:', err);
    showToast('Falha ao obter lista de jogos', 'error');
  }
}

// Carregar Dinamicamente Jogos Mais Populares do Mundo
async function loadTopGamesDynamic() {
  showToast('Buscando jogos mais assistidos do mundo...', 'info');
  try {
    const resp = await fetch(`/api/games/top?platform=${State.platform}`);
    const data = await resp.json();
    if (data.sucesso && data.games.length > 0) {
      State.featuredGames = data.games;
      renderGamesShelf();
      showToast(`${data.games.length} jogos populares carregados!`, 'success');
    }
  } catch (err) {
    console.error('Erro ao buscar top games:', err);
  }
}

// Renderiza Shelf de Jogos (Mais Capas como na Twitch)
function renderGamesShelf() {
  const container = document.getElementById('games-shelf');
  if (!container) return;
  container.innerHTML = '';

  State.featuredGames.forEach(game => {
    const card = document.createElement('div');
    card.className = `game-card ${State.currentGame && State.currentGame.id === game.id ? 'active' : ''}`;
    card.dataset.gameId = game.id;
    
    card.innerHTML = `
      <div class="game-card-img-wrap">
        <img src="${game.box_art || 'https://via.placeholder.com/150x200?text=Game'}" alt="${game.name}" loading="lazy" />
        <span class="game-badge">${game.badge || 'Popular'}</span>
        <div class="game-active-check">✓</div>
      </div>
      <div class="game-card-info">
        <div class="game-card-name" title="${game.name}">${game.name}</div>
        <div class="game-card-viewers">${game.viewers ? formatLiveViewers(game.viewers) : 'Ao Vivo'}</div>
      </div>
    `;

    card.addEventListener('click', () => selectGame(game));
    container.appendChild(card);
  });
}

// Seleciona um Jogo
function selectGame(game) {
  State.currentGame = game;

  document.querySelectorAll('.game-card').forEach(c => {
    c.classList.toggle('active', c.dataset.gameId === game.id);
  });

  const bannerThumb = document.getElementById('active-game-thumb');
  const bannerTitle = document.getElementById('active-game-title');
  const bannerTags = document.getElementById('active-game-tags');
  const viewersTag = document.getElementById('active-game-viewers-tag');

  if (bannerThumb) bannerThumb.src = game.box_art || '';
  if (bannerTitle) bannerTitle.textContent = game.name;
  if (viewersTag && game.viewers) {
    viewersTag.textContent = `🔥 Mais de ${formatLiveViewers(game.viewers)} acompanhando`;
  }
  if (bannerTags && game.tags) {
    bannerTags.innerHTML = game.tags.map(t => `<span class="banner-tag">${t}</span>`).join('');
  }

  // Garantir que ao clicar em qualquer categoria do catálogo, NÃO exiba canais ao vivo,
  // mas sim a categoria de Clipes e Cortes virais ou Vídeos mais assistidos
  if (State.currentTab === 'lives') {
    State.currentTab = 'clips';
    document.querySelectorAll('.content-tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === 'clips');
    });
    const periodWrap = document.getElementById('period-pills-wrap');
    const sortSelect = document.getElementById('sort-select');
    if (periodWrap) periodWrap.style.display = 'flex';
    if (sortSelect) {
      sortSelect.style.display = 'block';
      sortSelect.innerHTML = `
        <option value="VIEWS_DESC" selected>🔥 Mais Visualizados (Ranking)</option>
        <option value="TRENDING">⚡ Em Alta (Trending)</option>
      `;
      State.sort = 'VIEWS_DESC';
    }
  }

  fetchCurrentTabContent();
}

// Renderiza Resultados da Pesquisa Rápida
function renderSearchDropdown(items) {
  const dropdown = document.getElementById('search-dropdown');
  dropdown.innerHTML = '';

  if (items.length === 0) {
    dropdown.innerHTML = '<div style="padding: 12px; color: var(--text-muted); font-size: 13px;">Nenhum jogo encontrado.</div>';
    dropdown.style.display = 'block';
    return;
  }

  items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'search-item';
    row.innerHTML = `
      <img src="${item.box_art || 'https://via.placeholder.com/32x42?text=Game'}" alt="" />
      <div>
        <div style="font-size: 13px; font-weight: 700; color: #fff;">${item.name}</div>
        <div style="font-size: 11px; color: var(--text-muted);">${State.platform.toUpperCase()}</div>
      </div>
    `;

    row.addEventListener('click', () => {
      dropdown.style.display = 'none';
      document.getElementById('search-input').value = item.name;

      const customGame = {
        id: item.id,
        name: item.name,
        twitch_name: item.name,
        kick_slug: item.id || item.name.toLowerCase().replace(/\s+/g, '-'),
        box_art: item.box_art,
        badge: 'Pesquisa',
        tags: ['Comunidade']
      };

      selectGame(customGame);
    });

    dropdown.appendChild(row);
  });

  dropdown.style.display = 'block';
}

// Busca Conteúdo da Aba Atual (Clipes vs Lives ao Vivo)
async function fetchCurrentTabContent() {
  if (!State.currentGame) return;

  const grid = document.getElementById('content-grid');
  if (!grid) return;

  // Skeletons de Loading
  grid.innerHTML = Array(8).fill(0).map(() => `
    <div class="media-card" style="opacity: 0.6; pointer-events: none;">
      <div class="media-thumb-wrap" style="background: #1c212b;"></div>
      <div class="card-info">
        <div style="width: 40px; height: 40px; border-radius: 50%; background: #272d3b;"></div>
        <div style="flex: 1;">
          <div style="height: 14px; background: #272d3b; border-radius: 4px; margin-bottom: 6px;"></div>
          <div style="height: 11px; width: 60%; background: #272d3b; border-radius: 4px;"></div>
        </div>
      </div>
    </div>
  `).join('');

  const gameParam = State.platform === 'twitch' ? State.currentGame.twitch_name : State.currentGame.kick_slug;

  if (State.currentTab === 'lives') {
    // ABA LIVES AO VIVO
    try {
      const url = `/api/streams?platform=${State.platform}&game=${encodeURIComponent(gameParam)}&limit=40`;
      const resp = await fetch(url);
      const data = await resp.json();

      if (!data.sucesso) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 50px; text-align: center; color: var(--text-secondary);">
            <div style="font-size: 32px; margin-bottom: 12px;">📡</div>
            <div style="font-size: 16px; font-weight: 700; color: #fff;">${data.erro || 'Nenhuma live ao vivo encontrada no momento'}</div>
          </div>
        `;
        return;
      }

      State.lives = data.lives || [];
      renderLivesGrid();
    } catch (err) {
      console.error('Erro ao buscar lives:', err);
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 50px; text-align: center; color: var(--text-secondary);">
          <div style="font-size: 32px; margin-bottom: 12px;">⚠️</div>
          <div style="font-size: 16px; font-weight: 700; color: #fff;">Falha de conexão ao carregar transmissões ao vivo</div>
        </div>
      `;
    }
  } else if (State.currentTab === 'videos') {
    // ABA VÍDEOS COMPLETOS E VODS DA CATEGORIA
    try {
      const url = `/api/videos?platform=${State.platform}&game=${encodeURIComponent(gameParam)}&sort=${State.sort === 'TRENDING' ? 'TRENDING' : 'VIEWS'}&languages=${State.language}&limit=60`;
      const resp = await fetch(url);
      const data = await resp.json();

      if (!data.sucesso) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 50px; text-align: center; color: var(--text-secondary);">
            <div style="font-size: 32px; margin-bottom: 12px;">📹</div>
            <div style="font-size: 16px; font-weight: 700; color: #fff;">${data.erro || 'Nenhum vídeo completo disponível'}</div>
          </div>
        `;
        return;
      }

      State.videos = data.videos || [];
      renderVideosGrid();
    } catch (err) {
      console.error('Erro ao buscar vídeos:', err);
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 50px; text-align: center; color: var(--text-secondary);">
          <div style="font-size: 32px; margin-bottom: 12px;">⚠️</div>
          <div style="font-size: 16px; font-weight: 700; color: #fff;">Falha de conexão ao carregar vídeos</div>
        </div>
      `;
    }
  } else {
    // ABA CLIPES E CORTES POPULARES
    try {
      const url = `/api/clips?platform=${State.platform}&game=${encodeURIComponent(gameParam)}&period=${State.period}&sort=${State.sort}&languages=${State.language}&limit=60`;
      const resp = await fetch(url);
      const data = await resp.json();

      if (!data.sucesso) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 50px; text-align: center; color: var(--text-secondary);">
            <div style="font-size: 32px; margin-bottom: 12px;">🎬</div>
            <div style="font-size: 16px; font-weight: 700; color: #fff;">${data.erro || 'Nenhum clipe disponível'}</div>
          </div>
        `;
        return;
      }

      State.clips = data.clipes || [];
      renderClipsGrid();
    } catch (err) {
      console.error('Erro ao buscar clipes:', err);
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 50px; text-align: center; color: var(--text-secondary);">
          <div style="font-size: 32px; margin-bottom: 12px;">⚠️</div>
          <div style="font-size: 16px; font-weight: 700; color: #fff;">Falha de conexão ao carregar clipes</div>
        </div>
      `;
    }
  }
}

// Renderiza Grid de Lives Ao Vivo ("Assistir quem tá fazendo live do jogo")
function renderLivesGrid() {
  const grid = document.getElementById('content-grid');
  if (!grid) return;
  grid.innerHTML = '';

  if (State.lives.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 60px; text-align: center; color: var(--text-secondary);">
        <div style="font-size: 40px; margin-bottom: 14px;">📡</div>
        <div style="font-size: 17px; font-weight: 700; color: #fff;">Nenhum streamer transmitindo este jogo no momento</div>
        <div style="font-size: 13px; margin-top: 8px;">Tente alternar para a Twitch ou verificar a aba de Clipes.</div>
      </div>
    `;
    return;
  }

  State.lives.forEach(live => {
    const card = document.createElement('div');
    card.className = 'media-card';

    card.innerHTML = `
      <div class="media-thumb-wrap">
        <img class="media-thumb-img" src="${live.thumbnail || 'https://via.placeholder.com/320x180?text=Ao+Vivo'}" alt="${live.title}" loading="lazy" />
        <span class="live-stream-badge">
          <span class="live-dot" style="background: #fff;"></span> AO VIVO
        </span>
        <span class="views-badge">👥 ${formatLiveViewers(live.viewers)}</span>
        
        <div class="play-hover-overlay">
          <div class="play-circle-btn">▶</div>
        </div>
      </div>

      <div class="card-info">
        <img class="streamer-avatar" src="${live.streamer.avatar || 'https://via.placeholder.com/40'}" alt="${live.streamer.name}" />
        <div class="card-meta">
          <div class="card-title" title="${live.title}">${live.title}</div>
          <div class="streamer-name">
            ${live.streamer.name}
            <span class="verified-icon">✓</span>
          </div>
          <div class="card-subtext">${live.game_name} • ${live.platform.toUpperCase()}</div>
        </div>
      </div>

      <div class="card-actions">
        <button class="btn-card-action btn-play-live" style="background: var(--accent-active); color: #fff;">
          ▶ Assistir Live
        </button>
        <button class="btn-card-action btn-open-channel">
          🔗 Canal
        </button>
      </div>
    `;

    card.querySelector('.media-thumb-wrap').addEventListener('click', () => openLivePlayer(live));
    card.querySelector('.btn-play-live').addEventListener('click', () => openLivePlayer(live));
    card.querySelector('.btn-open-channel').addEventListener('click', () => {
      window.open(live.streamer.channel_url, '_blank');
    });

    grid.appendChild(card);
  });
}

// Renderiza Grid de Clipes & Cortes Populares
function renderClipsGrid() {
  const grid = document.getElementById('content-grid');
  if (!grid) return;
  grid.innerHTML = '';

  if (State.clips.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 60px; text-align: center; color: var(--text-secondary);">
        <div style="font-size: 40px; margin-bottom: 14px;">✂️</div>
        <div style="font-size: 17px; font-weight: 700; color: #fff;">Nenhum clipe encontrado para estes filtros</div>
        <div style="font-size: 13px; margin-top: 8px;">Mude para "Todo o Período" ou escolha outro idioma.</div>
      </div>
    `;
    return;
  }

  State.clips.forEach((clip, idx) => {
    const isSelected = State.selectedClips.has(clip.id);
    const card = document.createElement('div');
    card.className = `media-card ${isSelected ? 'selected' : ''}`;
    card.dataset.clipId = clip.id;

    const thumbStyle = (!State.bypass18 && clip.is_mature) ? 'filter: blur(12px);' : '';
    const rank = clip.ranking || (idx + 1);

    card.innerHTML = `
      <input type="checkbox" class="clip-select-check" ${isSelected ? 'checked' : ''} />
      <div class="media-thumb-wrap">
        <img class="media-thumb-img" src="${clip.thumbnail}" alt="${clip.title}" loading="lazy" style="${thumbStyle}" />
        ${getRankingBadge(idx, rank)}
        <span class="duration-badge" style="left: auto; right: 8px;">⏱️ ${formatDuration(clip.duration)}</span>
        <span class="views-badge">👁️ ${formatViews(clip.views)}</span>
        <span class="time-badge">${formatTimeAgo(clip.created_at)}</span>
        ${State.bypass18 ? '<span class="uncensored-tag" style="top: 36px; right: 8px;">🔓 Sem Censura</span>' : ''}
        
        <div class="play-hover-overlay">
          <div class="play-circle-btn">▶</div>
        </div>
      </div>

      <div class="card-info">
        <img class="streamer-avatar" src="${clip.broadcaster.avatar || 'https://via.placeholder.com/38'}" alt="${clip.broadcaster.name}" />
        <div class="card-meta">
          <div class="card-title" title="${clip.title}">${clip.title}</div>
          <div class="streamer-name">
            ${clip.broadcaster.name}
            <span class="verified-icon">✓</span>
          </div>
          <div class="card-monitoring-metrics">
            <span class="metric-views-highlight">👁️ ${formatViews(clip.views)}</span>
            <span>•</span>
            <span class="metric-rank-highlight">#${rank} no ranking</span>
            <span>•</span>
            <span class="metric-duration-highlight" style="color: #38bdf8; font-weight: 700;">⏱️ ${formatDuration(clip.duration)}</span>
          </div>
          ${clip.curator && clip.curator.name ? `<div class="card-subtext" style="margin-top: 2px;">Criado por ${clip.curator.name}</div>` : ''}
        </div>
      </div>

      <div class="card-actions">
        <button class="btn-card-action btn-play">▶ Assistir</button>
        <button class="btn-card-action btn-download">⬇ Baixar</button>
        <button class="btn-card-action btn-miner" title="Baixa e gera cortes automáticos organizados por categoria">✂ Cortes IA</button>
      </div>
    `;

    const check = card.querySelector('.clip-select-check');
    check.addEventListener('change', (e) => {
      toggleClipSelection(clip, e.target.checked);
    });

    card.querySelector('.media-thumb-wrap').addEventListener('click', () => {
      if (State.batchMode) {
        check.checked = !check.checked;
        toggleClipSelection(clip, check.checked);
        return;
      }
      openClipPlayer(clip);
    });

    card.querySelector('.btn-play').addEventListener('click', () => openClipPlayer(clip));
    card.querySelector('.btn-download').addEventListener('click', () => solicitarConfirmacaoCortes(clip, false));
    card.querySelector('.btn-miner').addEventListener('click', () => executarDownloadFinal(clip, true, false));

    grid.appendChild(card);
  });
}

// Renderiza Grid de Vídeos e VODs Completos Mais Assistidos
function renderVideosGrid() {
  const grid = document.getElementById('content-grid');
  if (!grid) return;
  grid.innerHTML = '';

  if (State.videos.length === 0) {
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 60px; text-align: center; color: var(--text-secondary);">
        <div style="font-size: 40px; margin-bottom: 14px;">📹</div>
        <div style="font-size: 17px; font-weight: 700; color: #fff;">Nenhum vídeo completo encontrado para esta categoria</div>
        <div style="font-size: 13px; margin-top: 8px;">Tente alterar o idioma ou o critério de ordenação.</div>
      </div>
    `;
    return;
  }

  State.videos.forEach((video, idx) => {
    const isSelected = State.selectedClips.has(video.id);
    const card = document.createElement('div');
    card.className = `media-card ${isSelected ? 'selected' : ''}`;
    card.dataset.clipId = video.id;

    const thumbStyle = (!State.bypass18 && video.is_mature) ? 'filter: blur(12px);' : '';
    const rank = video.ranking || (idx + 1);

    card.innerHTML = `
      <input type="checkbox" class="clip-select-check" ${isSelected ? 'checked' : ''} />
      <div class="media-thumb-wrap">
        <img class="media-thumb-img" src="${video.thumbnail}" alt="${video.title}" loading="lazy" style="${thumbStyle}" />
        ${getRankingBadge(idx, rank)}
        <span class="duration-badge" style="left: auto; right: 8px;">⏱️ ${formatDuration(video.duration)}</span>
        <span class="views-badge">👁️ ${formatViews(video.views)}</span>
        <span class="time-badge">${formatTimeAgo(video.created_at)}</span>
        ${State.bypass18 ? '<span class="uncensored-tag" style="top: 36px; right: 8px;">🔓 Sem Censura</span>' : ''}
        
        <div class="play-hover-overlay">
          <div class="play-circle-btn">▶</div>
        </div>
      </div>

      <div class="card-info">
        <img class="streamer-avatar" src="${video.broadcaster.avatar || 'https://via.placeholder.com/38'}" alt="${video.broadcaster.name}" />
        <div class="card-meta">
          <div class="card-title" title="${video.title}">${video.title}</div>
          <div class="streamer-name">
            ${video.broadcaster.name}
            <span class="verified-icon">✓</span>
          </div>
          <div class="card-monitoring-metrics">
            <span class="metric-views-highlight">👁️ ${formatViews(video.views)}</span>
            <span>•</span>
            <span class="metric-rank-highlight">#${rank} Mais Assistido</span>
            <span>•</span>
            <span class="metric-duration-highlight" style="color: #38bdf8; font-weight: 700;">⏱️ ${formatDuration(video.duration)}</span>
          </div>
          <div class="card-subtext" style="margin-top: 2px;">VOD Completo • ${video.platform.toUpperCase()}</div>
        </div>
      </div>

      <div class="card-actions">
        <button class="btn-card-action btn-play">▶ Assistir VOD</button>
        <button class="btn-card-action btn-download">⬇ Baixar Vídeo</button>
        <button class="btn-card-action btn-miner" title="Baixa o vídeo e extrai cortes verticais inteligentes com IA">✂ Minerar Cortes</button>
      </div>
    `;

    const check = card.querySelector('.clip-select-check');
    check.addEventListener('change', (e) => {
      toggleClipSelection(video, e.target.checked);
    });

    card.querySelector('.media-thumb-wrap').addEventListener('click', () => {
      if (State.batchMode) {
        check.checked = !check.checked;
        toggleClipSelection(video, check.checked);
        return;
      }
      openClipPlayer(video);
    });

    card.querySelector('.btn-play').addEventListener('click', () => openClipPlayer(video));
    card.querySelector('.btn-download').addEventListener('click', () => solicitarConfirmacaoCortes(video, false));
    card.querySelector('.btn-miner').addEventListener('click', () => executarDownloadFinal(video, true, false));

    grid.appendChild(card);
  });
}

function renderContentGrid() {
  if (State.currentTab === 'lives') {
    renderLivesGrid();
  } else if (State.currentTab === 'videos') {
    renderVideosGrid();
  } else {
    renderClipsGrid();
  }
}

// Seleção de Clipes em Lote
function toggleClipSelection(clip, isSelected) {
  if (isSelected) {
    State.selectedClips.set(clip.id, clip);
  } else {
    State.selectedClips.delete(clip.id);
  }

  const card = document.querySelector(`.media-card[data-clip-id="${clip.id}"]`);
  if (card) {
    card.classList.toggle('selected', isSelected);
  }

  updateBatchUI();
}

function updateBatchUI() {
  const bar = document.getElementById('batch-floating-bar');
  const countSpan = document.getElementById('batch-count-num');
  const total = State.selectedClips.size;

  if (countSpan) countSpan.textContent = total;

  if (bar) {
    if (total > 0 && State.batchMode) {
      bar.classList.add('visible');
    } else {
      bar.classList.remove('visible');
    }
  }
}

function clearBatchSelection() {
  State.selectedClips.clear();
  document.querySelectorAll('.media-card').forEach(c => c.classList.remove('selected'));
  document.querySelectorAll('.clip-select-check').forEach(c => c.checked = false);
  updateBatchUI();
  showToast('Seleção desmarcada', 'info');
}

// ==========================================================================
// FUNÇÃO DE CONFIRMAÇÃO: DESEJA GERAR CORTES AUTOMÁTICOS COM IA?
// ==========================================================================
function solicitarConfirmacaoCortes(itemOuArray, isBatch = false) {
  State.pendingDownloadAction = { item: itemOuArray, isBatch };

  // Se o usuário já tiver preferência salva em settings, executa direto sem perguntar
  if (State.rememberCutsChoice !== null) {
    executarDownloadFinal(itemOuArray, State.rememberCutsChoice, isBatch);
    return;
  }

  const modal = document.getElementById('cuts-confirm-modal');
  const platSpan = document.getElementById('confirm-platform-name');
  const streamerSpan = document.getElementById('confirm-streamer-name');

  if (platSpan) {
    platSpan.textContent = State.platform.toUpperCase();
  }
  if (streamerSpan) {
    if (!isBatch && itemOuArray && itemOuArray.broadcaster && itemOuArray.broadcaster.name) {
      streamerSpan.textContent = itemOuArray.broadcaster.name;
    } else {
      streamerSpan.textContent = '[Streamer_do_Vídeo]';
    }
  }
  if (modal) modal.classList.add('active');
}

function selecionarLayoutCard(layout) {
  const hiddenInput = document.getElementById('select-cuts-layout');
  if (hiddenInput) hiddenInput.value = layout;

  document.querySelectorAll('.layout-preview-grid .layout-card').forEach(card => {
    if (card.getAttribute('data-layout') === layout) {
      card.classList.add('active');
    } else {
      card.classList.remove('active');
    }
  });
}
window.selecionarLayoutCard = selecionarLayoutCard;

function abrirNoStudio(caminhoArquivoEncoded) {
  const caminho = decodeURIComponent(caminhoArquivoEncoded);
  window.open(`/studio?video=${encodeURIComponent(caminho)}`, '_blank');
}
window.abrirNoStudio = abrirNoStudio;

function responderConfirmacaoCortes(modoAcao) {
  const modal = document.getElementById('cuts-confirm-modal');
  if (modal) modal.classList.remove('active');

  const desejaCortes = (modoAcao === true || modoAcao === 'auto_cuts');
  const abrirStudio = (modoAcao === 'studio');

  const remember = document.getElementById('check-remember-cuts')?.checked;
  if (remember) {
    State.rememberCutsChoice = desejaCortes;
    fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_cortes_padrao: desejaCortes })
    });
  }

  const selectLayout = document.getElementById('select-cuts-layout');
  const layoutModo = selectLayout ? selectLayout.value : 'SPLIT_PRO';

  const selectCuts = document.getElementById('select-cuts-per-hour');
  const cortesPorHora = selectCuts ? (parseInt(selectCuts.value) || 10) : 10;

  const radioModo = document.querySelector('input[name="miner-mode"]:checked');
  const modoMineracao = radioModo ? radioModo.value : 'por_hora';

  let opcoesCortes = {
    modo_mineracao: modoMineracao,
    cortes_por_hora: cortesPorHora,
    layout_modo: layoutModo,
    abrir_studio: abrirStudio
  };

  if (State.pendingDownloadAction) {
    const { item, isBatch } = State.pendingDownloadAction;
    executarDownloadFinal(item, desejaCortes, isBatch, opcoesCortes);
    State.pendingDownloadAction = null;
  }
}

async function executarDownloadFinal(itemOuArray, gerarCortes, isBatch = false, opcoesCortes = {}) {
  const modoMineracao = opcoesCortes.modo_mineracao || 'por_hora';
  const cortesPorHora = opcoesCortes.cortes_por_hora || 10;
  const layoutModo = opcoesCortes.layout_modo || 'SPLIT_PRO';

  if (isBatch) {
    const clipsArray = Array.isArray(itemOuArray) ? itemOuArray : Array.from(State.selectedClips.values());
    if (clipsArray.length === 0) return;

    try {
      const payload = {
        clips: clipsArray.map((c, idx) => ({
          clip_id: c.id,
          titulo: c.title,
          streamer: c.broadcaster ? c.broadcaster.name : (c.streamer ? c.streamer.name : 'Streamer'),
          jogo: c.game_name || State.currentGame.name,
          url: c.url,
          platform: c.platform,
          thumbnail: c.thumbnail,
          views: formatViews(c.views) || (c.views ? String(c.views) : ''),
          ranking: c.ranking || (idx + 1),
          gerar_cortes: gerarCortes,
          modo_mineracao: modoMineracao,
          cortes_por_hora: cortesPorHora,
          layout_modo: layoutModo
        })),
        gerar_cortes: gerarCortes,
        modo_mineracao: modoMineracao,
        cortes_por_hora: cortesPorHora,
        layout_modo: layoutModo
      };

      const resp = await fetch('/api/download/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const res = await resp.json();
      if (res.sucesso) {
        showToast(`Iniciando lote de ${res.total} vídeos! ${gerarCortes ? `(Mineração IA: ${modoMineracao === 'por_hora' ? '10 cortes/hora' : 'Top Geral'})` : 'Apenas originais.'}`, 'success');
        clearBatchSelection();
        openDownloadsDrawer();
      }
    } catch (err) {
      console.error('Erro no download em lote:', err);
    }
  } else {
    // Download Individual
    const clip = itemOuArray;
    const rank = clip.ranking || (State.clips.findIndex(x => x.id === clip.id) + 1) || 1;
    try {
      const payload = {
        clip_id: clip.id,
        titulo: clip.title,
        streamer: clip.broadcaster ? clip.broadcaster.name : (clip.streamer ? clip.streamer.name : 'Streamer'),
        jogo: clip.game_name || State.currentGame.name,
        url: clip.url || (clip.streamer ? clip.streamer.channel_url : ''),
        platform: clip.platform,
        thumbnail: clip.thumbnail,
        views: formatViews(clip.views) || (clip.views ? String(clip.views) : ''),
        ranking: rank,
        gerar_cortes: gerarCortes,
        modo_mineracao: modoMineracao,
        cortes_por_hora: cortesPorHora,
        layout_modo: layoutModo
      };

      const resp = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const res = await resp.json();
      if (res.sucesso) {
        showToast(res.mensagem, 'success');
        if (opcoesCortes.abrir_studio && res.task_id) {
          State.pendingStudioTasks = State.pendingStudioTasks || new Set();
          State.pendingStudioTasks.add(res.task_id);
          showToast('📐 Vídeo sendo baixado! O Studio abrirá automaticamente assim que estiver pronto.', 'info');
        }
        openDownloadsDrawer();
      }
    } catch (err) {
      console.error('Erro no download:', err);
      showToast('Erro ao iniciar download', 'error');
    }
  }
}

let currentHlsInstance = null;
let currentPlayingTimeout = null;

function playStreamInVideo(videoElement, spinnerElement, streamUrl, onFailCallback) {
  if (currentHlsInstance) {
    try { currentHlsInstance.destroy(); } catch (e) {}
    currentHlsInstance = null;
  }
  if (currentPlayingTimeout) {
    clearTimeout(currentPlayingTimeout);
    currentPlayingTimeout = null;
  }

  let hasStarted = false;
  currentPlayingTimeout = setTimeout(() => {
    if (!hasStarted) {
      console.warn('[PLAYER] Timeout de 3.5s ao carregar fluxo nativo. Acionando fallback...');
      if (onFailCallback) onFailCallback('timeout');
    }
  }, 3500);

  function markLoaded() {
    if (!hasStarted) {
      hasStarted = true;
      if (currentPlayingTimeout) {
        clearTimeout(currentPlayingTimeout);
        currentPlayingTimeout = null;
      }
      spinnerElement.style.display = 'none';
      videoElement.play().catch(e => console.log('Autoplay info:', e));
    }
  }

  videoElement.style.display = 'block';
  videoElement.onloadeddata = markLoaded;
  videoElement.oncanplay = markLoaded;
  videoElement.onerror = (e) => {
    console.warn('[PLAYER] Erro nativo no elemento video:', e);
    if (currentPlayingTimeout) {
      clearTimeout(currentPlayingTimeout);
      currentPlayingTimeout = null;
    }
    if (onFailCallback) onFailCallback('video_error');
  };

  if (streamUrl && streamUrl.includes('.m3u8')) {
    if (typeof Hls !== 'undefined' && Hls.isSupported()) {
      currentHlsInstance = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 60
      });
      currentHlsInstance.loadSource(streamUrl);
      currentHlsInstance.attachMedia(videoElement);
      currentHlsInstance.on(Hls.Events.MANIFEST_PARSED, markLoaded);
      currentHlsInstance.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          console.warn('[PLAYER] HLS Fatal Error:', data.type, data.details);
          if (currentPlayingTimeout) {
            clearTimeout(currentPlayingTimeout);
            currentPlayingTimeout = null;
          }
          try { currentHlsInstance.destroy(); } catch (e) {}
          currentHlsInstance = null;
          if (onFailCallback) onFailCallback('hls_fatal');
        }
      });
      return;
    } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
      videoElement.src = streamUrl;
      return;
    }
  }

  // MP4 direto ou fallback
  videoElement.src = streamUrl;
}

// Player de Clipes e Vídeos (Sem Censura / +18 Liberado com Fallback Infalível)
async function openClipPlayer(clip) {
  State.currentPlayingMedia = clip;
  const modal = document.getElementById('player-modal');
  const title = document.getElementById('player-title');
  const streamer = document.getElementById('player-streamer');
  const video = document.getElementById('player-video');
  const iframe = document.getElementById('player-iframe');
  const spinner = document.getElementById('player-spinner');
  const tagStatus = document.getElementById('player-tag-status');

  if (!modal || !video) return;

  const streamerName = clip.broadcaster ? clip.broadcaster.name : (clip.streamer ? clip.streamer.name : 'Streamer');
  title.textContent = clip.title;
  streamer.textContent = `${streamerName} • 👁️ ${formatViews(clip.views)} • ⏱️ ${formatDuration(clip.duration)}`;
  document.getElementById('player-type-icon').textContent = clip.type === 'video' ? '📹' : '✂️';

  modal.classList.add('active');
  spinner.style.display = 'flex';
  video.style.display = 'none';
  iframe.style.display = 'none';
  video.pause();
  video.src = '';
  iframe.src = '';

  // Determina URL de Embed Oficial Twitch / Kick como fallback 100% infalível
  let embedUrl = '';
  const isVod = clip.type === 'video' || (clip.url && clip.url.includes('/videos/'));
  if (clip.platform === 'twitch') {
    if (isVod) {
      embedUrl = `https://player.twitch.tv/?video=${clip.id}&parent=localhost&parent=127.0.0.1&autoplay=true&muted=false`;
    } else {
      const slug = clip.slug || clip.id;
      embedUrl = `https://clips.twitch.tv/embed?clip=${slug}&parent=localhost&parent=127.0.0.1&autoplay=true&muted=false`;
    }
  } else {
    // Kick
    const slug = clip.broadcaster?.slug || clip.broadcaster?.name || clip.streamer?.name || 'kick';
    embedUrl = `https://player.kick.com/${slug}?autoplay=true&muted=false`;
  }

  State.currentPlayingEmbedUrl = embedUrl;
  State.currentPlayingStreamUrl = '';
  State.isCurrentEmbedActive = false;

  function switchToEmbed(reason = '') {
    console.log('[PLAYER] Alternando para embed oficial:', reason, embedUrl);
    if (currentHlsInstance) {
      try { currentHlsInstance.destroy(); } catch (e) {}
      currentHlsInstance = null;
    }
    if (currentPlayingTimeout) {
      clearTimeout(currentPlayingTimeout);
      currentPlayingTimeout = null;
    }
    video.pause();
    video.src = '';
    video.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = embedUrl;
    spinner.style.display = 'none';
    State.isCurrentEmbedActive = true;
    if (tagStatus) {
      tagStatus.textContent = '📺 Player Oficial Twitch (Embed Ativo)';
      tagStatus.style.background = 'rgba(147, 51, 234, 0.2)';
      tagStatus.style.borderColor = 'rgba(147, 51, 234, 0.5)';
      tagStatus.style.color = '#c084fc';
    }
  }

  try {
    const resp = await fetch(`/api/clip/stream?url=${encodeURIComponent(clip.url)}&platform=${clip.platform}`);
    const data = await resp.json();

    if (data.sucesso && data.stream_url && !data.is_embed) {
      State.currentPlayingStreamUrl = data.stream_url;
      if (data.embed_url) State.currentPlayingEmbedUrl = data.embed_url;

      video.style.display = 'block';
      iframe.style.display = 'none';
      State.isCurrentEmbedActive = false;
      if (tagStatus) {
        tagStatus.textContent = '🔓 Sem Restrições / +18 Liberado (Stream Direto)';
        tagStatus.style.background = 'rgba(34, 197, 94, 0.15)';
        tagStatus.style.borderColor = 'rgba(34, 197, 94, 0.4)';
        tagStatus.style.color = '#4ade80';
      }

      playStreamInVideo(video, spinner, data.stream_url, (reason) => {
        switchToEmbed(reason);
      });
    } else {
      if (data.embed_url) embedUrl = data.embed_url;
      switchToEmbed('api_requested_embed');
    }
  } catch (err) {
    console.error('Erro ao resolver stream:', err);
    switchToEmbed('fetch_error');
  }
}

// Player de Lives Ao Vivo ("Assistir quem tá fazendo live do jogo")
async function openLivePlayer(live) {
  State.currentPlayingMedia = live;
  const modal = document.getElementById('player-modal');
  const title = document.getElementById('player-title');
  const streamer = document.getElementById('player-streamer');
  const video = document.getElementById('player-video');
  const iframe = document.getElementById('player-iframe');
  const spinner = document.getElementById('player-spinner');
  const tagStatus = document.getElementById('player-tag-status');

  if (!modal) return;

  title.textContent = `🔴 AO VIVO: ${live.title}`;
  streamer.textContent = `${live.streamer.name} • 👥 ${formatLiveViewers(live.viewers)}`;
  document.getElementById('player-type-icon').textContent = '🔴';

  modal.classList.add('active');
  spinner.style.display = 'flex';
  video.pause();
  video.src = '';
  iframe.src = '';

  const defaultEmbed = live.platform === 'kick' 
    ? `https://player.kick.com/${live.streamer.login}?autoplay=true&muted=false`
    : `https://player.twitch.tv/?channel=${live.streamer.login}&parent=localhost&parent=127.0.0.1&autoplay=true&muted=false`;

  State.currentPlayingEmbedUrl = defaultEmbed;
  State.currentPlayingStreamUrl = '';
  State.isCurrentEmbedActive = false;

  function switchToEmbedLive(reason = '') {
    console.log('[LIVE PLAYER] Alternando para embed oficial:', reason);
    if (currentHlsInstance) {
      try { currentHlsInstance.destroy(); } catch (e) {}
      currentHlsInstance = null;
    }
    video.pause();
    video.src = '';
    video.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = State.currentPlayingEmbedUrl || defaultEmbed;
    spinner.style.display = 'none';
    State.isCurrentEmbedActive = true;
    if (tagStatus) {
      tagStatus.textContent = '🔴 Live Oficial (Player Embed)';
    }
  }

  if (live.platform === 'kick' && live.playback_url) {
    video.style.display = 'block';
    iframe.style.display = 'none';
    playStreamInVideo(video, spinner, live.playback_url, () => switchToEmbedLive('kick_hls_fail'));
  } else {
    try {
      const resp = await fetch(`/api/stream/live?channel=${live.streamer.login}&platform=twitch`);
      const data = await resp.json();

      if (data.sucesso && !data.is_embed && data.stream_url) {
        iframe.style.display = 'none';
        video.style.display = 'block';
        State.currentPlayingStreamUrl = data.stream_url;
        playStreamInVideo(video, spinner, data.stream_url, () => switchToEmbedLive('twitch_stream_fail'));
      } else {
        if (data.embed_url) State.currentPlayingEmbedUrl = data.embed_url;
        switchToEmbedLive('api_requested_embed');
      }
    } catch (err) {
      console.error('Erro ao carregar live:', err);
      switchToEmbedLive('fetch_error');
    }
  }
}

// Alternador Manual entre Player Nativo e Player Embed Oficial
function togglePlayerMode() {
  const video = document.getElementById('player-video');
  const iframe = document.getElementById('player-iframe');
  const spinner = document.getElementById('player-spinner');
  const tagStatus = document.getElementById('player-tag-status');

  if (State.isCurrentEmbedActive) {
    // Tenta voltar para o player nativo se houver stream direto
    if (State.currentPlayingStreamUrl) {
      iframe.style.display = 'none';
      iframe.src = '';
      video.style.display = 'block';
      State.isCurrentEmbedActive = false;
      playStreamInVideo(video, spinner, State.currentPlayingStreamUrl);
      if (tagStatus) tagStatus.textContent = '🔓 Player Nativo (Stream Direto)';
      showToast('Alternado para Player Nativo HTML5', 'info');
    } else {
      showToast('Fluxo nativo não disponível para este vídeo (utilizando Player Oficial)', 'warning');
    }
  } else {
    // Alterna para Embed Oficial
    if (State.currentPlayingEmbedUrl) {
      if (currentHlsInstance) {
        try { currentHlsInstance.destroy(); } catch (e) {}
        currentHlsInstance = null;
      }
      video.pause();
      video.src = '';
      video.style.display = 'none';
      iframe.style.display = 'block';
      iframe.src = State.currentPlayingEmbedUrl;
      spinner.style.display = 'none';
      State.isCurrentEmbedActive = true;
      if (tagStatus) tagStatus.textContent = '📺 Player Oficial Twitch/Kick (Embed)';
      showToast('Alternado para Player Oficial Embed', 'info');
    }
  }
}

function closePlayerModal() {
  const modal = document.getElementById('player-modal');
  const video = document.getElementById('player-video');
  const iframe = document.getElementById('player-iframe');
  const spinner = document.getElementById('player-spinner');

  if (currentPlayingTimeout) {
    clearTimeout(currentPlayingTimeout);
    currentPlayingTimeout = null;
  }
  if (currentHlsInstance) {
    try { currentHlsInstance.destroy(); } catch (e) {}
    currentHlsInstance = null;
  }
  if (video) {
    video.pause();
    video.src = '';
    video.style.display = 'none';
  }
  if (iframe) {
    iframe.src = '';
    iframe.style.display = 'none';
  }
  if (spinner) spinner.style.display = 'none';
  if (modal) modal.classList.remove('active');
  State.currentPlayingMedia = null;
  State.currentPlayingEmbedUrl = '';
  State.currentPlayingStreamUrl = '';
  State.isCurrentEmbedActive = false;
}

// Drawer de Downloads & Cortes IA
function openDownloadsDrawer() {
  document.getElementById('downloads-drawer')?.classList.add('open');
  fetchDownloads();
}

function closeDownloadsDrawer() {
  document.getElementById('downloads-drawer')?.classList.remove('open');
}

function startDownloadsPolling() {
  if (State.downloadsInterval) clearInterval(State.downloadsInterval);
  State.downloadsInterval = setInterval(fetchDownloads, 1800);
}

async function fetchDownloads() {
  try {
    const resp = await fetch('/api/downloads');
    const data = await resp.json();
    if (!data.sucesso) return;

    const badge = document.getElementById('downloads-badge');
    const tarefas = data.tarefas || [];

    // Checa se há alguma tarefa aguardando abertura automática do Studio
    if (State.pendingStudioTasks && State.pendingStudioTasks.size > 0) {
      tarefas.forEach(t => {
        if (State.pendingStudioTasks.has(t.id) && t.caminho_arquivo && (t.status === 'completed' || t.status === 'processing_cuts' || t.progress >= 100)) {
          State.pendingStudioTasks.delete(t.id);
          showToast(`Download de "${t.titulo}" concluído! Abrindo no Studio...`, 'success');
          window.open(`/studio?video=${encodeURIComponent(t.caminho_arquivo)}`, '_blank');
        }
      });
    }

    const ativas = tarefas.filter(t => t.status === 'downloading' || t.status === 'queued' || t.status === 'processing_cuts').length;

    if (badge) {
      badge.textContent = ativas;
      badge.style.display = ativas > 0 ? 'inline-block' : 'none';
    }

    const drawer = document.getElementById('downloads-drawer');
    if (drawer && drawer.classList.contains('open')) {
      renderDownloadsList(tarefas);
    }
  } catch (err) {
    // polling silencioso
  }
}

function getStageBadgeInfo(t) {
  const stage = t.stage || t.status;
  if (t.status === 'cancelled') {
    return { label: '🛑 Cancelado', color: '#6b7280', bg: 'rgba(107, 114, 128, 0.15)' };
  }
  if (t.status === 'error') {
    return { label: '❌ Erro', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)' };
  }
  if (t.status === 'completed') {
    return { label: t.cortes_gerados ? '🎉 Cortes Prontos!' : '✅ Download Concluído', color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)' };
  }
  switch (stage) {
    case 'downloading':
      return { label: `📥 Baixando (${t.progress}%)`, color: '#60a5fa', bg: 'rgba(96, 165, 250, 0.15)' };
    case 'starting_ia':
      return { label: '⚡ Iniciando IA Pro', color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.15)' };
    case 'audio_extract':
      return { label: '🎵 Extraindo Áudio', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)' };
    case 'whisper':
      return { label: '🎙️ Whisper IA Transcrevendo', color: '#a855f7', bg: 'rgba(168, 85, 247, 0.15)' };
    case 'mining':
      return { label: '🧠 Minerando Ganchos Virais', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' };
    case 'vision':
      return { label: '👁️ Rastreando Webcam YuNet', color: '#ec4899', bg: 'rgba(236, 72, 153, 0.15)' };
    case 'rendering':
      return { label: '🎬 Renderizando GPU AMF', color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.15)' };
    default:
      return { label: '⏳ Processando...', color: '#9146ff', bg: 'rgba(145, 70, 255, 0.15)' };
  }
}

function renderDownloadsList(tasks) {
  const list = document.getElementById('drawer-downloads-list');
  if (!list) return;

  if (tasks.length === 0) {
    list.innerHTML = `
      <div style="padding: 40px; text-align: center; color: var(--text-muted); font-size: 13px;">
        Nenhum download ou corte na fila.
      </div>
    `;
    return;
  }

  list.innerHTML = tasks.map(t => {
    const isProcessingCuts = t.status === 'processing_cuts';
    const isCompleted = t.status === 'completed';
    const isError = t.status === 'error';
    const isCancelled = t.status === 'cancelled';

    const stageBadge = getStageBadgeInfo(t);
    const cortes = t.cortes_prontos || [];
    const logs = t.logs || [];

    const pastaSalva = t.pasta_organizada || (isCompleted ? t.caminho_arquivo : '');

    return `
      <div class="download-task-card ${isCompleted ? 'task-completed' : ''}" data-task-id="${t.id}">
        <!-- Top bar with platform and stage badge -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span class="platform-indicator ${t.platform}" style="font-size: 10px; font-weight: 700; text-transform: uppercase; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);">
            ${t.platform}
          </span>
          <span style="font-size: 11px; font-weight: 700; color: ${stageBadge.color}; background: ${stageBadge.bg}; padding: 3px 8px; border-radius: 4px; border: 1px solid ${stageBadge.color}33;">
            ${stageBadge.label}
          </span>
        </div>

        <!-- Title -->
        <div class="task-title" title="${t.titulo}">${t.titulo}</div>

        <!-- Meta info -->
        <div class="task-sub" style="margin-bottom: 8px;">
          <span>📁 <strong>${t.jogo}</strong></span>
          <span>•</span>
          <span>👤 <strong>${t.streamer}</strong></span>
          ${t.ranking ? `<span style="background: rgba(245,158,11,0.2); color: #fbbf24; font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 3px;">#${t.ranking}</span>` : ''}
        </div>

        <!-- Real-time Status / Activity text -->
        <div style="font-size: 12px; color: ${isError ? '#f87171' : isCompleted ? '#34d399' : '#e2e8f0'}; margin-bottom: 8px; line-height: 1.4; display: flex; align-items: flex-start; gap: 6px; background: rgba(0,0,0,0.25); padding: 7px 10px; border-radius: 5px; border: 1px solid rgba(255,255,255,0.06);">
          <span>${isCompleted ? '✅' : isError ? '❌' : isCancelled ? '🛑' : '⚡'}</span>
          <span style="font-weight: 500;">${t.detalhe_status || 'Em processamento...'}</span>
        </div>
        
        <!-- Progress Bar with Percentage -->
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
          <div class="task-progress-bar" style="flex: 1; margin-bottom: 0;">
            <div class="task-progress-fill" style="width: ${t.progress}%; background: ${stageBadge.color};"></div>
          </div>
          <span style="font-size: 12px; font-weight: 700; color: ${stageBadge.color}; min-width: 38px; text-align: right;">${t.progress}%</span>
        </div>

        <!-- Speed & Mode info -->
        <div class="task-sub" style="font-size: 10px; margin-bottom: 8px;">
          <span>${t.speed && t.speed !== '--' ? `⚡ ${t.speed}` : ''}</span>
          <span>${t.eta && t.eta !== '--' ? `Restante: ${t.eta}` : (t.modo_mineracao === 'por_hora' ? '⏱️ Mineração por Hora' : '')}</span>
        </div>

        <!-- Folder Path display (shown as soon as folder is created or completed) -->
        ${pastaSalva ? `
          <div style="margin-bottom: 8px; font-size: 11px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); padding: 6px 8px; border-radius: 4px; word-break: break-all;">
            <span style="color: var(--text-secondary);">📂 Salvo em:</span>
            <div style="color: #38bdf8; font-family: monospace; font-size: 10.5px; margin-top: 2px;">${pastaSalva}</div>
          </div>
        ` : ''}

        <!-- Actions -->
        <div class="task-actions" style="margin-bottom: 8px;">
          ${pastaSalva ? `
            <button class="btn-task" style="background: rgba(168,85,247,0.15); border-color: rgba(168,85,247,0.3); color: #c084fc; font-weight: 600;" onclick="openDownloadFolder('${t.id}')">
              📂 Abrir Pasta
            </button>
          ` : ''}
          ${t.caminho_arquivo ? `
            <button class="btn-task" style="background: rgba(245,158,11,0.15); border-color: rgba(245,158,11,0.35); color: #fbbf24; font-weight: 600;" onclick="abrirNoStudio('${encodeURIComponent(t.caminho_arquivo)}')">
              📐 Abrir no Studio
            </button>
          ` : ''}
          ${(t.caminho_arquivo && (isCompleted || isProcessingCuts)) ? `
            <button class="btn-task" onclick="playLocalFile('${t.id}')">
              ▶ Vídeo Original
            </button>
          ` : ''}
          ${(!isCompleted && !isError && !isCancelled) ? `
            <button class="btn-task" style="color: #ef4444; border-color: rgba(239,68,68,0.3);" onclick="cancelDownloadTask('${t.id}')">
              ✕ Cancelar
            </button>
          ` : ''}
        </div>

        <!-- Stream de Cortes Prontos (Aparece em tempo real assim que cada corte/hora termina!) -->
        ${(cortes.length > 0) ? `
          <div style="margin-top: 10px; background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.25); border-radius: 6px; padding: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 12px; font-weight: 700; color: #34d399;">✂️ Cortes Prontos (${cortes.length})</span>
              <span style="font-size: 10px; background: rgba(16,185,129,0.2); color: #10b981; font-weight: 700; padding: 2px 6px; border-radius: 3px;">Liberado p/ Uso</span>
            </div>
            <div style="max-height: 140px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px;">
              ${cortes.map(c => `
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.3); padding: 5px 8px; border-radius: 4px; font-size: 11px;">
                  <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 170px;" title="${c.titulo}">
                    🎬 ${c.titulo} <span style="color: var(--text-muted); font-size: 10px;">(${c.duracao || 40}s)</span>
                  </span>
                  <div style="display: flex; gap: 4px;">
                    <button class="btn-task" style="padding: 2px 6px; font-size: 10px; background: rgba(255,255,255,0.08);" onclick="playCutFile('${t.id}', '${encodeURIComponent(c.path)}')">▶ Assistir</button>
                    <button class="btn-task" style="padding: 2px 6px; font-size: 10px; background: rgba(255,255,255,0.08);" onclick="openCutFolder('${t.id}', '${encodeURIComponent(c.pasta || pastaSalva)}')">📂 Ver</button>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Logs do Processo Expansíveis -->
        ${(logs.length > 0 && !isCompleted) ? `
          <details style="margin-top: 8px; font-size: 10.5px;">
            <summary style="cursor: pointer; color: var(--text-secondary); outline: none;">📋 Ver logs do script (${logs.length} linhas)</summary>
            <pre style="background: #0d0d12; border: 1px solid rgba(255,255,255,0.08); border-radius: 4px; padding: 6px; margin-top: 4px; font-family: monospace; font-size: 10px; color: #94a3b8; max-height: 90px; overflow-y: auto; white-space: pre-wrap;">${logs.slice(-6).join('\n')}</pre>
          </details>
        ` : ''}
      </div>
    `;
  }).join('');
}

async function openDownloadFolder(taskId) {
  await fetch(`/api/downloads/${taskId}/open-folder`, { method: 'POST' });
}

async function playLocalFile(taskId) {
  await fetch(`/api/downloads/${taskId}/play-local`, { method: 'POST' });
}

async function playCutFile(taskId, pathEnc) {
  const path = decodeURIComponent(pathEnc);
  await fetch(`/api/downloads/${taskId}/play-local`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ caminho: path })
  });
}

async function openCutFolder(taskId, pathEnc) {
  const path = decodeURIComponent(pathEnc);
  await fetch(`/api/downloads/${taskId}/open-folder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ caminho: path })
  });
}

async function sendToMinerEditor(taskId) {
  const resp = await fetch(`/api/downloads/${taskId}/send-to-miner`, { method: 'POST' });
  const data = await resp.json();
  if (data.sucesso) {
    showToast('Clipe aberto no Cortes IA Pro (gui_cortes.py)!', 'success');
  }
}

async function cancelDownloadTask(taskId) {
  try {
    const resp = await fetch(`/api/downloads/${taskId}/cancel`, { method: 'POST' });
    const data = await resp.json();
    if (data.sucesso) {
      showToast('Tarefa cancelada com sucesso.', 'info');
      fetchDownloads();
    }
  } catch (err) {
    console.error('Erro ao cancelar download:', err);
  }
}

// Configurações
async function loadSettings() {
  try {
    const resp = await fetch('/api/settings');
    const data = await resp.json();
    if (data.sucesso) {
      document.getElementById('setting-download-dir').value = data.download_dir || '';
      document.getElementById('setting-bypass-18').checked = data.bypass_18_plus !== false;
      document.getElementById('setting-auto-cortes').checked = data.auto_cortes_padrao === true;
      State.bypass18 = data.bypass_18_plus !== false;
      if (data.auto_cortes_padrao !== undefined) {
        State.rememberCutsChoice = data.auto_cortes_padrao;
      }
      updateBypassUI();
    }
  } catch (err) {
    console.error('Erro ao ler settings:', err);
  }
}

function openSettingsModal() {
  loadSettings();
  document.getElementById('settings-modal')?.classList.add('active');
}

function closeSettingsModal() {
  document.getElementById('settings-modal')?.classList.remove('active');
}

async function saveSettings() {
  const dir = document.getElementById('setting-download-dir').value.trim();
  const twitchToken = document.getElementById('setting-twitch-token').value.trim();
  const kickToken = document.getElementById('setting-kick-token').value.trim();
  const bypass = document.getElementById('setting-bypass-18').checked;
  const autoCortes = document.getElementById('setting-auto-cortes').checked;

  const payload = {
    download_dir: dir || undefined,
    twitch_auth_token: twitchToken || undefined,
    kick_auth_token: kickToken || undefined,
    bypass_18_plus: bypass,
    auto_cortes_padrao: autoCortes
  };

  try {
    const resp = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await resp.json();
    if (data.sucesso) {
      State.bypass18 = bypass;
      State.rememberCutsChoice = autoCortes;
      updateBypassUI();
      renderContentGrid();
      closeSettingsModal();
      showToast('Configurações salvas com sucesso!', 'success');
    }
  } catch (err) {
    showToast('Erro ao salvar configurações', 'error');
  }
}

function updateBypassUI() {
  const pill = document.getElementById('bypass-pill');
  if (!pill) return;
  if (State.bypass18) {
    pill.classList.remove('disabled');
    pill.innerHTML = '<span>🔓</span> <span>Bypass +18 Ativo</span>';
  } else {
    pill.classList.add('disabled');
    pill.innerHTML = '<span>🔒</span> <span>Censura +18 Padrão</span>';
  }
}
