/**
 * live.js - Live audio streaming via WebSocket + Web Audio API
 * Nhận PCM data từ backend, decode và phát real-time + visualize
 */

// ── Config (sẽ nhận từ server sau khi kết nối) ──────────────────────────────
let SAMPLE_RATE = 48000;
let CHANNELS    = 1;
let BIT_DEPTH   = 16;
const WS_PORT   = 8765;  // Phải khớp với config.yaml

// ── State ────────────────────────────────────────────────────────────────────
let ws           = null;
let audioCtx     = null;
let gainNode     = null;
let isListening  = false;
let isMuted      = false;
let reconnectTimer = null;
let reconnectDelay = 1500;

// ── Audio scheduling clock ────────────────────────────────────────────────────
// nextPlayTime tracks when the NEXT chunk should start playing.
// This prevents chunks from overlapping (the core audio bug).
let nextPlayTime = 0;
const SCHEDULE_AHEAD = 0.05;  // 50ms look-ahead buffer
const CHUNK_GAP      = 0.001; // 1ms gap between chunks

// Stats
let packetCount  = 0;
let totalBytes   = 0;
let bytesLastSec = 0;
let statsInterval = null;
let startTime    = null;

// Visualizer
let waveformCtx  = null;
let spectrumCtx  = null;
let analyser     = null;
let animFrame    = null;
let waveformData = new Float32Array(256);
let spectrumData = null;

// ── DOM Elements ─────────────────────────────────────────────────────────────
const canvas        = document.getElementById('waveformCanvas');
const specCanvas    = document.getElementById('spectrumCanvas');
const waveOverlay   = document.getElementById('waveformOverlay');
const statusDot     = document.getElementById('statusDot');
const statusText    = document.getElementById('statusText');
const liveBadge     = document.getElementById('liveBadge');
const btnListenIcon = document.getElementById('btnListenIcon');
const btnListenText = document.getElementById('btnListenText');
const wsStatusEl    = document.getElementById('wsStatus');
const micStatusEl   = document.getElementById('micStatus');
const sampleRateEl  = document.getElementById('sampleRateInfo');
const formatEl      = document.getElementById('formatInfo');
const muteIcon      = document.getElementById('muteIcon');
const latencyEl     = document.getElementById('latencyBadge');

// ── Canvas Setup ──────────────────────────────────────────────────────────────
function setupCanvas() {
  // Waveform
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width  = rect.width  * dpr;
  canvas.height = 140 * dpr;
  waveformCtx = canvas.getContext('2d');
  waveformCtx.scale(dpr, dpr);

  // Spectrum
  const sRect = specCanvas.getBoundingClientRect();
  specCanvas.width  = sRect.width  * dpr;
  specCanvas.height = 100 * dpr;
  spectrumCtx = specCanvas.getContext('2d');
  spectrumCtx.scale(dpr, dpr);
}

window.addEventListener('resize', setupCanvas);
setTimeout(setupCanvas, 100);

// ── WebSocket Connection ──────────────────────────────────────────────────────
function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  const wsUrl = `ws://${location.hostname}:${WS_PORT}`;
  updateStatus('connecting');

  try {
    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      reconnectDelay = 1500;
      updateStatus('connected');
      showToast('✓ Kết nối WebSocket thành công', 'success');
      fetchSystemStatus();
    };

    ws.onmessage = (event) => {
      if (typeof event.data === 'string') {
        // JSON config message
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'config') {
            SAMPLE_RATE = msg.sampleRate;
            CHANNELS    = msg.channels;
            BIT_DEPTH   = msg.bitDepth;
            updateAudioInfo(msg);
          }
        } catch(e) {}
        return;
      }

      // Binary audio data (PCM)
      if (isListening && audioCtx) {
        playPCMChunk(event.data);
      }

      // Stats
      packetCount++;
      bytesLastSec += event.data.byteLength;
      totalBytes   += event.data.byteLength;
      document.getElementById('statPackets').textContent = packetCount;
    };

    ws.onclose = (ev) => {
      updateStatus('disconnected');
      if (!ev.wasClean) {
        showToast('Mất kết nối WebSocket, thử lại...', 'error');
        scheduleReconnect();
      }
    };

    ws.onerror = () => {
      ws.close();
    };

  } catch(e) {
    updateStatus('disconnected');
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    connect();
    reconnectDelay = Math.min(reconnectDelay * 1.5, 15000);
  }, reconnectDelay);
}

