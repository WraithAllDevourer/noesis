#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import socket
import time
import uuid
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from writer import EventWriter


def iso_utc_now_ms() -> str:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(dt.microsecond / 1000):03d}Z"


def iso_utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def make_run_id() -> str:
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    suffix = uuid.uuid4().hex[:6]
    return f"{started}-{suffix}"


@dataclass
class BridgeConfig:
    host: str
    port: int
    username: str
    password: str
    out_dir: Path
    meta_subdir: str = "meta"
    logs_subdir: str = "logs"
    log_level: str = "INFO"
    mode_name: str = "dry_run"  # dry_run | record


def load_config(path: Path) -> BridgeConfig:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def get(dct: Dict[str, Any], *keys: str) -> Any:
        cur: Any = dct
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return None
            cur = cur[k]
        return cur

    host = get(data, "connection", "host")
    port = get(data, "connection", "port")
    username = get(data, "auth", "username")
    password = get(data, "auth", "password")
    out_dir = get(data, "output", "out_dir")

    meta_subdir = get(data, "output", "meta_subdir") or "meta"
    logs_subdir = get(data, "output", "logs_subdir") or "logs"
    log_level = get(data, "logging", "level") or "INFO"
    mode_name = get(data, "mode", "name") or "dry_run"

    if not isinstance(host, str) or not host.strip():
        raise ValueError("Invalid config: connection.host must be a non-empty string")
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError("Invalid config: connection.port must be int in range 1..65535")
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Invalid config: auth.username must be a non-empty string")
    if not isinstance(password, str) or not password:
        raise ValueError("Invalid config: auth.password must be a non-empty string")
    if not isinstance(out_dir, str) or not out_dir.strip():
        raise ValueError("Invalid config: output.out_dir must be a non-empty string path")

    mode_name = str(mode_name).lower().strip()
    if mode_name not in ("dry_run", "record"):
        raise ValueError("Invalid config: mode.name must be 'dry_run' or 'record'")

    return BridgeConfig(
        host=host.strip(),
        port=port,
        username=username.strip(),
        password=password,
        out_dir=Path(out_dir.strip()),
        meta_subdir=str(meta_subdir),
        logs_subdir=str(logs_subdir),
        log_level=str(log_level).upper(),
        mode_name=mode_name,
    )


class TechLogger:
    def __init__(self, log_dir: Path, level: str = "INFO") -> None:
        self.log_dir = log_dir
        self.level = level
        self._fh: Optional[Any] = None
        self._current_day: Optional[str] = None

    def _ensure_open(self) -> None:
        day = iso_utc_date()
        if self._fh and self._current_day == day:
            return
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"bridge-{day}.log"
        self._fh = open(path, "a", encoding="utf-8")
        self._current_day = day

    def log(self, msg: str) -> None:
        self._ensure_open()
        line = f"{iso_utc_now_ms()} {msg}\n"
        self._fh.write(line)
        self._fh.flush()
        print(line, end="")

    def close(self) -> None:
        if self._fh:
            try:
                self._fh.close()
            except Exception:
                pass
        self._fh = None
        self._current_day = None


class MuxClient:
    def __init__(self, host: str, port: int, logger: TechLogger) -> None:
        self.host = host
        self.port = port
        self.logger = logger
        self.sock: Optional[socket.socket] = None

    def connect(self, timeout_s: float = 10.0) -> None:
        self.logger.log(f"[mux] connecting to {self.host}:{self.port}")
        s = socket.create_connection((self.host, self.port), timeout=timeout_s)
        s.settimeout(2.0)
        self.sock = s
        self.logger.log("[mux] connected")

    def recv_some(self) -> str:
        if not self.sock:
            return ""
        try:
            data = self.sock.recv(4096)
            if data == b"":
                # peer closed connection
                raise ConnectionError("socket closed by peer")
            return data.decode("utf-8", errors="replace")
        except socket.timeout:
            return ""
        except Exception as e:
            self.logger.log(f"[mux] recv error: {e}")
            self.close()
            return ""

    def send_line(self, line: str) -> None:
        if not self.sock:
            raise RuntimeError("Not connected")
        self.sock.sendall((line + "\n").encode("utf-8"))

    def login(self, username: str, password: str) -> None:
        banner = ""
        start = time.time()
        while time.time() - start < 2.0:
            banner += self.recv_some()
        if banner.strip():
            self.logger.log("[mux] banner received")

        self.logger.log(f"[mux] logging in as {username}")
        self.send_line(f"connect {username} {password}")

        resp = ""
        start = time.time()
        while time.time() - start < 3.0:
            resp += self.recv_some()

        if "Either that player does not exist" in resp:
            self.logger.log("[mux] login failed: bad username/password")
            raise RuntimeError("TinyMUX login failed")

        self.logger.log("[mux] login response received (ok)")

        self.send_line("who")
        who_resp = ""
        start = time.time()
        while time.time() - start < 2.0:
            who_resp += self.recv_some()
        if who_resp.strip():
            self.logger.log("[mux] WHO ok")

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None


class KeepAlive(threading.Thread):
    def __init__(self, mux: MuxClient, logger: TechLogger, interval_s: int = 20) -> None:
        super().__init__(daemon=True)
        self.mux = mux
        self.logger = logger
        self.interval_s = interval_s
        self.last_pong_ts: Optional[float] = None

    def run(self) -> None:
        while True:
            try:
                if self.mux.sock:
                    self.mux.send_line("+ping")
            except Exception as e:
                self.logger.log(f"[keepalive] send error: {e}")
            time.sleep(self.interval_s)


def write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)


