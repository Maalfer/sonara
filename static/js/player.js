/* Sonara — reproductor persistente (cola, aleatorio, repetir, volumen, media session). */
'use strict';

function formatTime(secs) {
  const s = Math.floor(secs || 0);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
    : `${m}:${String(sec).padStart(2, '0')}`;
}
window.formatTime = formatTime;

const FALLBACK_THUMB = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Crect width='24' height='24' fill='%2314141f'/%3E%3Cpath fill='%239a9ab0' d='M12 3v9.28a4.39 4.39 0 00-1.5-.28C8.01 12 6 14.01 6 16.5S8.01 21 10.5 21c2.31 0 4.2-1.75 4.45-4H15V6h4V3h-7z'/%3E%3C/svg%3E";

function shuffleArray(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const Player = {
  audio: null,
  queue: [],
  order: [],
  orderPos: -1,
  currentIndex: -1,
  shuffle: false,
  repeatMode: 'off', // off | all | one
  isSeeking: false,
  _pendingSeek: null,
  _initialized: false,

  init() {
    if (this._initialized) return;
    this.audio = document.getElementById('audio-player');
    if (!this.audio) return;
    this._initialized = true;
    this.shuffle = localStorage.getItem('sn_shuffle') === '1';
    this.repeatMode = localStorage.getItem('sn_repeat') || 'off';
    this.audio.volume = parseFloat(localStorage.getItem('sn_volume') || '1');
    this.bindAudioEvents();
    this.bindControls();
    this.updateShuffleRepeatUI();
    this.restoreState();
  },

  bindAudioEvents() {
    const a = this.audio;
    a.addEventListener('timeupdate', () => {
      if (this.isSeeking) return;
      const pct = a.duration ? (a.currentTime / a.duration) * 100 : 0;
      this.updateSeekUI(pct, a.currentTime, a.duration);
      const now = Date.now();
      if (!this._lastTimeSave || now - this._lastTimeSave > 900) {
        this._lastTimeSave = now;
        try { localStorage.setItem('sn_time', a.currentTime || 0); } catch (_) {}
      }
    });
    a.addEventListener('play', () => { this.setPlayIcon(true); try { localStorage.setItem('sn_paused', '0'); } catch (_) {} });
    a.addEventListener('pause', () => { this.setPlayIcon(false); try { localStorage.setItem('sn_paused', '1'); } catch (_) {} });
    a.addEventListener('ended', () => this._onEnded());
    a.addEventListener('loadedmetadata', () => {
      if (this._pendingSeek != null && isFinite(this._pendingSeek)) {
        try { a.currentTime = Math.min(this._pendingSeek, a.duration || this._pendingSeek); } catch (_) {}
        this._pendingSeek = null;
      }
      const pct = a.duration ? (a.currentTime / a.duration) * 100 : 0;
      this.updateSeekUI(pct, a.currentTime, a.duration);
    });
    a.addEventListener('error', (e) => console.warn('Audio error', e));
  },

  bindControls() {
    const on = (id, ev, fn) => { const el = document.getElementById(id); if (el) el.addEventListener(ev, fn); };
    on('btn-play-pause', 'click', () => this.togglePlay());
    on('btn-prev', 'click', () => this.advance(-1));
    on('btn-next', 'click', () => this.advance(1));
    on('btn-shuffle', 'click', () => this.toggleShuffle());
    on('btn-repeat', 'click', () => this.cycleRepeat());
    on('player-expand-btn', 'click', () => this.openFullscreen());

    on('pf-play-pause', 'click', () => this.togglePlay());
    on('pf-prev', 'click', () => this.advance(-1));
    on('pf-next', 'click', () => this.advance(1));
    on('pf-shuffle', 'click', () => this.toggleShuffle());
    on('pf-repeat', 'click', () => this.cycleRepeat());
    on('pf-close', 'click', () => this.closeFullscreen());

    ['pf-seek', 'mini-seek'].forEach((id) => {
      const seekBar = document.getElementById(id);
      if (!seekBar) return;
      seekBar.addEventListener('input', () => {
        this.isSeeking = true;
        const pct = parseFloat(seekBar.value);
        this._syncSeekBars(pct);
        if (this.audio.duration) {
          const cur = document.getElementById('pf-current');
          if (cur) cur.textContent = formatTime(this.audio.duration * pct / 100);
        }
      });
      seekBar.addEventListener('change', () => {
        if (this.audio.duration) this.audio.currentTime = this.audio.duration * parseFloat(seekBar.value) / 100;
        this.isSeeking = false;
      });
    });

    const volSlider = document.getElementById('volume-slider');
    if (volSlider) {
      volSlider.value = Math.round(this.audio.volume * 100);
      volSlider.addEventListener('input', () => {
        this.audio.volume = parseFloat(volSlider.value) / 100;
        localStorage.setItem('sn_volume', this.audio.volume);
        this.updateMuteIcon();
      });
    }
    on('btn-mute', 'click', () => {
      this.audio.muted = !this.audio.muted;
      this.updateMuteIcon();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const fs = document.getElementById('player-fullscreen');
        if (fs && !fs.classList.contains('hidden')) this.closeFullscreen();
      }
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      if (e.code === 'Space') { e.preventDefault(); this.togglePlay(); }
    });
  },

  updateMuteIcon() {
    const icon = document.getElementById('icon-vol');
    if (icon) icon.style.opacity = (this.audio.muted || this.audio.volume === 0) ? '0.4' : '1';
  },

  playSong(song, queue, index) {
    this.queue = queue || [];
    this._buildOrder(index != null ? index : 0);
    this._loadAndPlay(song);
  },

  _buildOrder(startIndex) {
    const n = this.queue.length;
    const seq = Array.from({ length: n }, (_, i) => i);
    if (this.shuffle) {
      const rest = seq.filter((i) => i !== startIndex);
      this.order = [startIndex, ...shuffleArray(rest)];
    } else {
      this.order = seq;
    }
    this.orderPos = this.order.indexOf(startIndex);
    if (this.orderPos < 0) this.orderPos = 0;
    this.currentIndex = startIndex;
  },

  toggleShuffle() {
    this.shuffle = !this.shuffle;
    localStorage.setItem('sn_shuffle', this.shuffle ? '1' : '0');
    if (this.queue.length) this._buildOrder(this.currentIndex);
    this.updateShuffleRepeatUI();
    this.updateUpNext();
  },

  cycleRepeat() {
    this.repeatMode = { off: 'all', all: 'one', one: 'off' }[this.repeatMode];
    localStorage.setItem('sn_repeat', this.repeatMode);
    this.updateShuffleRepeatUI();
    this.updateUpNext();
  },

  updateShuffleRepeatUI() {
    ['btn-shuffle', 'pf-shuffle'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle('active', this.shuffle);
    });
    ['btn-repeat', 'pf-repeat'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.classList.toggle('active', this.repeatMode !== 'off');
        el.classList.toggle('repeat-one', this.repeatMode === 'one');
      }
    });
  },

  _loadAndPlay(song) {
    if (!song) return;
    this.audio.src = `/api/stream/${song.id}`;
    this.audio.load();
    this._pendingSeek = null;
    this.audio.play().catch(() => {});
    this.updateUI(song);
    this.setupMediaSession(song);
    this.saveState();
    this.highlightCurrent();
    this.updateUpNext();
    fetch(`/api/songs/${song.id}/play`, {
      method: 'POST',
      headers: { 'X-CSRFToken': window.CSRF_TOKEN || '' },
    }).catch(() => {});
  },

  updateUI(song) {
    const bar = document.getElementById('player-bar');
    if (bar) bar.classList.remove('hidden');
    document.body.classList.add('has-player');
    const setSrc = (id, v) => { const el = document.getElementById(id); if (el) { el.src = v || FALLBACK_THUMB; el.onerror = () => { el.onerror = null; el.src = FALLBACK_THUMB; }; } };
    const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v || ''; };
    setSrc('player-thumb', song.thumbnail);
    setText('player-title', song.title || '');
    setText('player-artist', song.artist || '');
    setSrc('pf-thumb', song.thumbnail);
    setText('pf-title', song.title || '');
    setText('pf-artist', song.artist || '');
  },

  togglePlay() {
    if (!this.audio || !this.audio.src) return;
    if (this.audio.paused) this.audio.play().catch(() => {});
    else this.audio.pause();
  },

  advance(delta) {
    if (!this.order.length) return;
    if (delta < 0 && this.audio.currentTime > 3) { this.audio.currentTime = 0; return; }
    this.orderPos = (this.orderPos + delta + this.order.length) % this.order.length;
    this.currentIndex = this.order[this.orderPos];
    this._loadAndPlay(this.queue[this.currentIndex]);
  },

  _onEnded() {
    if (this.repeatMode === 'one') {
      this.audio.currentTime = 0;
      this.audio.play().catch(() => {});
      return;
    }
    const atEnd = this.orderPos >= this.order.length - 1;
    if (atEnd && this.repeatMode === 'off') {
      this.setPlayIcon(false);
      return;
    }
    this.advance(1);
  },

  setPlayIcon(playing) {
    ['icon-play', 'pf-icon-play'].forEach((id) => { const el = document.getElementById(id); if (el) el.style.display = playing ? 'none' : ''; });
    ['icon-pause', 'pf-icon-pause'].forEach((id) => { const el = document.getElementById(id); if (el) el.style.display = playing ? '' : 'none'; });
  },

  updateSeekUI(pct, cur, dur) {
    if (!this.isSeeking) this._syncSeekBars(pct);
    const c = document.getElementById('pf-current'); if (c) c.textContent = formatTime(cur || 0);
    const d = document.getElementById('pf-duration'); if (d) d.textContent = formatTime(dur || 0);
  },

  _syncSeekBars(pct) {
    ['pf-seek', 'mini-seek'].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.value = pct;
      el.style.setProperty('--fill', pct + '%');
    });
  },

  updateUpNext() {
    const el = document.getElementById('pf-upnext');
    if (!el) return;
    if (!this.order.length || this.order.length < 2) { el.textContent = ''; return; }
    let nextPos = this.orderPos + 1;
    if (nextPos >= this.order.length) {
      if (this.repeatMode !== 'all') { el.textContent = ''; return; }
      nextPos = 0;
    }
    const next = this.queue[this.order[nextPos]];
    el.textContent = next ? `Siguiente: ${next.title}` : '';
  },

  openFullscreen() { const fs = document.getElementById('player-fullscreen'); if (fs) { fs.classList.remove('hidden'); document.body.style.overflow = 'hidden'; } },
  closeFullscreen() { const fs = document.getElementById('player-fullscreen'); if (fs) { fs.classList.add('hidden'); document.body.style.overflow = ''; } },

  highlightCurrent() {
    document.querySelectorAll('.song-item').forEach((el) => el.classList.remove('playing'));
    if (this.currentIndex < 0 || !this.queue.length) return;
    const cur = this.queue[this.currentIndex];
    if (!cur) return;
    const el = document.querySelector(`.song-item[data-song-id="${cur.id}"]`);
    if (el) el.classList.add('playing');
  },

  setupMediaSession(song) {
    if (!('mediaSession' in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: song.title || 'Unknown',
      artist: song.artist || 'Unknown',
      artwork: song.thumbnail ? [{ src: song.thumbnail, sizes: '480x360', type: 'image/jpeg' }] : [],
    });
    navigator.mediaSession.setActionHandler('play', () => this.audio.play().catch(() => {}));
    navigator.mediaSession.setActionHandler('pause', () => this.audio.pause());
    navigator.mediaSession.setActionHandler('nexttrack', () => this.advance(1));
    navigator.mediaSession.setActionHandler('previoustrack', () => this.advance(-1));
    navigator.mediaSession.setActionHandler('seekto', (d) => { if (d.seekTime != null) this.audio.currentTime = d.seekTime; });
  },

  saveState() {
    if (this.currentIndex < 0 || !this.queue.length) return;
    try {
      localStorage.setItem('sn_song', JSON.stringify(this.queue[this.currentIndex]));
      localStorage.setItem('sn_queue', JSON.stringify(this.queue));
      localStorage.setItem('sn_order', JSON.stringify(this.order));
      localStorage.setItem('sn_orderpos', this.orderPos);
      localStorage.setItem('sn_time', this.audio.currentTime || 0);
    } catch (_) {}
  },

  restoreState() {
    try {
      const songRaw = localStorage.getItem('sn_song');
      const queueRaw = localStorage.getItem('sn_queue');
      if (!songRaw || !queueRaw) return;
      const song = JSON.parse(songRaw);
      const queue = JSON.parse(queueRaw);
      const order = JSON.parse(localStorage.getItem('sn_order') || '[]');
      const orderPos = parseInt(localStorage.getItem('sn_orderpos') || '0');
      const time = parseFloat(localStorage.getItem('sn_time') || '0');
      const wasPlaying = localStorage.getItem('sn_paused') === '0';
      if (!song || !queue || !queue.length) return;

      this.queue = queue;
      this.order = order.length === queue.length ? order : queue.map((_, i) => i);
      this.orderPos = Math.max(0, Math.min(orderPos, this.order.length - 1));
      this.currentIndex = this.order[this.orderPos];
      this.audio.src = `/api/stream/${song.id}`;
      this.audio.load();
      this._pendingSeek = time;
      this.updateUI(song);
      this.setupMediaSession(song);
      this.setPlayIcon(!!wasPlaying);
      this.updateUpNext();
      if (wasPlaying) this.audio.play().catch(() => this.setPlayIcon(false));
    } catch (_) {}
  },
};

window.Player = Player;
document.addEventListener('DOMContentLoaded', () => Player.init());
