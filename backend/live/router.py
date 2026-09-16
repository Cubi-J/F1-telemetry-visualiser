import logging
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from .models import DashboardFrame, PlaybackState, ControlRequest
from .live_engine import live_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["live"])


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_available_sessions():
    """
    Returns available 2024 race sessions that can be loaded into replay mode.
    """
    try:
        sessions = await live_engine.openf1_client.get_sessions(year=2024, session_name="Race")
        return [
            {
                "session_key": s["session_key"],
                "country_name": s.get("country_name", ""),
                "circuit_short_name": s.get("circuit_short_name", ""),
                "location": s.get("location", ""),
                "date_start": s.get("date_start", ""),
                "year": s.get("year", 2024),
            }
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"Failed to fetch replay sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state", response_model=DashboardFrame)
async def get_live_state():
    """
    Returns the current snapshot frame for instant page rendering.
    """
    try:
        return await live_engine.get_current_frame()
    except Exception as e:
        logger.error(f"Failed to produce frame: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/control", response_model=PlaybackState)
async def handle_control_action(request: ControlRequest):
    """
    Controls playback: play, pause, seek, set_speed, load_session.
    """
    try:
        return await live_engine.handle_control(request)
    except Exception as e:
        logger.error(f"Control action failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.websocket("/ws")
async def websocket_live_stream(websocket: WebSocket):
    """
    WebSocket endpoint that streams unified DashboardFrame updates at 2 Hz
    and accepts control commands sent from the client.
    """
    await live_engine.connect_client(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = ControlRequest.model_validate_json(data)
                state = await live_engine.handle_control(msg)
                await websocket.send_text(state.model_dump_json())
            except Exception as parse_err:
                logger.warning(f"Invalid WebSocket control message received: {parse_err}")
    except WebSocketDisconnect:
        live_engine.disconnect_client(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        live_engine.disconnect_client(websocket)
