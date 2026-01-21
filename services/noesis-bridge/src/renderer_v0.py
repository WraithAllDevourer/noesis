from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class RendererConfig:
    out_dir: Path
    identity_map_path: Path
    templates_path: Path
    language: str = "pl"
    follow_utc: bool = True
    from_start: bool = False
    poll_ms: int = 200


def utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def local_day() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def find_events_file(out_dir: Path, day: str) -> Optional[Path]:
    year = day[:4]
    month = day[:7]
    p = out_dir / "events" / year / month / f"events-{day}.jsonl"
    return p if p.exists() else None


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_config(path: Path) -> RendererConfig:
    d = load_yaml(path)
    return RendererConfig(
        out_dir=Path(d["out_dir"]),
        identity_map_path=Path(d["identity_map_path"]),
        templates_path=Path(d["templates_path"]),
        language=str(d.get("language", "pl")).lower(),
        follow_utc=bool(d.get("follow_utc", True)),
        from_start=bool(d.get("from_start", False)),
        poll_ms=int(d.get("poll_ms", 200)),
    )


def resolve_name(dbref: str, mapping: Dict[str, str]) -> str:
    return mapping.get(dbref, dbref)


def render_event(
    ev: Dict[str, Any],
    lang: str,
    templates: Dict[str, Any],
    actors: Dict[str, str],
    locations: Dict[str, str],
) -> Optional[str]:
    etype = ev.get("type")
    ts = ev.get("ts_utc", "")

    actor_dbref = (ev.get("actor") or {}).get("dbref") or ""
    actor_name = resolve_name(actor_dbref, actors)

    if etype == "SAY":
        tpl = (
            templates.get("SAY", {}).get(lang)
            or templates.get("SAY", {}).get("en")
            or "{ts} {actor} {verb}: {raw}  @ {location}"
        )
        loc_dbref = (ev.get("location") or {}).get("dbref") or ""
        loc_name = resolve_name(loc_dbref, locations)
        content = ev.get("content") or {}
        raw = content.get("raw") or ""
        verb = content.get("verb") or ("mówi" if lang == "pl" else "says")
        return tpl.format(ts=ts, actor=actor_name, location=loc_name, raw=raw, verb=verb)

    if etype == "MOVE":
        tpl = templates.get("MOVE", {}).get(lang) or templates.get("MOVE", {}).get("en") or "{ts} {actor} moves"
        content = ev.get("content") or {}
        frm = content.get("from", "")
        to = content.get("to", "")
        frm_name = resolve_name(frm, locations)
        to_name = resolve_name(to, locations)
        return tpl.format(ts=ts, actor=actor_name, from_loc=frm_name, to_loc=to_name)

    return None


def write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    tmp.replace(path)


def main() -> None:
    cfg_path = Path("/opt/tinymux/services/noesis-bridge/renderer_config.yaml")
    cfg = load_config(cfg_path)

    ident = load_json(cfg.identity_map_path)
    actors = ident.get("actors", {})
    locations = ident.get("locations", {})
    templates = load_yaml(cfg.templates_path)

    poll_s = max(cfg.poll_ms, 50) / 1000.0
    hb_path = cfg.out_dir / "renderer.heartbeat.json"
    last_line_ts = time.time()
    last_hb_emit = 0.0

    while True:
        day = utc_day() if cfg.follow_utc else local_day()
        events_file = find_events_file(cfg.out_dir, day)
        while events_file is None:
            print(f"[renderer] waiting for events file for {day}...")
            time.sleep(1.0)
            day = utc_day() if cfg.follow_utc else local_day()
            events_file = find_events_file(cfg.out_dir, day)

        print(f"[renderer] following: {events_file}")
        with open(events_file, "r", encoding="utf-8") as f:
            if not cfg.from_start:
                f.seek(0, 2)

            while True:
                # rotacja dnia: jeśli zmieniła się data, wyjdź i otwórz nowy plik
                current_day = utc_day() if cfg.follow_utc else local_day()
                if current_day != day:
                    break

                pos = f.tell()
                line = f.readline()
                if not line:
                    f.seek(pos)
                    time.sleep(poll_s)
                else:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except Exception:
                        print(f"[renderer] bad json line: {line[:160]}")
                        continue

                    out = render_event(ev, cfg.language, templates, actors, locations)
                    if out:
                        print(out)
                    last_line_ts = time.time()

                now = time.time()
                if now - last_hb_emit >= 30.0:
                    last_hb_emit = now
                    hb = {
                        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        "pid": os.getpid(),
                        "last_line_ts": last_line_ts,
                        "following_day": day,
                        "poll_ms": cfg.poll_ms,
                    }
                    # os.getpid() wymaga os:
                    # dodamy import lokalnie, żeby było 100% pewne:
                    try:
                        import os as _os
                        hb["pid"] = _os.getpid()
                    except Exception:
                        pass
                    write_json_atomic(hb_path, hb)

if __name__ == "__main__":
    main()
