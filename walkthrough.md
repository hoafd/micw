# 🎙️ MicW - WO Mic Streaming System

Hệ thống đã được xây dựng và đang chạy thành công!

## ✅ Kết quả

![Live Stream Page](file:///C:/Users/admin/.gemini/antigravity-ide/brain/99f19da1-a676-407c-88ba-aaeebddb08b2/main_page_live_stream_1789053028383.png)
*Trang Live Stream - nghe trực tiếp từ WO Mic*

![Recordings Page](file:///C:/Users/admin/.gemini/antigravity-ide/brain/99f19da1-a676-407c-88ba-aaeebddb08b2/recordings_page_1789053047339.png)
*Trang Recordings - nghe lại âm thanh đã ghi*

## 🌐 Truy cập

| URL | Chức năng |
|-----|-----------|
| http://localhost:5000/ | 🔴 Live Stream - nghe trực tiếp |
| http://localhost:5000/recordings | 📼 Recordings - nghe lại |

## 📁 Cấu trúc dự án

```
micw/
├── config.yaml          ← Cấu hình (thiết bị mic, ports, thư mục...)
├── main.py              ← Entry point - chạy tất cả services
├── requirements.txt     ← Dependencies Python
├── start.bat            ← Script khởi động Windows
├── src/
│   ├── config.py        ← Load config từ YAML
│   ├── mic_capture.py   ← Capture audio từ WO Mic Device
│   ├── recorder.py      ← Ghi WAV files với auto-segment
│   ├── ws_broadcaster.py← WebSocket server stream audio
│   └── web_server.py    ← Flask HTTP server + API
├── web/
│   ├── index.html       ← Trang Live Stream
│   ├── recordings.html  ← Trang Recordings
│   ├── style.css        ← Design system
│   ├── live.js          ← WebSocket + Web Audio + Visualizer
│   └── recordings.js    ← Playback + Delete + Sort
└── recordings/          ← WAV files được ghi tự động
```

## ⚙️ Cấu hình (config.yaml)

Chỉnh sửa [config.yaml](file:///c:/Users/admin/Chương trình riêng/Source/micw/config.yaml) để thay đổi:
- `audio.device_index`: Index của WO Mic Device (mặc định: 9)
- `audio.sample_rate`: 48000Hz
- `recording.segment_minutes`: Mỗi file lưu bao nhiêu phút (mặc định: 10)
- `recording.max_files`: Số file tối đa giữ lại (mặc định: 50)
- `websocket.port`: Port WebSocket (mặc định: 8765)
- `web.port`: Port Web (mặc định: 5000)

## 🚀 Cách chạy

```powershell
# Chạy từ terminal
python main.py

# Hoặc double-click file
start.bat
```

## 🔧 Kiến trúc

```
[WO Mic App (Phone)]
        │
  WiFi TCP 192.168.10.80:8125
        │
[WO Mic Virtual Driver (Windows)]
        │
[PyAudio → MicCapture]
     /        \
[Recorder]  [WS Broadcaster]
  │WAV files    │WebSocket ws://8765
[recordings/]   │
          [Browser]
          ├── Live: Web Audio API → Speaker
          └── Recordings: HTML5 Audio Player
```

## 📊 Status hiện tại

| Service | Status |
|---------|--------|
| WO Mic Device (index 9, 48kHz) | ✅ Connected |
| Audio Recorder | ✅ Active |
| WebSocket Server (:8765) | ✅ Running |
| Web Server (:5000) | ✅ Running |
