"""
ws_broadcaster.py - WebSocket server để stream audio real-time đến browsers
Nhận PCM chunks từ MicCapture và broadcast đến tất cả connected clients
"""
import asyncio
import logging
import threading
import queue
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class WebSocketBroadcaster:
    """
    WebSocket server phát audio PCM real-time.
    Clients (browsers) kết nối và nhận PCM data liên tục.
    """

    def __init__(self, config):
        self.config = config
        self._clients: Set[WebSocketServerProtocol] = set()
        self._server = None
        self._loop: asyncio.AbstractEventLoop = None
        self._thread: threading.Thread = None
        self._running = False
        self._chunk_counter = 0
        self._send_every = config.websocket.send_every_n_chunks
        self._buffer = bytearray()

    def on_audio_chunk(self, data: bytes):
        """
        Được gọi bởi MicCapture mỗi khi có audio data.
        Accumulate và gửi đến clients qua asyncio event loop.
        """
        if not self._running or not self._loop:
            return

        self._buffer.extend(data)
        self._chunk_counter += 1

        if self._chunk_counter >= self._send_every:
            chunk_to_send = bytes(self._buffer)
            self._buffer.clear()
            self._chunk_counter = 0

            if self._clients and self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._broadcast(chunk_to_send),
                    self._loop
                )

    async def _broadcast(self, data: bytes):
        """Gửi data đến tất cả connected clients"""
        if not self._clients:
            return

        disconnected = set()
        for client in self._clients:
            try:
                await client.send(data)
            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosedOK):
                disconnected.add(client)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")
                disconnected.add(client)

        # Xóa clients đã disconnect
        self._clients -= disconnected
        if disconnected:
            logger.info(f"Removed {len(disconnected)} disconnected client(s). "
                        f"Active: {len(self._clients)}")

    async def _handler(self, websocket: WebSocketServerProtocol):
        """Xử lý connection mới từ browser"""
        client_info = f"{websocket.remote_address}"
        logger.info(f"New WebSocket client: {client_info}")
        self._clients.add(websocket)

        try:
            # Gửi audio config để browser biết format
            import json
            cfg = self.config.audio
            await websocket.send(json.dumps({
                "type": "config",
                "sampleRate": cfg.sample_rate,
                "channels": cfg.channels,
                "bitDepth": cfg.bit_depth,
                "chunkSize": cfg.chunk_size * self._send_every
            }))

            # Giữ kết nối, lắng nghe ping/pong hoặc messages từ client
            async for message in websocket:
                # Client có thể gửi control messages (future use)
                pass

        except (websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError):
            pass
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self._clients.discard(websocket)
            logger.info(f"Client disconnected: {client_info}. "
                        f"Active: {len(self._clients)}")

    async def _run_server(self):
        """Chạy WebSocket server"""
        cfg = self.config.websocket
        logger.info(f"WebSocket server starting on ws://{cfg.host}:{cfg.port}")

        async with websockets.serve(
            self._handler,
            cfg.host,
            cfg.port,
            ping_interval=20,
            ping_timeout=20,
            max_size=None,
        ) as server:
            self._server = server
            logger.info(f"✓ WebSocket server ready: ws://localhost:{cfg.port}")
            await asyncio.Future()  # Chạy mãi đến khi bị cancel

    def start(self):
        """Bắt đầu WebSocket server trong thread riêng"""
        self._running = True
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="ws-broadcaster"
        )
        self._thread.start()
        logger.info("WebSocketBroadcaster started")

    def _run_loop(self):
        """Chạy asyncio event loop trong thread"""
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_server())
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")

    def stop(self):
        """Dừng WebSocket server"""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        logger.info("WebSocketBroadcaster stopped")

    @property
    def client_count(self) -> int:
        return len(self._clients)
