"""
recorder.py - Ghi âm thanh từ WO Mic thành WAV files
Hỗ trợ auto-segment theo thời gian và quản lý file
"""
import logging
import os
import wave
import threading
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class AudioRecorder:
    """
    Ghi PCM data vào WAV files.
    - Tự động tạo segment mới theo thời gian cấu hình
    - Quản lý số lượng file tối đa
    - Lưu metadata kèm theo
    """

    def __init__(self, config):
        self.config = config
        self._wav_file: Optional[wave.Wave_write] = None
        self._current_file: Optional[Path] = None
        self._segment_start: Optional[datetime] = None
        self._frames_written = 0
        self._lock = threading.Lock()
        self._running = False
        self._session_index = 0

        # Tạo thư mục recordings
        self.output_dir = config.recordings_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Recordings dir: {self.output_dir}")

    def start(self):
        """Bắt đầu recording session"""
        if not self.config.recording.enabled:
            logger.info("Recording disabled trong config")
            return
        self._running = True
        self._open_new_file()
        logger.info("AudioRecorder started")

    def stop(self):
        """Dừng recording và đóng file hiện tại"""
        self._running = False
        with self._lock:
            self._close_current_file()
        logger.info("AudioRecorder stopped")

    def write(self, pcm_data: bytes):
        """Nhận PCM chunk và ghi vào WAV file"""
        if not self._running or not self.config.recording.enabled:
            return

        with self._lock:
            # Kiểm tra có cần segment mới không
            if self._should_rotate():
                self._close_current_file()
                self._open_new_file()

            if self._wav_file:
                try:
                    self._wav_file.writeframes(pcm_data)
                    self._frames_written += len(pcm_data) // (self.config.audio.bit_depth // 8)
                except Exception as e:
                    logger.error(f"Lỗi ghi WAV: {e}")

    def _should_rotate(self) -> bool:
        """Kiểm tra có nên tạo file segment mới không"""
        seg_minutes = self.config.recording.segment_minutes
        if seg_minutes <= 0 or not self._segment_start:
            return False
        elapsed = (datetime.now() - self._segment_start).total_seconds()
        return elapsed >= seg_minutes * 60

    def _open_new_file(self):
        """Tạo WAV file mới"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._session_index += 1
        filename = f"{self.config.recording.filename_prefix}_{timestamp}.wav"
        filepath = self.output_dir / filename

        try:
            cfg = self.config.audio
            wav = wave.open(str(filepath), 'wb')
            wav.setnchannels(cfg.channels)
            wav.setsampwidth(cfg.bit_depth // 8)
            wav.setframerate(cfg.sample_rate)
            self._wav_file = wav
            self._current_file = filepath
            self._segment_start = datetime.now()
            self._frames_written = 0
            logger.info(f"Ghi vào file mới: {filename}")
        except Exception as e:
            logger.error(f"Không thể tạo WAV file: {e}")
            self._wav_file = None

    def _close_current_file(self):
        """Đóng WAV file hiện tại"""
        if self._wav_file:
            try:
                self._wav_file.close()
                logger.info(f"Đã lưu: {self._current_file.name} "
                             f"({self._frames_written} frames)")
            except Exception as e:
                logger.error(f"Lỗi đóng WAV file: {e}")
            finally:
                self._wav_file = None

        # Dọn file cũ nếu vượt max_files
        self._cleanup_old_files()

    def _cleanup_old_files(self):
        """Xóa file cũ nếu vượt quá max_files"""
        max_files = self.config.recording.max_files
        if max_files <= 0:
            return

        prefix = self.config.recording.filename_prefix
        files = sorted(
            self.output_dir.glob(f"{prefix}_*.wav"),
            key=lambda p: p.stat().st_mtime
        )

        while len(files) > max_files:
            oldest = files.pop(0)
            try:
                oldest.unlink()
                logger.info(f"Xóa file cũ: {oldest.name}")
            except Exception as e:
                logger.error(f"Không thể xóa {oldest.name}: {e}")

    def get_recordings(self) -> List[Dict]:
        """Trả về danh sách file đã ghi với metadata"""
        prefix = self.config.recording.filename_prefix
        files = sorted(
            self.output_dir.glob(f"{prefix}_*.wav"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        result = []
        for f in files:
            try:
                stat = f.stat()
                # Đọc metadata WAV
                duration_secs = 0
                sample_rate = self.config.audio.sample_rate
                try:
                    with wave.open(str(f), 'rb') as w:
                        frames = w.getnframes()
                        rate = w.getframerate()
                        duration_secs = frames / rate if rate > 0 else 0
                        sample_rate = rate
                except Exception:
                    pass

                result.append({
                    "filename": f.name,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "duration_seconds": round(duration_secs, 1),
                    "duration_str": self._format_duration(duration_secs),
                    "sample_rate": sample_rate,
                })
            except Exception as e:
                logger.error(f"Lỗi đọc metadata {f.name}: {e}")

        return result

    @staticmethod
    def _format_duration(seconds: float) -> str:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
