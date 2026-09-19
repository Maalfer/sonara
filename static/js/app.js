/* Sonara — biblioteca, búsqueda, añadir canciones, favoritos, tema, navegación. */
'use strict';

const Toast = {
  show(msg, type = 'info', ms = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = msg;
    container.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => el.remove(), 300);
    }, ms);
  },
};

const Confirm = {
  _resolve: null,
  init() {
    document.getElementById('confirm-backdrop').addEventListener('click', () => this._settle(false));
    document.getElementById('confirm-cancel').addEventListener('click', () => this._settle(false));
    document.getElementById('confirm-ok').addEventListener('click', () => this._settle(true));
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !document.getElementById('confirm-dialog').classList.contains('hidden')) this._settle(false);
    });
  },
  ask(message, okLabel = 'Eliminar') {
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('confirm-ok').textContent = okLabel;
    document.getElementById('confirm-dialog').classList.remove('hidden');
    return new Promise((resolve) => { this._resolve = resolve; });
  },
  _settle(value) {
    document.getElementById('confirm-dialog').classList.add('hidden');
    if (this._resolve) { this._resolve(value); this._resolve = null; }
  },
};

const Theme = {
  KEY: 'sn_theme',
  init() {
    const saved = localStorage.getItem(this.KEY) || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    const btn = document.getElementById('btn-theme-toggle');
    if (btn) btn.addEventListener('click', () => this.toggle());
  },
  toggle() {
    const cur = document.documentElement.getAttribute('data-theme');
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(this.KEY, next);
  },
};

const NAV_LABELS = { all: 'Toda la música', favorites: 'Favoritas', top: 'Más escuchadas' };

