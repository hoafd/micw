"""
mic_capture.py - Capture audio từ WO Mic Device qua PyAudio
Phân phối PCM data đến recorder và WebSocket broadcaster
"""
import asyncio
import logging
import threading
import time
import wave
import pyaudio
from pathlib import Path
from datetime import datetime
from typing import Optional, Set, Callable

logger = logging.getLogger(__name__)


class MicCapture:
    """
    Capture audio từ WO Mic virtual device.
    Dùng PyAudio để đọc PCM data và phân phối đến các subscribers.
    """

    def __init__(self, config):
        self.config = config
        self._pa: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._subscribers: Set[Callable] = set()
        self._lock = threading.Lock()
        self.device_index: Optional[int] = None
        self.is_connected = False
        self.error_message: Optional[str] = None

    def find_device(self) -> Optional[int]:
        """Tìm WO Mic device index"""
        pa = pyaudio.PyAudio()
        try:
            cfg = self.config.audio

            # Ưu tiên device_index từ config (nếu không phải -1)
            if cfg.device_index >= 0:
                try:
                    info = pa.get_device_info_by_index(cfg.device_index)
                    if info['maxInputChannels'] > 0:
                        logger.info(f"Dùng device [{cfg.device_index}]: {info['name']}")
                        return cfg.device_index
                    else:
                        logger.warning(f"Device [{cfg.device_index}] không có input channel")
                except Exception:
                    logger.warning(f"Device index {cfg.device_index} không hợp lệ")

            # Tìm theo tên
            search_name = cfg.device_name.lower()
            best_idx = None
            best_rate_diff = float('inf')

            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if (info['maxInputChannels'] > 0 and
                        search_name in info['name'].lower()):
                    rate_diff = abs(info['defaultSampleRate'] - cfg.sample_rate)
                    if rate_diff < best_rate_diff:
                        best_rate_diff = rate_diff
                        best_idx = i
                        logger.info(f"Found WO Mic device [{i}]: {info['name']} "
                                    f"@ {info['defaultSampleRate']}Hz")

            if best_idx is not None:
                return best_idx

            logger.error("Không tìm thấy WO Mic device!")
            return None
        finally:
            pa.terminate()

    def subscribe(self, callback: Callable):
        """Đăng ký nhận PCM data. callback(data: bytes) sẽ được gọi mỗi chunk"""
        with self._lock:
            self._subscribers.add(callback)

    def unsubscribe(self, callback: Callable):
        with self._lock:
            self._subscribers.discard(callback)

    def _notify_subscribers(self, data: bytes):
        with self._lock:
            subs = set(self._subscribers)
        for cb in subs:
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Subscriber error: {e}")

    def start(self):
        """Bắt đầu capture trong background thread"""
        if self._running:
            logger.warning("MicCapture đã đang chạy")
            return

        self.device_index = self.find_device()
        if self.device_index is None:
            self.error_message = "Không tìm thấy WO Mic device"
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("MicCapture started")

    def stop(self):
        """Dừng capture"""
        self._running = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
        self.is_connected = False
        logger.info("MicCapture stopped")

    def _capture_loop(self):
        """Main capture loop chạy trong thread riêng"""
        retry_delay = 2

        while self._running:
            try:
                self._pa = pyaudio.PyAudio()
                cfg = self.config.audio

                # Map bit_depth sang PyAudio format
                format_map = {8: pyaudio.paInt8, 16: pyaudio.paInt16, 32: pyaudio.paInt32}
                pa_format = format_map.get(cfg.bit_depth, pyaudio.paInt16)

                logger.info(f"Mở audio stream: device={self.device_index}, "
                            f"rate={cfg.sample_rate}, channels={cfg.channels}")

                self._stream = self._pa.open(
                    format=pa_format,
                    channels=cfg.channels,
                    rate=cfg.sample_rate,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=cfg.chunk_size,
                )

                self.is_connected = True
                self.error_message = None
                logger.info("✓ Audio stream mở thành công!")
                retry_delay = 2  # Reset retry delay

                while self._running:
                    data = self._stream.read(cfg.chunk_size, exception_on_overflow=False)
                    self._notify_subscribers(data)

            except OSError as e:
                self.is_connected = False
                self.error_message = str(e)
                logger.error(f"Audio stream error: {e}")
                if self._running:
                    logger.info(f"Thử lại sau {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)
            except Exception as e:
                self.is_connected = False
                self.error_message = str(e)
                logger.error(f"Unexpected error: {e}")
                if self._running:
                    time.sleep(retry_delay)
            finally:
                if self._stream:
                    try:
                        self._stream.stop_stream()
                        self._stream.close()
                    except Exception:
                        pass
                    self._stream = None
                if self._pa:
                    try:
                        self._pa.terminate()
                    except Exception:
                        pass
                    self._pa = None
