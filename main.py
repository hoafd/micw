"""
main.py - Entry point cho WO Mic Recording & Streaming System
Khởi động: MicCapture → Recorder → WebSocket Broadcaster → Web Server
"""
import sys
import os
import signal
import logging
import logging.handlers
import time
from pathlib import Path

# Thêm src vào path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config
from mic_capture import MicCapture
from recorder import AudioRecorder
from ws_broadcaster import WebSocketBroadcaster
from web_server import run_web_server


def setup_logging(config):
    """Cấu hình logging với file rotation"""
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)

    # Tạo thư mục logs
    log_path = config.log_file_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler với rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=config.logging.max_bytes,
        backupCount=config.logging.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return logging.getLogger(__name__)


def print_banner(config):
    """In thông tin khởi động"""
    ws_port = config.websocket.port
    web_port = config.web.port
    print("\n" + "=" * 60)
    print("  🎙️  WO Mic Recording & Streaming System")
    print("=" * 60)
    print(f"  📡 Audio Device  : WO Mic (index {config.audio.device_index})")
    print(f"  🎚️  Sample Rate   : {config.audio.sample_rate}Hz, "
          f"{config.audio.channels}ch, {config.audio.bit_depth}bit")
    print(f"  💾 Recording     : {'✓ Enabled' if config.recording.enabled else '✗ Disabled'}")
    if config.recording.enabled:
        print(f"  📁 Output Dir    : {config.recordings_dir}")
        seg = config.recording.segment_minutes
        print(f"  ⏱️  Segment       : {'No limit' if seg == 0 else f'{seg} min/file'}")
    print(f"  🔌 WebSocket     : ws://localhost:{ws_port}")
    print(f"  🌐 Web Server    : http://localhost:{web_port}")
    print(f"  🌐 Live Stream   : http://localhost:{web_port}/")
    print(f"  📼 Recordings    : http://localhost:{web_port}/recordings")
    print("=" * 60)
    print("  Press Ctrl+C to stop")
    print("=" * 60 + "\n")


def main():
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    config = load_config(str(config_path))

    # Setup logging
    logger = setup_logging(config)
    logger.info("Starting WO Mic System...")

    # Khởi tạo components
    mic = MicCapture(config)
    recorder = AudioRecorder(config)
    ws_broadcaster = WebSocketBroadcaster(config)

    # Đăng ký subscribers: mic → recorder, mic → ws_broadcaster
    mic.subscribe(recorder.write)
    mic.subscribe(ws_broadcaster.on_audio_chunk)

    # Khởi động services theo thứ tự
    logger.info("Starting WebSocket broadcaster...")
    ws_broadcaster.start()
    time.sleep(0.5)  # Chờ WS server init

    logger.info("Starting Web server...")
    run_web_server(config, recorder, mic)
    time.sleep(0.5)

    logger.info("Starting audio recorder...")
    recorder.start()

    logger.info("Starting mic capture...")
    mic.start()

    # In banner
    print_banner(config)

    # Handle Ctrl+C
    def shutdown(signum, frame):
        print("\n\nDừng hệ thống...")
        logger.info("Shutting down...")
        mic.stop()
        recorder.stop()
        ws_broadcaster.stop()
        logger.info("Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Main loop - giữ process sống và hiển thị status
    status_interval = 30  # giây
    last_status = time.time()

    while True:
        time.sleep(1)
        now = time.time()
        if now - last_status >= status_interval:
            status = "✓ Connected" if mic.is_connected else f"✗ {mic.error_message or 'Disconnected'}"
            logger.info(f"Status: Mic={status}, WS Clients={ws_broadcaster.client_count}")
            last_status = now


if __name__ == "__main__":
    main()
