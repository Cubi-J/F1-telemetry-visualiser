import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import httpx

logger = logging.getLogger(__name__)

OPENF1_BASE_URL = "https://api.openf1.org/v1"
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "openf1_replays"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class OpenF1Client:
    def __init__(self, base_url: str = OPENF1_BASE_URL):
        self.base_url = base_url
        self.timeout = httpx.Timeout(30.0, connect=10.0)

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/{endpoint}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            if response.status_code != 200:
                logger.warning(f"OpenF1 API {endpoint} returned {response.status_code}: {response.text}")
                return []
            data = response.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "detail" in data:
                return []
            return [data] if data else []

    async def get_sessions(self, year: int = 2024, session_name: str = "Race") -> List[Dict[str, Any]]:
        return await self._get("sessions", {"year": year, "session_name": session_name})

    async def get_session_by_key(self, session_key: int) -> Optional[Dict[str, Any]]:
        sessions = await self._get("sessions", {"session_key": session_key})
        return sessions[0] if sessions else None

    async def get_drivers(self, session_key: int) -> List[Dict[str, Any]]:
        return await self._get("drivers", {"session_key": session_key})

    async def get_positions(self, session_key: int) -> List[Dict[str, Any]]:
        return await self._get("position", {"session_key": session_key})

    async def get_intervals(self, session_key: int) -> List[Dict[str, Any]]:
        return await self._get("intervals", {"session_key": session_key})

    async def get_laps(self, session_key: int) -> List[Dict[str, Any]]:
        return await self._get("laps", {"session_key": session_key})

    async def get_stints(self, session_key: int) -> List[Dict[str, Any]]:
        return await self._get("stints", {"session_key": session_key})

    async def get_weather(self, session_key: int) -> List[Dict[str, Any]]:
        return await self._get("weather", {"session_key": session_key})

    async def get_race_control(self, session_key: int) -> List[Dict[str, Any]]:
        return await self._get("race_control", {"session_key": session_key})

    async def get_locations(
        self,
        session_key: int,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query_parts = [f"session_key={session_key}"]
        if date_start:
            query_parts.append(f"date>={date_start}")
        if date_end:
            query_parts.append(f"date<={date_end}")
        url = f"{self.base_url}/location?{'&'.join(query_parts)}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(f"OpenF1 API location returned {response.status_code}: {response.text}")
                return []
            data = response.json()
            return data if isinstance(data, list) else []

    async def load_or_fetch_replay_bundle(
        self,
        session_key: int = 9523,  # Monaco 2024 default
        duration_minutes: int = 10,
    ) -> Dict[str, Any]:
        """
        Loads a pre-cached replay session bundle or fetches it from OpenF1 and persists to disk.
        """
        cache_file = CACHE_DIR / f"session_{session_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("locations") and len(data["locations"]) > 0:
                        logger.info(f"Loaded replay session {session_key} from disk cache.")
                        return data
            except Exception as e:
                logger.error(f"Failed to read cache file {cache_file}: {e}")

        logger.info(f"Fetching replay session {session_key} from OpenF1 API...")
        session_info = await self.get_session_by_key(session_key)
        if not session_info:
            raise ValueError(f"Session {session_key} not found in OpenF1.")

        drivers = await self.get_drivers(session_key)
        laps = await self.get_laps(session_key)
        stints = await self.get_stints(session_key)
        positions = await self.get_positions(session_key)
        intervals = await self.get_intervals(session_key)
        weather = await self.get_weather(session_key)
        race_control = await self.get_race_control(session_key)

        # Determine active start time from lap 1 or session date_start
        valid_lap_dates = [l["date_start"] for l in laps if l.get("date_start")]
        if valid_lap_dates:
            start_iso = min(valid_lap_dates)
        else:
            start_iso = session_info.get("date_start", "2024-05-26T13:44:00+00:00")

        # Compute end time
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        start_filter = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        end_filter = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        logger.info(f"Fetching car locations between {start_filter} and {end_filter}...")
        locations = await self.get_locations(session_key, date_start=start_filter, date_end=end_filter)

        bundle = {
            "session_info": session_info,
            "drivers": drivers,
            "laps": laps,
            "stints": stints,
            "positions": positions,
            "intervals": intervals,
            "weather": weather,
            "race_control": race_control,
            "locations": locations,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
        }

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(bundle, f)
            logger.info(f"Saved replay session {session_key} to cache ({cache_file}).")
        except Exception as e:
            logger.error(f"Failed to write cache file {cache_file}: {e}")

        return bundle