const Library = {
  songs: [],
  loading: false,
  state: { search: '', sort: 'recent', nav: 'all' },
  view: localStorage.getItem('sn_view') || 'list',

  init(initialSongs) {
    this.songs = initialSongs || [];
    this.render();
    this.bindSearch();
    this.bindSort();
    this.bindNav();
    this.bindView();
    this.bindSongList();
    this.bindContextMenu();
    this.bindShortcuts();
  },

  navPresets: {
    all: { sort: 'recent', favoritesOnly: false, showSort: true },
    favorites: { sort: 'recent', favoritesOnly: true, showSort: true },
    top: { sort: 'plays', favoritesOnly: false, showSort: false },
  },

  async refresh() {
    this.loading = true;
    this.renderSkeleton();
    const preset = this.navPresets[this.state.nav];
    const params = new URLSearchParams();
    if (this.state.search) params.set('search', this.state.search);
    params.set('sort', this.state.sort);
    if (preset.favoritesOnly) params.set('favorites', '1');
    try {
      const res = await fetch(`/api/songs?${params.toString()}`, { headers: { 'X-Requested-With': 'fetch' } });
      if (res.status === 401) { window.location = '/login/'; return; }
      const data = await res.json();
      this.songs = data.songs || [];
    } catch (e) {
      Toast.show('No se pudo actualizar la biblioteca', 'error');
      this.songs = [];
    }
    this.loading = false;
    this.render();
  },

  renderSkeleton() {
    const area = document.getElementById('content-area');
    const n = 6;
    if (this.view === 'grid') {
      area.innerHTML = `<div class="song-grid">${Array.from({ length: n }).map(() => `
        <div class="song-card">
          <div class="skeleton card-thumb-wrap"></div>
          <div class="skeleton skeleton-line" style="width:80%"></div>
          <div class="skeleton skeleton-line" style="width:55%"></div>
        </div>`).join('')}</div>`;
    } else {
      area.innerHTML = `<ul class="song-list">${Array.from({ length: n }).map(() => `
        <li class="skeleton-row">
          <div class="skeleton skeleton-thumb"></div>
          <div style="flex:1; display:flex; flex-direction:column; gap:6px;">
            <div class="skeleton skeleton-line" style="width:45%"></div>
            <div class="skeleton skeleton-line" style="width:25%"></div>
          </div>
        </li>`).join('')}</ul>`;
    }
  },

  render() {
    const area = document.getElementById('content-area');
    const titleEl = document.getElementById('content-title');
    if (titleEl) titleEl.textContent = NAV_LABELS[this.state.nav] || 'Biblioteca';

    if (!this.songs.length) {
      const emptyMsg = this.state.search
        ? `<p>No se encontraron canciones para "${escapeHtml(this.state.search)}"</p>`
        : this.state.nav === 'favorites'
          ? `<p>Aún no tienes canciones favoritas</p><p class="empty-sub">Márcalas con ★ desde el menú de opciones de cada canción</p>`
          : this.state.nav === 'top'
            ? `<p>Todavía no hay reproducciones registradas</p>`
            : `<p>Tu biblioteca está vacía</p><p class="empty-sub">Pulsa <strong>+</strong> para traer tu primera canción de YouTube</p>`;
      area.innerHTML = `
        <div class="empty-state">
          <svg width="56" height="56" viewBox="0 0 24 24" fill="currentColor" class="empty-icon"><path d="M12 3v9.28a4.39 4.39 0 00-1.5-.28C8.01 12 6 14.01 6 16.5S8.01 21 10.5 21c2.31 0 4.2-1.75 4.45-4H15V6h4V3h-7z"/></svg>
          ${emptyMsg}
          ${!this.state.search && this.state.nav === 'all' ? '<button class="btn btn-primary" id="empty-add-btn">Añadir canción</button>' : ''}
        </div>`;
      const emptyBtn = document.getElementById('empty-add-btn');
      if (emptyBtn) emptyBtn.addEventListener('click', () => AddModal.open());
      return;
    }

    const count = this.songs.length;
    const html = this.view === 'grid' ? this._renderGrid() : this._renderList();
    area.innerHTML = `
      <div class="page-library fade-in">
        <div class="songs-count">${count} ${count === 1 ? 'canción' : 'canciones'}</div>
        ${html}
      </div>`;

    window._librarySongs = this.songs;
    Player.highlightCurrent();
    this.bindSongList();
  },

  _renderList() {
    const rows = this.songs.map((song, index) => `
      <li class="song-item" data-song-id="${song.id}" data-index="${index}">
        <div class="song-thumb-wrap">
          ${song.thumbnail
            ? `<img src="${escapeHtml(song.thumbnail)}" alt="" class="song-thumb" loading="lazy" onerror="this.onerror=null;this.src=FALLBACK_THUMB">`
            : `<div class="song-thumb-placeholder">${noteIcon()}</div>`}
          <div class="song-play-overlay">${playIcon()}</div>
        </div>
        <div class="song-info">
          <div class="song-title">${escapeHtml(song.title)}</div>
          <div class="song-artist">${escapeHtml(song.artist)}</div>
        </div>
        <div class="song-meta">
          ${song.is_favorite ? '<span class="fav-dot" title="Favorita">★</span>' : ''}
          ${song.duration ? `<span class="song-duration">${formatTime(song.duration)}</span>` : ''}
          <button class="song-menu-btn" data-song-id="${song.id}" title="Opciones">${dotsIcon()}</button>
        </div>
      </li>`).join('');
    return `<ul class="song-list" id="song-list">${rows}</ul>`;
  },

  _renderGrid() {
    const cards = this.songs.map((song, index) => `
      <div class="song-card" data-song-id="${song.id}" data-index="${index}">
        <div class="card-thumb-wrap">
          ${song.thumbnail
            ? `<img src="${escapeHtml(song.thumbnail)}" alt="" class="card-thumb" loading="lazy" onerror="this.onerror=null;this.src=FALLBACK_THUMB">`
            : `<div class="song-thumb-placeholder">${noteIcon()}</div>`}
          <div class="card-play-overlay">${playIcon()}</div>
          <button class="card-menu-btn song-menu-btn" data-song-id="${song.id}" title="Opciones">${dotsIcon()}</button>
          ${song.is_favorite ? '<span class="fav-dot card-fav-dot" title="Favorita">★</span>' : ''}
        </div>
        <div class="card-title">${escapeHtml(song.title)}</div>
        <div class="card-artist">${escapeHtml(song.artist)}</div>
      </div>`).join('');
    return `<div class="song-grid" id="song-list">${cards}</div>`;
  },

  bindSearch() {
    const input = document.getElementById('search-input');
    const clearBtn = document.getElementById('search-clear');
    if (!input) return;
    let debounce;
    input.addEventListener('input', () => {
      clearBtn.classList.toggle('hidden', !input.value);
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        this.state.search = input.value.trim();
        this.refresh();
      }, 350);
    });
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        input.value = '';
        clearBtn.classList.add('hidden');
        this.state.search = '';
        this.refresh();
        input.focus();
      });
    }
  },

  bindSort() {
    const sel = document.getElementById('sort-select');
    if (!sel) return;
    sel.value = this.state.sort;
    sel.addEventListener('change', () => {
      this.state.sort = sel.value;
      this.refresh();
    });
  },

  bindNav() {
    const buttons = document.querySelectorAll('[data-nav]');
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const nav = btn.dataset.nav;
        if (this.state.nav === nav) return;
        this.state.nav = nav;
        const preset = this.navPresets[nav];
        this.state.sort = preset.sort;

        document.querySelectorAll('[data-nav]').forEach((b) => b.classList.toggle('active', b.dataset.nav === nav));
        const sortSelect = document.getElementById('sort-select');
        if (sortSelect) {
          sortSelect.value = preset.sort;
          sortSelect.classList.toggle('hidden', !preset.showSort);
        }
        this.refresh();
      });
    });
  },

  bindView() {
    const listBtn = document.getElementById('view-list');
    const gridBtn = document.getElementById('view-grid');
    if (!listBtn || !gridBtn) return;
    const apply = () => {
      listBtn.classList.toggle('active', this.view === 'list');
      gridBtn.classList.toggle('active', this.view === 'grid');
    };
    apply();
    listBtn.addEventListener('click', () => { this.view = 'list'; localStorage.setItem('sn_view', 'list'); apply(); this.render(); });
    gridBtn.addEventListener('click', () => { this.view = 'grid'; localStorage.setItem('sn_view', 'grid'); apply(); this.render(); });
  },

  bindSongList() {
    const list = document.getElementById('song-list');
    if (!list) return;
    list.addEventListener('click', (e) => {
      if (e.target.closest('.song-menu-btn')) return;
      const item = e.target.closest('.song-item, .song-card');
      if (!item) return;
      const index = parseInt(item.dataset.index, 10);
      const songs = window._librarySongs || [];
      if (songs[index]) Player.playSong(songs[index], songs, index);
    });
  },

  bindContextMenu() {
    const menu = document.getElementById('song-context-menu');
    if (!menu) return;
    let activeSongId = null;

    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.song-menu-btn');
      if (!btn) {
        if (!menu.contains(e.target)) menu.classList.add('hidden');
        return;
      }
      e.stopPropagation();
      activeSongId = parseInt(btn.dataset.songId, 10);
      const song = this.songs.find((s) => s.id === activeSongId);
      const favBtn = document.getElementById('ctx-favorite');
      if (favBtn) favBtn.textContent = song && song.is_favorite ? 'Quitar de favoritas' : 'Añadir a favoritas';

      const rect = btn.getBoundingClientRect();
      menu.classList.remove('hidden');
      const menuH = 130;
      const menuW = 190;
      const top = rect.bottom + 4;
      menu.style.top = ((top + menuH > window.innerHeight) ? rect.top - menuH - 4 : top) + 'px';
      let left = rect.right - menuW;
      left = Math.max(8, Math.min(left, window.innerWidth - menuW - 8));
      menu.style.left = left + 'px';
      menu.style.right = 'auto';
    });

    document.getElementById('ctx-play').addEventListener('click', () => {
      menu.classList.add('hidden');
      const songs = window._librarySongs || [];
      const idx = songs.findIndex((s) => s.id === activeSongId);
      if (idx >= 0) Player.playSong(songs[idx], songs, idx);
    });

    document.getElementById('ctx-favorite').addEventListener('click', () => this.toggleFavorite(activeSongId, menu));
    document.getElementById('ctx-delete').addEventListener('click', async () => {
      menu.classList.add('hidden');
      if (!activeSongId) return;
      const song = this.songs.find((s) => s.id === activeSongId);
      const ok = await Confirm.ask(`¿Eliminar "${song ? song.title : 'esta canción'}" de tu biblioteca? Esta acción no se puede deshacer.`);
      if (ok) this.deleteSong(activeSongId);
    });
  },

  bindShortcuts() {
    document.addEventListener('keydown', (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (e.key === '/' && tag !== 'input' && tag !== 'textarea') {
        e.preventDefault();
        document.getElementById('search-input').focus();
      }
    });
  },

  async toggleFavorite(songId, menu) {
    if (menu) menu.classList.add('hidden');
    try {
      const res = await fetch(`/api/songs/${songId}/favorite`, { method: 'POST', headers: { 'X-CSRFToken': window.CSRF_TOKEN } });
      const data = await res.json();
      if (data.success) {
        const song = this.songs.find((s) => s.id === songId);
        if (song) song.is_favorite = data.is_favorite;
        Toast.show(data.is_favorite ? 'Añadida a favoritas' : 'Quitada de favoritas', 'success', 2000);
        if (this.state.nav === 'favorites' && !data.is_favorite) {
          this.songs = this.songs.filter((s) => s.id !== songId);
        }
        this.render();
      }
    } catch (e) {
      Toast.show('No se pudo actualizar', 'error');
    }
  },

  async deleteSong(songId) {
    try {
      const res = await fetch(`/api/songs/${songId}/delete`, { method: 'POST', headers: { 'X-CSRFToken': window.CSRF_TOKEN } });
      const data = await res.json();
      if (data.success) {
        this.songs = this.songs.filter((s) => s.id !== songId);
        this.render();
        const idx = Player.queue.findIndex((s) => s.id === songId);
        if (idx >= 0) {
          Player.queue.splice(idx, 1);
          Player.order = Player.order.filter((i) => i !== idx).map((i) => (i > idx ? i - 1 : i));
          if (Player.currentIndex > idx) Player.currentIndex--;
          Player.saveState();
        }
        Toast.show('Canción eliminada', 'success', 2000);
      } else {
        Toast.show(data.error || 'Error al eliminar', 'error');
      }
    } catch (e) {
      Toast.show('Error de conexión', 'error');
    }
  },
};

