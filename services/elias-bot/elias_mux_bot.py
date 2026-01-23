#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import socket
import logging
from typing import Optional, Tuple

from openai import OpenAI  # openai-python (Responses API)

LOG = logging.getLogger("elias-bot")

# --- TinyMUX / telnet helpers -------------------------------------------------

IAC = 255  # telnet "Interpret As Command"


def strip_telnet_iac(data: bytes) -> bytes:
    """
    Minimal telnet IAC stripping:
    - Removes IAC negotiations (IAC <cmd> <opt>)
    - Removes IAC SB ... IAC SE subnegotiations
    Leaves plain text intact.
    """
    out = bytearray()
    i = 0
    n = len(data)

    while i < n:
        b = data[i]
        if b != IAC:
            out.append(b)
            i += 1
            continue

        # b == IAC
        if i + 1 >= n:
            break
        cmd = data[i + 1]

        # IAC IAC => literal 255
        if cmd == IAC:
            out.append(IAC)
            i += 2
            continue

        # Subnegotiation: IAC SB ... IAC SE
        if cmd == 250:  # SB
            i += 2
            while i < n:
                if data[i] == IAC and i + 1 < n and data[i + 1] == 240:  # SE
                    i += 2
                    break
                i += 1
            continue

        # Negotiation: IAC WILL/WONT/DO/DONT <opt>
        if cmd in (251, 252, 253, 254):
            i += 3  # skip cmd + opt
            continue

        # Other commands: skip IAC + cmd
        i += 2

    return bytes(out)


def smart_decode(data: bytes) -> str:
    """
    Prefer UTF-8, but if it looks like mojibake hell, fall back to latin-1.
    """
    if not data:
        return ""
    cleaned = strip_telnet_iac(data)

    # First try utf-8 (replace, but we measure damage)
    s_utf8 = cleaned.decode("utf-8", errors="replace")
    replacement_ratio = s_utf8.count("\ufffd") / max(1, len(s_utf8))

    if replacement_ratio > 0.02:
        return cleaned.decode("latin-1", errors="replace")
    return s_utf8


def now_ms() -> int:
    return int(time.time() * 1000)


# --- OpenAI -------------------------------------------------------------------

def build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing in environment")
    return OpenAI(api_key=api_key)


def elias_reply(client: OpenAI, model: str, prompt: str) -> str:
    """
    Generate a concise, in-character reply.
    Uses Responses API (recommended).
    """
    system = (
        "Jesteś Eliasem – always-on NPC w TinyMUX. "
        "Odpowiadasz krótko, po polsku, bez emoji-spamu. "
        "Masz lekko mroczny, gotycko-punkowy vibe, ale nie przesadzasz. "
        "Jeśli pytanie jest techniczne (TinyMUX, Noesis, boty), odpowiadasz konkretnie."
    )
    # Keep it simple: system + user prompt
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    text = getattr(resp, "output_text", None)
    if not text:
        # compatible fallback if SDK changes shape
        try:
            text = resp.output[0].content[0].text  # type: ignore
        except Exception:
            text = "…cisza w eterze. Spróbuj jeszcze raz."
    return text.strip()

def parse_say(line: str) -> Optional[Tuple[str, str]]:
    for pat in SAY_PATTERNS:
        m = pat.match(line.strip())
        if m:
            return m.group("who").strip(), (m.group("msg") or "").strip()
    return None


# --- Main bot -----------------------------------------------------------------
# Stara wersja:
# PAGE_PATTERNS = [
#     # Typical MUX-ish: "X pages: message"
#     re.compile(r"^(?P<who>.+?)\s+pages:\s*(?P<msg>.*)$", re.IGNORECASE),
#     # Sometimes: "From afar, X pages: msg"
#     re.compile(r"^From afar,\s+(?P<who>.+?)\s+pages:\s*(?P<msg>.*)$", re.IGNORECASE),
#     # Sometimes: "You sense that X is looking for you. msg"
#     re.compile(r"^You sense that\s+(?P<who>.+?)\s+is looking for you\.?\s*(?P<msg>.*)$", re.IGNORECASE),
# ]

