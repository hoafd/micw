/**
 * recordings.js - Trang nghe lại âm thanh đã ghi
 */

// ── State ────────────────────────────────────────────────────────────────────
let allRecordings = [];
let filteredRecordings = [];
let currentFile = null;
let currentSort = 'date';
let sortAscending = false;

// ── DOM Elements ─────────────────────────────────────────────────────────────
const listEl     = document.getElementById('recordingsList');
const playerBar  = document.getElementById('playerBar');
const audioEl    = document.getElementById('audioPlayer');
const playerTitle= document.getElementById('playerTitle');
const playerSub  = document.getElementById('playerSub');
const downloadBtn= document.getElementById('downloadBtn');
const statusDot  = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');

// ── Load Recordings ───────────────────────────────────────────────────────────
async function loadRecordings() {
  listEl.innerHTML = `
    <div class="empty-state">
      <div class="spinner" style="margin: 0 auto 16px;"></div>
      <h3>Đang tải danh sách...</h3>
    </div>`;

  try {
    const res  = await fetch('/api/recordings');
    const data = await res.json();
    allRecordings = data.recordings || [];
    applySort();
    renderList();
    updateStats();
  } catch(e) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="icon">❌</div>
        <h3>Không thể tải danh sách</h3>
        <p>${e.message}</p>
      </div>`;
  }
}

function updateStats() {
  const total = allRecordings.length;
  const totalMB = allRecordings.reduce((s, r) => s + r.size_mb, 0);
  const totalSecs = allRecordings.reduce((s, r) => s + r.duration_seconds, 0);
  const sampleRate = allRecordings[0]?.sample_rate || 48000;

  document.getElementById('statTotalFiles').textContent = total;
  document.getElementById('statTotalSize').textContent  = totalMB > 1024
    ? `${(totalMB/1024).toFixed(1)}GB`
    : `${totalMB.toFixed(0)}MB`;
  document.getElementById('statTotalDuration').textContent = formatDuration(totalSecs);
  document.getElementById('statSampleRate').textContent    = `${sampleRate/1000}kHz`;
}

// ── Render List ───────────────────────────────────────────────────────────────
function renderList() {
  const query = document.getElementById('searchInput').value.toLowerCase();
  filteredRecordings = allRecordings.filter(r =>
    r.filename.toLowerCase().includes(query)
  );

  document.getElementById('fileCount').textContent =
    filteredRecordings.length === allRecordings.length
      ? `${allRecordings.length} file`
      : `${filteredRecordings.length} / ${allRecordings.length} file`;

  if (filteredRecordings.length === 0) {
    listEl.innerHTML = `
      <div class="empty-state">
        <div class="icon">🎵</div>
        <h3>${allRecordings.length === 0 ? 'Chưa có file nào' : 'Không tìm thấy'}</h3>
        <p>${allRecordings.length === 0
          ? 'Bắt đầu ghi âm từ trang Live Stream'
          : 'Thử từ khóa tìm kiếm khác'
        }</p>
        ${allRecordings.length === 0 ? `<a href="/" class="btn btn-primary" style="margin-top:16px;">🔴 Live Stream</a>` : ''}
      </div>`;
    return;
  }

  listEl.innerHTML = '';
  const ul = document.createElement('div');
  ul.style.cssText = 'display: flex; flex-direction: column; gap: 8px;';

  filteredRecordings.forEach((rec, idx) => {
    const item = createRecordingItem(rec, idx);
    ul.appendChild(item);
  });

  listEl.appendChild(ul);
}

function createRecordingItem(rec, idx) {
  const isPlaying = currentFile === rec.filename;
  const div = document.createElement('div');
  div.className = `recording-item${isPlaying ? ' playing' : ''}`;
  div.id = `rec-item-${idx}`;

  // Parse date from filename: rec_YYYYMMDD_HHMMSS.wav
  const dateStr = parseDate(rec.filename);

  div.innerHTML = `
    <div class="rec-icon">🎙️</div>
    <div class="rec-info">
      <div class="rec-name" title="${rec.filename}">${rec.filename}</div>
      <div class="rec-meta">
        ${dateStr} &nbsp;·&nbsp;
        ${rec.duration_str} &nbsp;·&nbsp;
        ${rec.size_mb}MB &nbsp;·&nbsp;
        <span style="color:var(--accent-teal)">${rec.sample_rate / 1000}kHz</span>
      </div>
    </div>
    <div class="rec-actions">
      <button class="btn btn-primary btn-sm" onclick="playRecording('${rec.filename}', ${idx})"
              id="play-btn-${idx}" title="Phát">
        ${isPlaying ? '⏸ Đang phát' : '▶ Phát'}
      </button>
      <a class="btn btn-secondary btn-sm"
         href="/api/recordings/${encodeURIComponent(rec.filename)}"
         download="${rec.filename}" title="Download">
        ⬇
      </a>
      <button class="btn btn-danger btn-sm" onclick="deleteRecording('${rec.filename}', ${idx})"
              title="Xóa">
        🗑
      </button>
    </div>`;

  return div;
}

function parseDate(filename) {
  // Pattern: rec_YYYYMMDD_HHMMSS.wav
  const m = filename.match(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
  if (!m) return '';
  return `${m[3]}/${m[2]}/${m[1]} ${m[4]}:${m[5]}:${m[6]}`;
}

// ── Playback ──────────────────────────────────────────────────────────────────
function playRecording(filename, idx) {
  currentFile = filename;
  const rec = filteredRecordings[idx];
  const url = `/api/recordings/${encodeURIComponent(filename)}`;

  playerTitle.textContent = filename;
  playerSub.textContent   = `${rec.duration_str} · ${rec.size_mb}MB · ${rec.sample_rate/1000}kHz`;
  audioEl.src = url;
  audioEl.play();

  playerBar.classList.add('visible');
  downloadBtn.setAttribute('data-filename', filename);

  // Update list item highlight
  renderList(); // re-render to show playing state
}

function closePlayer() {
  audioEl.pause();
  audioEl.src = '';
  currentFile = null;
  playerBar.classList.remove('visible');
  renderList();
}

function downloadCurrent() {
  if (!currentFile) return;
  const a = document.createElement('a');
  a.href = `/api/recordings/${encodeURIComponent(currentFile)}`;
  a.download = currentFile;
  a.click();
}

// Auto-close player when audio ends
audioEl.addEventListener('ended', () => {
  // Find next track
  const idx = filteredRecordings.findIndex(r => r.filename === currentFile);
  if (idx >= 0 && idx < filteredRecordings.length - 1) {
    playRecording(filteredRecordings[idx + 1].filename, idx + 1);
  } else {
    closePlayer();
  }
});

// ── Delete ─────────────────────────────────────────────────────────────────────
async function deleteRecording(filename, idx) {
  if (!confirm(`Xóa file "${filename}"?`)) return;

  try {
    const res = await fetch(`/api/recordings/${encodeURIComponent(filename)}`, {
      method: 'DELETE'
    });
    const data = await res.json();

    if (data.success) {
      showToast(`✓ Đã xóa: ${filename}`, 'success');
      if (currentFile === filename) closePlayer();
      allRecordings = allRecordings.filter(r => r.filename !== filename);
      applySort();
      renderList();
      updateStats();
    } else {
      showToast(`Lỗi: ${data.error}`, 'error');
    }
  } catch(e) {
    showToast(`Lỗi: ${e.message}`, 'error');
  }
}

// ── Filter & Sort ─────────────────────────────────────────────────────────────
function filterRecordings() {
  renderList();
}

function sortBy(field) {
  if (currentSort === field) {
    sortAscending = !sortAscending;
  } else {
    currentSort   = field;
    sortAscending = false;
  }

  // Update button styles
  ['date', 'size', 'duration'].forEach(f => {
    const btn = document.getElementById(`sort${f.charAt(0).toUpperCase() + f.slice(1)}`);
    if (btn) {
      btn.style.borderColor = f === field ? 'var(--border-accent)' : 'var(--border)';
      btn.style.color       = f === field ? 'var(--accent-teal)'   : 'var(--text-primary)';
    }
  });

  applySort();
  renderList();
}

function applySort() {
  const dir = sortAscending ? 1 : -1;
  allRecordings.sort((a, b) => {
    switch(currentSort) {
      case 'size':     return (a.size_bytes - b.size_bytes) * dir;
      case 'duration': return (a.duration_seconds - b.duration_seconds) * dir;
      default:         return (new Date(a.modified) - new Date(b.modified)) * dir;
    }
  });
}

// ── Status ────────────────────────────────────────────────────────────────────
async function fetchStatus() {
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();

    statusDot.className = 'status-dot';
    if (data.mic_connected) {
      statusDot.classList.add('connected');
      statusText.textContent = 'Mic Active';
    } else {
      statusText.textContent = 'Mic Offline';
    }
  } catch(e) {
    statusText.textContent = 'Server Offline';
  }
}

// ── Duration Formatter ────────────────────────────────────────────────────────
function formatDuration(secs) {
  secs = Math.round(secs);
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

// ── Init ──────────────────────────────────────────────────────────────────────
loadRecordings();
fetchStatus();
setInterval(fetchStatus, 15000);
setInterval(loadRecordings, 60000); // Auto-refresh every minute