// ── Audio Context & Playback ──────────────────────────────────────────────────
function initAudioContext() {
  if (audioCtx) return;

  // Browsers may clamp AudioContext sampleRate to supported values.
  // We create it first, then check actual rate after creation.
  audioCtx = new (window.AudioContext || window.webkitAudioContext)({
    sampleRate: SAMPLE_RATE,
    latencyHint: 'interactive',
  });

  // Reset the scheduling clock when context is created
  nextPlayTime = audioCtx.currentTime + SCHEDULE_AHEAD;

  gainNode = audioCtx.createGain();

  // Analyser for visualization
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 512;
  analyser.smoothingTimeConstant = 0.75;
  spectrumData = new Uint8Array(analyser.frequencyBinCount);

  gainNode.connect(analyser);
  analyser.connect(audioCtx.destination);

  const vol = document.getElementById('volumeSlider').value / 100;
  gainNode.gain.setValueAtTime(vol, audioCtx.currentTime);

  // Unlock AudioContext on any user gesture (required by browser autoplay policy)
  if (audioCtx.state === 'suspended') {
    audioCtx.resume().then(() => console.log('AudioContext resumed'));
  }

  startTime = audioCtx.currentTime;
  drawLoop();
}

// PCM 16-bit signed integer → float32 planar
function playPCMChunk(arrayBuffer) {
  if (!audioCtx) return;

  // Resume context if browser suspended it
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }

  const raw    = new Int16Array(arrayBuffer);
  const frames = raw.length / CHANNELS;

  if (frames === 0) return;

  // Use actual AudioContext sample rate (may differ from requested)
  const ctxRate = audioCtx.sampleRate;

  const audioBuffer = audioCtx.createBuffer(CHANNELS, frames, ctxRate);

  for (let ch = 0; ch < CHANNELS; ch++) {
    const channelData = audioBuffer.getChannelData(ch);
    for (let i = 0; i < frames; i++) {
      channelData[i] = raw[i * CHANNELS + ch] / 32768.0;
    }
    // Update waveform display buffer (use first channel)
    if (ch === 0) {
      waveformData = channelData.slice(0, Math.min(256, frames));
    }
  }

  // Compute peak & RMS
  computeAudioStats(audioBuffer.getChannelData(0));

  const source = audioCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(gainNode);

  // ── FIX: Sequential scheduling clock ──────────────────────────────────────
  // Each chunk must start AFTER the previous one ends.
  // If we've fallen behind real-time (e.g. tab was hidden), reset the clock.
  const now = audioCtx.currentTime;
  if (nextPlayTime < now + SCHEDULE_AHEAD) {
    // We're behind or starting fresh — reset to slightly ahead of now
    nextPlayTime = now + SCHEDULE_AHEAD;
  }

  source.start(nextPlayTime);

  // Advance the clock by the duration of this chunk
  const chunkDuration = frames / ctxRate;
  nextPlayTime += chunkDuration + CHUNK_GAP;

  // Latency display: how far ahead we're scheduling
  const latencyMs = Math.round((nextPlayTime - now) * 1000);
  latencyEl.textContent = `~${latencyMs}ms latency`;
}

