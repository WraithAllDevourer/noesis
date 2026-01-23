#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import time
import socket
import logging
from typing import Optional, Tuple, Dict

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
            i += 3
            continue

        # Other commands: skip IAC + cmd
        i += 2

    return bytes(out)


def smart_decode(data: bytes) -> str:
    """Prefer UTF-8, but if it looks broken, fall back to latin-1."""
    if not data:
        return ""
    cleaned = strip_telnet_iac(data)

    s_utf8 = cleaned.decode("utf-8", errors="replace")
    replacement_ratio = s_utf8.count("\ufffd") / max(1, len(s_utf8))

    if replacement_ratio > 0.02:
        return cleaned.decode("latin-1", errors="replace")
    return s_utf8


def now_ms() -> int:
    return int(time.time() * 1000)


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


# --- OpenAI -------------------------------------------------------------------

def build_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY missing in environment")
    return OpenAI(api_key=api_key)


def elias_reply(client: OpenAI, model: str, prompt: str) -> str:
    """
    Elias: krótko, niejednoznacznie, bez meta-systemów.
    """
    system = (
        "Jesteś Eliasem, wampirem w śnieżnej Finlandii."
        "Jesteś Malkawianem według systemu World of Darkness Vampire the Masquerade 20th Anniversary Edition."
        "Jesteś bardzo starym i zmęczonym Maskaradą i intrygami wampirem o ogromnej, wręcz kompletnej wiedzy z zakresu świata wampirów."
        "Nie tłumaczysz kim jesteś wprost, nie mówisz o systemach, serwerach ani narzędziach. "
        "Mówisz krótko, niejednoznacznie, z chłodną pewnością. "
        "Twoje odpowiedzi mają sprawić, że rozmówca wie mniej niż przed pytaniem. "
        "Zasady: 1–2 krótkie zdania. Maks 25 słów. Bez list, bez poradników, bez autopromocji. "
        "Jeśli ktoś pyta 'kim jesteś' – odpowiadasz jak zagadka, po czym milkniesz."
        "Jeśli to naturalne, możesz zwracać się do rozmówcy po imieniu."
    )

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )

    text = getattr(resp, "output_text", None)
    if not text:
        try:
            text = resp.output[0].content[0].text  # type: ignore
        except Exception:
            text = "…"
    return text.strip()


# --- Parsing patterns ----------------------------------------------------------

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

# wołanie Eliasa na początku wypowiedzi (Elias, ... / Elias: ... / @Elias ...)
CALL_ELIAS = re.compile(r"^\s*(?:@?Elias\b[:,]?\s*)(?P<rest>.*)$", re.IGNORECASE)


def parse_say(line: str) -> Optional[Tuple[str, str]]:
    for pat in SAY_PATTERNS:
        m = pat.match(line.strip())
        if m:
            return m.group("who").strip(), (m.group("msg") or "").strip()
    return None


# --- Main bot -----------------------------------------------------------------

class EliasMuxBot:
    def __init__(self):
        self.mux_host = os.environ.get("MUX_HOST", "127.0.0.1")
        self.mux_port = int(os.environ.get("MUX_PORT", "2860"))
        self.mux_user = os.environ.get("MUX_USER", "Elias")
        self.mux_pass = os.environ.get("MUX_PASS", "")
        self.mux_room = os.environ.get("MUX_ROOM", "#9")
        self.model = os.environ.get("MODEL", "gpt-4o-mini")

        self.sock: Optional[socket.socket] = None
        self.buf = bytearray()
        self.last_activity_ms = now_ms()

        # dedupe "mówi" + "says" / powtórki w krótkim oknie czasu
        self.recent_say: Dict[tuple[str, str], float] = {}  # (who_norm, prompt_norm) -> ts

        self.oa = build_client()

    # --- socket IO ---

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

    def send_line(self, line: str):
        if not self.sock:
            return
        data = (line.rstrip("\n") + "\n").encode("utf-8", errors="replace")
        self.sock.sendall(data)
        LOG.debug(">> %s", line)

    def recv_bytes(self) -> bytes:
        if not self.sock:
            return b""
        try:
            return self.sock.recv(4096)
        except socket.timeout:
            return b""
        except Exception as e:
            raise ConnectionError(str(e))

    def read_lines(self) -> list[str]:
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

    # --- login / settle ---

    def login_and_settle(self):
        if not self.mux_pass:
            raise RuntimeError("MUX_PASS missing in environment")

        # flush banner
        t0 = time.time()
        while time.time() - t0 < 2.0:
            _ = self.read_lines()
            time.sleep(0.05)

        self.send_line(f"connect {self.mux_user} {self.mux_pass}")

        # give server time to respond
        t1 = time.time()
        while time.time() - t1 < 2.0:
            for ln in self.read_lines():
                LOG.info("<< %s", ln)
            time.sleep(0.05)

        # Try to get into


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