NOESIS_PREFIX_RE = re.compile(r"^\s*NOESIS:?\s*(.*)$")


def parse_noesis_kv(line: str) -> Optional[Dict[str, str]]:
    m = NOESIS_PREFIX_RE.match(line)
    if not m:
        return None
    payload = m.group(1).strip()
    if not payload:
        return None
    parts = [p for p in payload.split("|") if p]
    kv: Dict[str, str] = {}
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        kv[k.strip()] = v.strip()
    return kv if kv else None


def main() -> int:
    cfg_path = Path(os.environ.get("NOESIS_BRIDGE_CONFIG", "config.yaml")).resolve()
    cfg = load_config(cfg_path)

    run_id = make_run_id()
    started_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out_base = cfg.out_dir
    meta_dir = out_base / cfg.meta_subdir
    logs_dir = out_base / cfg.logs_subdir
    meta_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = TechLogger(logs_dir, level=cfg.log_level)
    logger.log(f"[bridge] starting run_id={run_id} config={cfg_path}")
    logger.log(f"[bridge] mode={cfg.mode_name}")

    meta = {
        "run_id": run_id,
        "started_at_utc": started_at,
        "host": cfg.host,
        "port": cfg.port,
        "pid": os.getpid(),
        "bridge_version": "0.5-keepalive-hb",
        "auth_user": cfg.username,
    }
    meta_path = meta_dir / f"run-{run_id}.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.log(f"[bridge] wrote run meta: {meta_path}")

    mux = MuxClient(cfg.host, cfg.port, logger)
    writer = EventWriter(out_dir=cfg.out_dir)

    seq = 0
    buffer = ""
    last_event_rx_ts = time.time()
    last_event_write_ts = 0.0
    events_written = 0

    hb_path = cfg.out_dir / "bridge.heartbeat.json"
    last_hb_emit = 0.0

    def reconnect() -> None:
        nonlocal buffer
        logger.log("[mux] reconnecting...")
        mux.close()
        time.sleep(1.0)
        mux.connect()
        mux.login(cfg.username, cfg.password)
        buffer = ""
        logger.log("[mux] reconnected + logged in")

    try:
        mux.connect()
        mux.login(cfg.username, cfg.password)
        logger.log("[bridge] READY (connected + logged in)")

        KeepAlive(mux, logger, interval_s=20).start()

        if cfg.mode_name == "dry_run":
            logger.log("[bridge] DRY RUN: telemetry ignored.")
        else:
            logger.log("[bridge] RECORD: telemetry ingest active (NOESIS → JSONL).")

        while True:
            if not mux.sock:
                reconnect()

            chunk = mux.recv_some()
            if chunk:
                last_event_rx_ts = time.time()
                buffer += chunk.replace("\r", "\n")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    if cfg.mode_name != "record":
                        continue

                    kv = parse_noesis_kv(line)
                    if kv is None:
                        continue

                    t = kv.get("t")
                    if not t:
                        continue

                    if t == "SAY":
                        actor = kv.get("actor")
                        loc = kv.get("loc")
                        raw = kv.get("raw", "")
                        verb = kv.get("verb")

                        if not actor or not loc:
                            logger.log(f"[telemetry] drop SAY missing actor/loc line={line}")
                            continue

                        seq += 1
                        content: Dict[str, Any] = {"raw": raw}
                        if verb:
                            content["verb"] = verb

                        event = {
                            "ts_utc": iso_utc_now_ms(),
                            "run_id": run_id,
                            "seq": seq,
                            "type": "SAY",
                            "actor": {"dbref": actor, "name": actor},
                            "location": {"dbref": loc, "name": loc},
                            "content": content,
                            "perception": {"perceived_by": [actor], "occluded_for": []},
                        }

                        path = writer.write_event(event)
                        events_written += 1
                        last_event_write_ts = time.time()
                        logger.log(f"[event] wrote SAY seq={seq} actor={actor} loc={loc} file={path}")
                        continue

                    if t == "MOVE":
                        actor = kv.get("actor")
                        frm = kv.get("from")
                        to = kv.get("to")
                        raw = kv.get("raw", "")

                        if not actor or not frm or not to:
                            logger.log(f"[telemetry] drop MOVE missing actor/from/to line={line}")
                            continue

                        seq += 1
                        event = {
                            "ts_utc": iso_utc_now_ms(),
                            "run_id": run_id,
                            "seq": seq,
                            "type": "MOVE",
                            "actor": {"dbref": actor, "name": actor},
                            "location": {"dbref": to, "name": to},
                            "content": {"from": frm, "to": to, "raw": raw},
                            "perception": {"perceived_by": [actor], "occluded_for": []},
                        }

                        path = writer.write_event(event)
                        events_written += 1
                        last_event_write_ts = time.time()
                        logger.log(f"[event] wrote MOVE seq={seq} actor={actor} from={frm} to={to} file={path}")
                        continue

            # heartbeat co 30s (stabilnie, bez spamowania co pętlę)
            now = time.time()
            if now - last_hb_emit >= 30.0:
                last_hb_emit = now
                hb = {
                    "ts": iso_utc_now_ms(),
                    "pid": os.getpid(),
                    "mux_connected": bool(mux.sock),
                    "last_event_rx_ts": last_event_rx_ts,
                    "last_event_write_ts": last_event_write_ts,
                    "events_written": events_written,
                    "run_id": run_id,
                }
                write_json_atomic(hb_path, hb)
                logger.log(f"[alive] {hb}")

            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.log("[bridge] stopping (KeyboardInterrupt)")
    except Exception as e:
        logger.log(f"[bridge] fatal: {e}")
        return 1
    finally:
        mux.close()
        logger.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