function computeAudioStats(channelData) {
  let peak = 0, rmsSum = 0;
  for (let i = 0; i < channelData.length; i++) {
    const abs = Math.abs(channelData[i]);
    if (abs > peak) peak = abs;
    rmsSum += channelData[i] * channelData[i];
  }
  const rms = Math.sqrt(rmsSum / channelData.length);

  const peakDb = peak > 0 ? Math.round(20 * Math.log10(peak)) : -Infinity;
  const rmsDb  = rms  > 0 ? Math.round(20 * Math.log10(rms))  : -Infinity;

  document.getElementById('statPeak').textContent = isFinite(peakDb) ? peakDb : '-∞';
  document.getElementById('statRMS').textContent  = isFinite(rmsDb)  ? rmsDb  : '-∞';
}

// ── Visualizers ───────────────────────────────────────────────────────────────
function drawLoop() {
  animFrame = requestAnimationFrame(drawLoop);
  drawWaveform();
  drawSpectrum();
}

function drawWaveform() {
  const w = canvas.width  / (window.devicePixelRatio || 1);
  const h = canvas.height / (window.devicePixelRatio || 1);
  const ctx = waveformCtx;

  ctx.clearRect(0, 0, w, h);

  // Background grid
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (let y = 0; y <= 4; y++) {
    const yPos = (y / 4) * h;
    ctx.beginPath();
    ctx.moveTo(0, yPos);
    ctx.lineTo(w, yPos);
    ctx.stroke();
  }

  if (!analyser) return;

  // Time-domain data
  const timeData = new Float32Array(analyser.fftSize);
  analyser.getFloatTimeDomainData(timeData);

  // Draw waveform with gradient
  const grad = ctx.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0,   'rgba(0, 212, 170, 0.8)');
  grad.addColorStop(0.5, 'rgba(139, 92, 246, 0.9)');
  grad.addColorStop(1,   'rgba(0, 212, 170, 0.8)');

  ctx.strokeStyle = grad;
  ctx.lineWidth   = 2;
  ctx.lineJoin    = 'round';
  ctx.shadowColor = '#00d4aa';
  ctx.shadowBlur  = 8;
  ctx.beginPath();

  const step = timeData.length / w;
  for (let x = 0; x < w; x++) {
    const idx = Math.floor(x * step);
    const v   = timeData[idx] || 0;
    const y   = (1 - v) * 0.5 * h;
    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.shadowBlur = 0;
}

function drawSpectrum() {
  if (!analyser || !spectrumData) return;

  const w = specCanvas.width  / (window.devicePixelRatio || 1);
  const h = specCanvas.height / (window.devicePixelRatio || 1);
  const ctx = spectrumCtx;

  analyser.getByteFrequencyData(spectrumData);
  ctx.clearRect(0, 0, w, h);

  const barCount = Math.min(spectrumData.length, 80);
  const barWidth = w / barCount - 1;

  for (let i = 0; i < barCount; i++) {
    const val = spectrumData[i] / 255;
    const barH = val * h;

    const hue = 160 + (i / barCount) * 100;
    const grad = ctx.createLinearGradient(0, h - barH, 0, h);
    grad.addColorStop(0, `hsla(${hue}, 85%, 60%, 0.9)`);
    grad.addColorStop(1, `hsla(${hue}, 85%, 40%, 0.4)`);

    ctx.fillStyle = grad;
    ctx.fillRect(i * (barWidth + 1), h - barH, barWidth, barH);
  }
}

// ── Controls ──────────────────────────────────────────────────────────────────
function toggleListen() {
  if (!isListening) {
    initAudioContext();
    // Reset scheduling clock when starting fresh
    nextPlayTime = audioCtx.currentTime + SCHEDULE_AHEAD;
    audioCtx.resume();
    isListening = true;
    btnListenIcon.textContent = '⏸';
    btnListenText.textContent = 'Dừng nghe';
    liveBadge.style.display = 'inline-flex';
    waveOverlay.classList.add('hidden');
    if (!ws || ws.readyState !== WebSocket.OPEN) connect();
    if (!statsInterval) startStatsTimer();
  } else {
    isListening = false;
    nextPlayTime = 0; // Reset clock
    btnListenIcon.textContent = '▶';
    btnListenText.textContent = 'Bắt đầu nghe';
    liveBadge.style.display = 'none';
    if (audioCtx) audioCtx.suspend();
  }
}

