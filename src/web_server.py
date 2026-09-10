"""
web_server.py - Flask HTTP server phục vụ web interface và API
"""
import logging
import os
import threading
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, abort, Response

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).parent.parent / "web"


def create_app(config, recorder, mic_capture):
    """Tạo Flask app với các routes cần thiết"""
    app = Flask(__name__, static_folder=None)
    app.config['SECRET_KEY'] = 'micw-secret-key-change-in-prod'

    # ── Static Web Files ────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.route("/recordings")
    def recordings_page():
        return send_from_directory(WEB_DIR, "recordings.html")

    @app.route("/<path:filename>")
    def static_files(filename):
        try:
            return send_from_directory(WEB_DIR, filename)
        except Exception:
            abort(404)

    # ── API Endpoints ───────────────────────────────────────────────────────

    @app.route("/api/status")
    def api_status():
        """Trạng thái hệ thống"""
        return jsonify({
            "mic_connected": mic_capture.is_connected,
            "mic_device": mic_capture.device_index,
            "error": mic_capture.error_message,
            "recording_enabled": config.recording.enabled,
            "ws_port": config.websocket.port,
            "audio": {
                "sample_rate": config.audio.sample_rate,
                "channels": config.audio.channels,
                "bit_depth": config.audio.bit_depth,
            }
        })

    @app.route("/api/recordings")
    def api_recordings():
        """Danh sách file đã ghi"""
        try:
            recordings = recorder.get_recordings()
            return jsonify({
                "recordings": recordings,
                "total": len(recordings)
            })
        except Exception as e:
            logger.error(f"API recordings error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/recordings/<filename>")
    def api_download_recording(filename):
        """Download/stream file WAV đã ghi"""
        # Validate filename để tránh path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            abort(400)

        recordings_dir = config.recordings_dir
        filepath = recordings_dir / filename

        if not filepath.exists():
            abort(404)

        return send_from_directory(
            str(recordings_dir),
            filename,
            mimetype="audio/wav",
            as_attachment=False,
        )

    @app.route("/api/recordings/<filename>", methods=["DELETE"])
    def api_delete_recording(filename):
        """Xóa file ghi âm"""
        if ".." in filename or "/" in filename or "\\" in filename:
            abort(400)

        recordings_dir = config.recordings_dir
        filepath = recordings_dir / filename

        if not filepath.exists():
            abort(404)

        try:
            # Nếu recorder đang ghi file này, flush và đóng trước khi xóa
            if hasattr(recorder, '_current_file') and recorder._current_file == filepath:
                with recorder._lock:
                    recorder._close_current_file()
                    filepath.unlink()
                    if recorder._running:
                        recorder._open_new_file()
            else:
                filepath.unlink()

            logger.info(f"Đã xóa: {filename}")
            return jsonify({"success": True, "deleted": filename})
        except Exception as e:
            logger.error(f"Lỗi xóa file {filename}: {e}")
            return jsonify({"error": str(e)}), 500

    return app


def run_web_server(config, recorder, mic_capture):
    """Chạy Flask server trong thread riêng"""
    app = create_app(config, recorder, mic_capture)
    cfg = config.web

    logger.info(f"Web server starting on http://{cfg.host}:{cfg.port}")

    thread = threading.Thread(
        target=lambda: app.run(
            host=cfg.host,
            port=cfg.port,
            debug=False,
            use_reloader=False,
            threaded=True,
        ),
        daemon=True,
        name="web-server"
    )
    thread.start()
    logger.info(f"✓ Web server ready: http://localhost:{cfg.port}")
    return thread
