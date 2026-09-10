"""
config.py - Load và validate configuration từ config.yaml
"""
import os
import yaml
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class AudioConfig:
    device_index: int = 9
    device_name: str = "WO Mic"
    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 16
    chunk_size: int = 1024


@dataclass
class RecordingConfig:
    enabled: bool = True
    output_dir: str = "recordings"
    segment_minutes: int = 10
    filename_prefix: str = "rec"
    max_files: int = 50


@dataclass
class WebSocketConfig:
    host: str = "0.0.0.0"
    port: int = 8765
    send_every_n_chunks: int = 2


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    log_file: str = "logs/micw.log"
    max_bytes: int = 10485760
    backup_count: int = 3


@dataclass
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    web: WebConfig = field(default_factory=WebConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @property
    def recordings_dir(self) -> Path:
        path = Path(self.recording.output_dir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @property
    def log_file_path(self) -> Path:
        path = Path(self.logging.log_file)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load config từ YAML file, trả về AppConfig với defaults nếu file không tồn tại"""

    if config_path is None:
        config_path = PROJECT_ROOT / "config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        logger.warning(f"Config file không tìm thấy: {config_path}. Dùng defaults.")
        return AppConfig()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    logger.info(f"Đã load config từ: {config_path}")

    config = AppConfig()

    # Audio
    if "audio" in data:
        a = data["audio"]
        config.audio = AudioConfig(
            device_index=a.get("device_index", 9),
            device_name=a.get("device_name", "WO Mic"),
            sample_rate=a.get("sample_rate", 48000),
            channels=a.get("channels", 1),
            bit_depth=a.get("bit_depth", 16),
            chunk_size=a.get("chunk_size", 1024),
        )

    # Recording
    if "recording" in data:
        r = data["recording"]
        config.recording = RecordingConfig(
            enabled=r.get("enabled", True),
            output_dir=r.get("output_dir", "recordings"),
            segment_minutes=r.get("segment_minutes", 10),
            filename_prefix=r.get("filename_prefix", "rec"),
            max_files=r.get("max_files", 50),
        )

    # WebSocket
    if "websocket" in data:
        ws = data["websocket"]
        config.websocket = WebSocketConfig(
            host=ws.get("host", "0.0.0.0"),
            port=ws.get("port", 8765),
            send_every_n_chunks=ws.get("send_every_n_chunks", 2),
        )

    # Web
    if "web" in data:
        w = data["web"]
        config.web = WebConfig(
            host=w.get("host", "0.0.0.0"),
            port=w.get("port", 5000),
            debug=w.get("debug", False),
        )

    # Logging
    if "logging" in data:
        lg = data["logging"]
        config.logging = LoggingConfig(
            level=lg.get("level", "INFO"),
            log_file=lg.get("log_file", "logs/micw.log"),
            max_bytes=lg.get("max_bytes", 10485760),
            backup_count=lg.get("backup_count", 3),
        )

    return config