function toggleMute() {
  isMuted = !isMuted;
  if (gainNode) gainNode.gain.setValueAtTime(isMuted ? 0 : document.getElementById('volumeSlider').value / 100, audioCtx.currentTime);
  muteIcon.textContent = isMuted ? '🔇' : '🔊';
}

function setVolume(val) {
  document.getElementById('volumeDisplay').textContent = val + '%';
  if (gainNode && !isMuted) gainNode.gain.setValueAtTime(val / 100, audioCtx.currentTime);
}

// ── Stats Timer ───────────────────────────────────────────────────────────────
function startStatsTimer() {
  statsInterval = setInterval(() => {
    const kbps = Math.round(bytesLastSec / 1024);
    document.getElementById('statKbps').textContent = kbps;
    bytesLastSec = 0;
  }, 1000);
}

// ── Status Updates ────────────────────────────────────────────────────────────
function updateStatus(state) {
  statusDot.className = 'status-dot';
  switch (state) {
    case 'connected':
      statusDot.classList.add('connected');
      statusText.textContent = 'Đã kết nối';
      wsStatusEl.textContent = 'Online';
      wsStatusEl.style.color = 'var(--color-connected)';
      break;
    case 'connecting':
      statusText.textContent = 'Đang kết nối...';
      wsStatusEl.textContent = 'Connecting...';
      wsStatusEl.style.color = 'var(--accent-blue)';
      break;
    case 'disconnected':
      statusText.textContent = 'Mất kết nối';
      wsStatusEl.textContent = 'Offline';
      wsStatusEl.style.color = 'var(--color-disconnected)';
      waveOverlay.classList.remove('hidden');
      waveOverlay.textContent = '🔌 Mất kết nối WebSocket...';
      break;
  }
}

function updateAudioInfo(cfg) {
  sampleRateEl.textContent = `${cfg.sampleRate / 1000}kHz`;
  formatEl.textContent = `PCM ${cfg.bitDepth}bit ${cfg.channels === 1 ? 'Mono' : 'Stereo'}`;
}

// ── System Status API Polling ─────────────────────────────────────────────────
async function fetchSystemStatus() {
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();

    micStatusEl.textContent = data.mic_connected ? 'Connected' : 'Disconnected';
    micStatusEl.style.color = data.mic_connected ? 'var(--color-connected)' : 'var(--color-disconnected)';

    document.getElementById('recStatus').textContent    = data.recording_enabled ? '● Active' : 'Disabled';
    document.getElementById('recStatus').style.color    = data.recording_enabled ? 'var(--color-recording)' : 'var(--text-muted)';

    statusDot.classList.toggle('recording', data.recording_enabled && data.mic_connected);
  } catch(e) {
    micStatusEl.textContent = 'API Error';
  }
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
connect();
setInterval(fetchSystemStatus, 10000);

// Draw idle animation even before listening
(function idleAnim() {
  if (!waveformCtx) { setTimeout(idleAnim, 200); return; }
  if (!isListening) {
    const w = canvas.width  / (window.devicePixelRatio || 1);
    const h = canvas.height / (window.devicePixelRatio || 1);
    waveformCtx.clearRect(0, 0, w, h);
    // Draw flat center line
    waveformCtx.strokeStyle = 'rgba(0,212,170,0.2)';
    waveformCtx.lineWidth = 1;
    waveformCtx.beginPath();
    waveformCtx.moveTo(0, h/2);
    waveformCtx.lineTo(w, h/2);
    waveformCtx.stroke();
    requestAnimationFrame(idleAnim);
  }
})();
