# MANIFEST.md — TinyMUX

> Repository manifest: what lives here, why it exists, how to run it, and where runtime artifacts land.
> Note: `out/` and other runtime files are generated — do not commit them.

---

## 0) Metadata

- **Manifest format:** `manifest-v1`
- **Repo / project:** TinyMUX
- **Last updated:** 2026-02-02
- **Owner:** TODO (e.g., Mandor / team)
- **Target environments:** dev (local), VPS (prod-ish), CI (if applicable)

---

## 1) Purpose

TinyMUX is a project where:
- the MUX core serves the “world” (commands, locations, characters, events),
- side services (e.g., `noesis-bridge`) handle telemetry / integrations / bridges (e.g., to the render/AI layer),
- `out/` collects run artifacts (meta, logs, JSONL, etc.) for debugging and replay.

---

## 2) Directory layout (contract)

> The structure below is a **contract**: if reality differs, update this section (not the other way around).

| Path | Type | Contents | Commit? |
|---|---|---|---|
| `services/` | dir | Companion services (bridge, ingest, emit, etc.) | ✅ |
| `services/noesis-bridge/` | service | Bridge: TinyMUX → telemetry (record/replay) | ✅ |
| `services/noesis-bridge/src/` | code | Bridge source code | ✅ |
| `services/noesis-bridge/config.yaml` | config | Bridge configuration (ports, mode, output) | ✅ *(no secrets)* |
| `out/` | runtime | Run artifacts (meta, logs, JSONL) | ❌ |
| `out/meta/` | runtime | Run metadata: `run-<...>.json` | ❌ |
| `docs/` | dir | Operational docs + cheat sheets | ✅ |
| `scripts/` | dir | Helper scripts (devops/bootstrap) | ✅ |
| `.env` / `*.secrets.*` | secrets | Secrets and tokens | ❌ |

### 2.1 Suggested tree (short)

- `services/`
  - `noesis-bridge/`
    - `src/`
    - `config.yaml`
- `docs/`
- `scripts/`
- `out/` *(generated)*
  - `meta/`
  - `logs/` *(optional)*
  - `telemetry/` *(optional)*

---

## 3) Components

### 3.1 TinyMUX (MUX server)
- **Role:** “world runtime” (game/simulation core + commands).
- **Input (typical):** TCP on localhost (e.g., `127.0.0.1:2860`).
- **Dependencies:** TODO (e.g., systemd, docker, build toolchain).
- **Artifacts:** TODO (server logs, dumps, DB files — if applicable).

> NOTE: `127.0.0.1:2860` comes from current bridge startup logs — treat it as a default, but it should ultimately live in config.

### 3.2 Noesis Bridge (`services/noesis-bridge`)
- **Role:** Connects to TinyMUX and produces telemetry (e.g., JSONL) + run metadata.
- **Modes:** `record` (capture), `replay` (playback) *(names depend on implementation)*.
- **Input:** MUX connection, default `127.0.0.1:2860` (configurable).
- **Output (artifacts):**
  - `out/meta/run-<ISO8601>Z-<shortid>.json` — run metadata
  - `out/.../*.jsonl` — event stream (if enabled)
- **Configuration:** `services/noesis-bridge/config.yaml`

---

## 4) Configuration

### 4.1 Config files

- `services/noesis-bridge/config.yaml`
  - **Holds:** mode (`record/replay`), MUX address, output paths, log levels, etc.
  - **Rule:** no secrets in YAML (tokens go into `.env` or a secrets manager).

### 4.2 Environment variables (contract)

| Variable | Meaning | Example | Required |
|---|---|---:|:---:|
| `OPENAI_API_KEY` | (If applicable) key for AI integrations | `voc-...` / `sk-...` | ⛔/✅ |

> If this repo uses Vocareum: the client base URL is typically `https://openai.vocareum.com/v1` and the key looks like `voc-...`. Keep it out of git.

---

## 5) Runtime artifacts (`out/`)

`out/` is generated at runtime and must stay out of version control.

Suggested subfolders:
- `out/meta/` — per-run metadata JSON
- `out/logs/` — service logs (optional)
- `out/telemetry/` — JSONL / event dumps (optional)

Naming convention (suggested):
- `run-YYYY-MM-DDTHH:MM:SSZ-<shortid>.json`

---

## 6) Operational quickstart (minimal)

> Keep this section “copy-paste friendly”.

### 6.1 Run Noesis Bridge (example)

From within `services/noesis-bridge/`:

- Ensure a virtualenv is active (if used).
- Run the bridge:

`python src/bridge.py`

Expected log highlights (example):
- `starting ... config=services/noesis-bridge/config.yaml`
- `mode=record`
- `connecting to 127.0.0.1:2860`
- `wrote run meta: out/meta/run-....json`

### 6.2 Where to look when debugging

- Connection issues: check MUX host/port in `config.yaml`.
- Output issues: verify `out/` exists and is writable.
- “Nothing happens”: confirm MUX is running and reachable on localhost.

---

## 7) Versioning & contribution rules

- Never commit secrets (`.env`, tokens, credentials).
- Keep runtime artifacts out of git (`out/`, logs, dumps).
- Update this manifest when:
  - directory layout changes,
  - new services are added,
  - artifact locations/names change.

---

## 8) TODO (intentionally explicit)

- [ ] Fill in owner/team name
- [ ] Confirm canonical MUX port + document where it’s configured
- [ ] Document the exact telemetry formats (JSONL schema / event types)
- [ ] Add CI notes (if any)
