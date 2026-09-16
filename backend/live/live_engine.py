import asyncio
import json
import logging
from typing import Set, Optional, Dict, Any
from fastapi import WebSocket

from .models import DashboardFrame, PlaybackState, ControlRequest
from .session_provider import SessionDataProvider
from .replay_provider import ReplaySessionProvider
from .openf1_client import OpenF1Client

logger = logging.getLogger(__name__)


class LiveEngineManager:
    """
    Coordinates the active session data provider (Replay or Live),
    manages WebSocket client connections, and runs the high-frequency broadcast tick loop.
    """

    def __init__(self):
        self.provider: SessionDataProvider = ReplaySessionProvider(session_key=9523, duration_minutes=10)
        self.active_connections: Set[WebSocket] = set()
        self.broadcast_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.tick_interval_sec = 0.5  # 2 Hz frame updates
        self.openf1_client = OpenF1Client()

    async def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        await self.provider.initialize()
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("LiveEngineManager broadcast loop started.")

    async def stop(self) -> None:
        self.is_running = False
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass
        await self.provider.cleanup()
        logger.info("LiveEngineManager stopped.")

    async def connect_client(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

        # Send immediate initial frame on connect
        try:
            frame = await self.provider.get_current_frame()
            await websocket.send_text(frame.model_dump_json())
        except Exception as e:
            logger.error(f"Error sending initial frame to client: {e}")

    def disconnect_client(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Remaining clients: {len(self.active_connections)}")

    async def get_current_frame(self) -> DashboardFrame:
        return await self.provider.get_current_frame()

    async def switch_session(self, session_key: int) -> None:
        logger.info(f"Switching replay session to session_key={session_key}")
        old_provider = self.provider
        new_provider = ReplaySessionProvider(session_key=session_key)
        await new_provider.initialize()
        self.provider = new_provider
        await old_provider.cleanup()

    async def handle_control(self, req: ControlRequest) -> PlaybackState:
        if req.action == "play":
            await self.provider.play()
        elif req.action == "pause":
            await self.provider.pause()
        elif req.action == "seek" and req.timestamp:
            await self.provider.seek(req.timestamp)
        elif req.action == "set_speed" and req.speed is not None:
            await self.provider.set_speed(req.speed)
        elif req.action == "load_session" and req.session_key is not None:
            await self.switch_session(req.session_key)

        return self.provider.get_playback_state()

    async def _broadcast_loop(self) -> None:
        while self.is_running:
            try:
                if self.active_connections:
                    frame = await self.provider.get_current_frame()
                    frame_json = frame.model_dump_json()

                    disconnected = set()
                    for ws in self.active_connections:
                        try:
                            await ws.send_text(frame_json)
                        except Exception:
                            disconnected.add(ws)

                    for ws in disconnected:
                        self.active_connections.discard(ws)

            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")

            await asyncio.sleep(self.tick_interval_sec)


# Global singleton engine instance
live_engine = LiveEngineManager()