PAGE_PATTERNS = [
    re.compile(r"^(?P<who>.+?)\s+pages:\s*(?P<msg>.*)$", re.IGNORECASE),
    re.compile(r"^From afar,\s+(?P<who>.+?)\s+pages:\s*(?P<msg>.*)$", re.IGNORECASE),
    re.compile(r"^You sense that\s+(?P<who>.+?)\s+is looking for you\.?\s*(?P<msg>.*)$", re.IGNORECASE),
]

SAY_PATTERNS = [
    # PL: Wizard mówi: „Elias, jaka dzisiaj jest noc?”
    re.compile(r"^(?P<who>.+?)\s+mówi:\s*[„\"](?P<msg>.*?)[”\"]\s*$", re.IGNORECASE),
    # EN: Wizard says, "Elias, what night is it?"
    re.compile(r"^(?P<who>.+?)\s+says,?\s*[\"“](?P<msg>.*?)[\"”]\s*$", re.IGNORECASE),
]

# wołanie Eliasa na początku wypowiedzi
CALL_ELIAS = re.compile(r"^\s*(?:@?Elias\b[:,]?\s*)(?P<rest>.*)$", re.IGNORECASE)


class EliasMuxBot:
    def __init__(self):
        self.mux_host = os.environ.get("MUX_HOST", "127.0.0.1")
        self.mux_port = int(os.environ.get("MUX_PORT", "2860"))
        self.mux_user = os.environ.get("MUX_USER", "Elias")
        self.mux_pass = os.environ.get("MUX_PASS", "")
        self.mux_room = os.environ.get("MUX_ROOM", "Kolorowa Krowa")
        self.model = os.environ.get("MODEL", "gpt-5-mini")

        self.sock: Optional[socket.socket] = None
        self.buf = bytearray()
        self.last_activity_ms = now_ms()

        self.oa = build_client()

    def connect(self):
        LOG.info("Connecting to %s:%s", self.mux_host, self.mux_port)
        s = socket.create_connection((self.mux_host, self.mux_port), timeout=15)
        s.settimeout(0.5)
        self.sock = s
        self.buf.clear()
        self.last_activity_ms = now_ms()

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def handle_and_reply(self, who: str, msg: str):
        LOG.info("Ask from %s: %s", who, msg)

        try:
            answer = elias_reply(self.oa, self.model, msg)
        except Exception as e:
            LOG.exception("OpenAI error")
            answer = f"Coś chrupnęło w eterze: {e}"

        answer = " ".join(answer.splitlines()).strip()
        if len(answer) > 800:
            answer = answer[:780].rstrip() + "…"

        self.send_line(f"page {who}={answer}")

    def send_line(self, line: str):
        if not self.sock:
            return
        # Ensure newline and utf-8
        data = (line.rstrip("\n") + "\n").encode("utf-8", errors="replace")
        self.sock.sendall(data)
        LOG.debug(">> %s", line)

    def recv_bytes(self) -> bytes:
        if not self.sock:
            return b""
        try:
            chunk = self.sock.recv(4096)
            return chunk
        except socket.timeout:
            return b""
        except Exception as e:
            raise ConnectionError(str(e))

    def read_lines(self) -> list[str]:
        """
        Non-blocking-ish read; returns decoded lines.
        """
        data = self.recv_bytes()
        if data:
            self.buf.extend(data)
            self.last_activity_ms = now_ms()

        lines: list[str] = []
        while b"\n" in self.buf:
            raw_line, _, rest = self.buf.partition(b"\n")
            self.buf = bytearray(rest)
            line = smart_decode(raw_line).rstrip("\r")
            if line.strip():
                lines.append(line)
        return lines

    def login_and_settle(self):
        """
        Connect + login + attempt to move to room.
        """
        if not self.mux_pass:
            raise RuntimeError("MUX_PASS missing in environment")

        # Wait a moment for banner/MOTD to flush
        t0 = time.time()
        while time.time() - t0 < 2.0:
            _ = self.read_lines()
            time.sleep(0.05)

        # Login
        self.send_line(f"connect {self.mux_user} {self.mux_pass}")

        # Let server respond
        t1 = time.time()
        while time.time() - t1 < 2.0:
            for ln in self.read_lines():
                LOG.info("<< %s", ln)
            time.sleep(0.05)

        # Try a few common ways to get into the target room (safe-ish, one-time burst)
        # One of these usually works depending on perms / server config.
        movers = [
            f"@tel me={self.mux_room}",
            f"@teleport me={self.mux_room}",
            f"@move me={self.mux_room}",
            f"@join {self.mux_room}",
            f"goto {self.mux_room}",
            f"look",
        ]
        for cmd in movers:
            self.send_line(cmd)
            time.sleep(0.2)

        # Final look to confirm presence (at least gives you logs)
        self.send_line("look")

    def parse_page(self, line: str) -> Optional[Tuple[str, str]]:
        for pat in PAGE_PATTERNS:
            m = pat.match(line.strip())
            if m:
                who = m.group("who").strip()
                msg = (m.group("msg") or "").strip()
                # Strip common noise like trailing quotes
                msg = msg.strip("\"'")
                return who, msg
        return None

    def loop(self):
        LOG.info("Bot loop start. model=%s room=%s", self.model, self.mux_room)
        while True:
            # keepalive: if idle, send something harmless
            if now_ms() - self.last_activity_ms > 60_000:
                self.send_line("@@")  # many MUX servers treat as noop/echo-suppress; if not, it's still harmless text
                self.last_activity_ms = now_ms()

            for line in self.read_lines():
                # 1) PAGE (zawsze odpowiadamy)
                parsed = self.parse_page(line)
                if parsed:
                    who, msg = parsed
                    msg = msg.strip()

                    # healthcheck bez AI (zero kosztu)
                    if msg == "@@healthcheck":
                        self.send_line(f"page {who}=@@ok {int(time.time())}")
                        continue

                    # normalna odpowiedź przez AI
                    self.handle_and_reply(who, msg)
                    continue

                # 2) SAY w pokoju (odpowiadamy TYLKO gdy ktoś woła Eliasa)
                said = parse_say(line)
                if not said:
                    continue

                who, msg = said
                m = CALL_ELIAS.match(msg)
                if not m:
                    continue  # ktoś mówi, ale nie do Eliasa

                prompt = (m.group("rest") or "").strip()
                if not prompt:
                    continue

                # odpowiadamy prywatnie, żeby nie spamować lokacji
                self.handle_and_reply(who, prompt)

                LOG.info("Page from %s: %s", who, msg)

                # Avoid weird loops / empty
                if not msg:
                    continue
                msg = msg.strip()

                if msg == "@@healthcheck":
                    self.send_line(f"page {who}=@@ok {int(time.time())}")
                    continue

                try:
                    answer = elias_reply(self.oa, self.model, msg)
                except Exception as e:
                    LOG.exception("OpenAI error")
                    answer = f"Coś chrupnęło w eterze: {e}"

                # TinyMUX page back
                # Keep it single line, MUX-friendly
                answer = " ".join(answer.splitlines()).strip()
                if len(answer) > 800:
                    answer = answer[:780].rstrip() + "…"

                self.send_line(f"page {who}={answer}")

            time.sleep(0.05)


def main():
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    backoff = 1.0
    while True:
        bot = EliasMuxBot()
        try:
            bot.connect()
            bot.login_and_settle()
            backoff = 1.0
            bot.loop()
        except Exception as e:
            LOG.warning("Disconnected / crash: %s", e)
            bot.close()
            time.sleep(backoff)
            backoff = min(backoff * 1.7, 30.0)


if __name__ == "__main__":
    main()