const AddModal = {
  init() {
    document.getElementById('modal-backdrop').addEventListener('click', () => this.close());
    document.getElementById('modal-close-btn').addEventListener('click', () => this.close());
    document.getElementById('open-add-modal').addEventListener('click', () => this.open());
    document.getElementById('btn-add-song').addEventListener('click', () => this.submit());
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !document.getElementById('modal-add-song').classList.contains('hidden')) this.close();
    });
  },

  open() {
    document.getElementById('modal-add-song').classList.remove('hidden');
    const textarea = document.getElementById('yt-urls');
    textarea.value = '';
    document.getElementById('add-song-status').innerHTML = '';
    textarea.focus();
  },

  close() { document.getElementById('modal-add-song').classList.add('hidden'); },

  async submit() {
    const textarea = document.getElementById('yt-urls');
    const urls = textarea.value.split('\n').map((u) => u.trim()).filter(Boolean);
    const statusList = document.getElementById('add-song-status');
    statusList.innerHTML = '';

    if (!urls.length) {
      Toast.show('Pega al menos un enlace de YouTube', 'error');
      return;
    }

    const btn = document.getElementById('btn-add-song');
    btn.disabled = true;
    let added = 0;

    for (const url of urls) {
      const row = document.createElement('li');
      row.className = 'status-row status-loading';
      row.innerHTML = `<span class="spinner spinner-sm"></span><span class="status-url">${escapeHtml(shortenUrl(url))}</span>`;
      statusList.appendChild(row);

      try {
        const res = await fetch('/api/songs/download', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': window.CSRF_TOKEN },
          body: JSON.stringify({ url }),
        });
        const data = await res.json();
        if (data.success) {
          added++;
          row.className = 'status-row status-success';
          row.innerHTML = `<span class="status-icon">✓</span><span class="status-url">${escapeHtml(data.song.title)}</span>`;
          Library.songs.unshift(data.song);
        } else {
          row.className = 'status-row status-error';
          row.innerHTML = `<span class="status-icon">✕</span><span class="status-url">${escapeHtml(data.error || 'Error desconocido')}</span>`;
        }
      } catch (e) {
        row.className = 'status-row status-error';
        row.innerHTML = `<span class="status-icon">✕</span><span class="status-url">Error de conexión</span>`;
      }
    }

    btn.disabled = false;
    if (added > 0) {
      Toast.show(`${added} ${added === 1 ? 'canción añadida' : 'canciones añadidas'}`, 'success');
      Library.render();
    }
  },
};

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}
function shortenUrl(url) {
  return url.length > 60 ? url.slice(0, 57) + '…' : url;
}
function noteIcon() {
  return '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v9.28a4.39 4.39 0 00-1.5-.28C8.01 12 6 14.01 6 16.5S8.01 21 10.5 21c2.31 0 4.2-1.75 4.45-4H15V6h4V3h-7z"/></svg>';
}
function playIcon() {
  return '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';
}
function dotsIcon() {
  return '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>';
}

document.addEventListener('DOMContentLoaded', () => {
  Theme.init();
  Confirm.init();
  Library.init(window.INITIAL_SONGS);
  AddModal.init();

  const avatarBtn = document.getElementById('user-avatar-btn');
  const dropdown = document.getElementById('user-dropdown');
  if (avatarBtn && dropdown) {
    avatarBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown.classList.toggle('hidden');
    });
    document.addEventListener('click', () => dropdown.classList.add('hidden'));
  }
});
