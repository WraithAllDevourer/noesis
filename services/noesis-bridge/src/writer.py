from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_day() -> str:
    """Return current UTC day as YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def events_path(out_dir: Path, day: str) -> Path:
    """
    Return path:
      out/events/YYYY/YYYY-MM/events-YYYY-MM-DD.jsonl
    Creates parent directories if missing.
    """
    year = day[:4]
    month = day[:7]  # YYYY-MM
    p = out_dir / "events" / year / month
    p.mkdir(parents=True, exist_ok=True)
    return p / f"events-{day}.jsonl"


@dataclass
class EventWriter:
    """
    SuperPoC JSONL writer.

    - Append-only JSON Lines (1 event = 1 line JSON)
    - Daily rotation by UTC date
    - Flush after each write (SuperPoC safety)
    - Does not interpret or mutate events
    """
    out_dir: Path
    _current_day: Optional[str] = None
    _fh: Optional[Any] = None
    _current_path: Optional[Path] = None

    def _ensure_open(self, day: str) -> None:
        if self._fh and self._current_day == day:
            return

        # rotate
        self.close()

        path = events_path(self.out_dir, day)
        self._fh = open(path, "a", encoding="utf-8")
        self._current_day = day
        self._current_path = path

    def write_event(self, event: Dict[str, Any]) -> Path:
        """
        Write a single event as one JSONL line.
        Returns the file path used.
        """
        day = utc_day()
        self._ensure_open(day)

        # Ensure JSON serializable (no mutation)
        line = json.dumps(event, ensure_ascii=False)
        self._fh.write(line + "\n")
        self._fh.flush()

        # type: ignore[return-value]
        return self._current_path

    def close(self) -> None:
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None
        self._current_day = None
        self._current_path = None
