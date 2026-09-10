# Tasks & Findings

## Main Page (http://localhost:5000/)
- **Title**: WO Mic Live Stream | Nghe Trực Tiếp
- **Theme/Colors**: Dark mode aesthetic with dark navy blue / dark slate background (`#0B0F19` / dark palette), teal/cyan primary accents (`#10B981` / green & cyan highlights), glassmorphism cards with translucent dark borders.
- **Top Navigation Bar**:
  - Logo: "MicW - WO Mic Streaming" with microphone icon 🎙️.
  - Links: "🔴 Live Stream" (active tab with red glow/dot), "📼 Recordings".
  - Status Badge top right: "● Đã kết nối" (Connected).
- **Header Section**:
  - Title: "🎙️ Live Audio Stream"
  - Subtitle: "Nghe trực tiếp từ microphone điện thoại qua WO Mic"
- **Main Layout Grid**:
  - **Left / Main Column**:
    - **Waveform Card**: Header "Waveform — ms latency", canvas area showing canvas message "🔌 Đang chờ kết nối WebSocket...", controls bar with "▶ Bắt đầu nghe" button (cyan/teal primary button), Mute button (🔊 icon), volume slider set to 80%.
    - **Spectrum Analyzer Card**: Header "Spectrum Analyzer", canvas visualizer area.
  - **Right Column Sidebar**:
    - **Connection Card**: "Connection", WebSocket: Online (green), Mic Device: Connected (green), Sample Rate: 48kHz, Format: PCM 16bit Mono.
    - **Audio Stats Card**: 4 metric boxes (Peak dB: 0, RMS dB: 0, Packets counter: e.g. 211, KB/s: 0).
    - **System Card**: "System", Recording: ● Active (orange), WS Clients: —, Link button "📼 Xem Recordings".

## Recordings Page (http://localhost:5000/recordings)
- **Title**: WO Mic Recordings | Nghe Lại
- **Theme/Colors**: Dark mode matching main page with dark background, glassmorphism cards, cyan/teal accent text & buttons.
- **Top Navigation Bar**:
  - Logo: "MicW - WO Mic Streaming".
  - Links: "🔴 Live Stream", "📼 Recordings" (active tab with green background highlight).
  - Status Badge top right: "● Mic Active".
- **Header Section**:
  - Title: "📼 Recordings"
  - Subtitle: "Nghe lại các file âm thanh đã ghi từ WO Mic"
- **Summary Stat Cards (4 Cards)**:
  - 1 Total Files
  - 4MB Total Size
  - 44s Total Duration
  - 48kHz Sample Rate
- **Search & Filter Controls Bar**:
  - Search Input Box: "🔍 Tìm kiếm file..."
  - Buttons: "🔄 Refresh", "📅 Ngày", "📦 Kích thước", "⏱ Thời lượng"
- **Recording List Section**:
  - Header: "Danh sách file ghi âm" (shows "1 file")
  - Item Card:
    - Icon: 🎙️
    - Filename: `rec_20260910_220955.wav`
    - Metadata: `10/09/2026 22:09:55 · 00:44 · 4.04MB · 48kHz`
    - Action Buttons: "⏸ Đang phát" (teal button), "⬇" Download button, "🗑" Delete button.
- **Bottom Fixed Audio Player Bar**:
  - Left: Filename `rec_20260910_220955.wav`, metadata `00:44 · 4.04MB · 48kHz`.
  - Center: HTML5 Audio player control widget (`0:03 / 0:46`).
  - Right: "⬇ Download" button, "✕" close player button.

