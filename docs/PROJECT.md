# PROJECT.md — TinyMUX

This document explains what this repository is, how the pieces fit together, and how to work on it safely.
For directory-level details and artifact locations, see `MANIFEST.md`.

---

## 1) What TinyMUX is

TinyMUX is a MUX-based “world runtime” plus a set of companion services that:
- run the world (commands, locations, characters, events),
- emit telemetry about what happens,
- optionally replay captured sessions,
- feed downstream systems (e.g., perception enrichment, RAG, and a render/AI layer).

**Design stance (important):**
- The “world” should remain authoritative and simple.
- AI/RAG sits **after** telemetry/perception, in the **render layer** (e.g., Discord/AI), not inside the MUX world logic.

---

## 2) High-level architecture

### 2.1 Components

- **TinyMUX (core server)**
  - Authoritative runtime.
  - Exposes a TCP interface (commonly on localhost, port configured).

- **Noesis Bridge** (`services/noesis-bridge`)
  - Connects to TinyMUX.
  - Captures and/or replays events.
  - Writes run metadata and telemetry artifacts to `out/`.

- **Downstream pipeline (conceptual)**
  - **Telemetry ingest → JSONL** (from bridge artifacts or live stream)
  - **Perception enrichment** (optional stage; “make telemetry perception-aware”)
  - **RAG** (attached after telemetry + perception filter, in render/AI layer)
  - **Render/AI layer** (Discord/UI/etc.) consumes enriched events and generates outputs

> The exact pipeline may be implemented as separate services; this repo documents the contract and the current parts.

### 2.2 Data flow (simplified)

TinyMUX → (TCP) → Noesis Bridge → `out/` artifacts (meta + JSONL) → ingest → (optional enrichment) → RAG → render

---

## 3) Repository layout

A short summary lives here; the authoritative layout contract is in `MANIFEST.md`.

- `services/` — companion services
  - `noesis-bridge/` — bridge service (record/replay)
- `docs/` — operational docs & cheat sheets
- `scripts/` — helper scripts
- `out/` — generated runtime artifacts (DO NOT COMMIT)

---

## 4) Runtime artifacts & “runs”

A **run** is a single execution session of a service (especially the bridge). Each run should produce:
- a **run_id** (timestamp + short id)
- **run metadata** JSON, e.g. `out/meta/run-<...>.json`
- optionally one or more **JSONL** files containing telemetry events

Artifacts are for:
- debugging (what happened?)
- replay (can we reproduce it?)
- feeding downstream tools (ingest/enrichment/RAG)

---

## 5) Configuration & secrets

### 5.1 Config files
- `services/noesis-bridge/config.yaml`
  - Holds: mode (`record` / `replay`), MUX address/port, output paths, log levels, etc.
  - Rule: **no secrets** in YAML.

### 5.2 Environment variables
Secrets live in `.env` (or a secrets manager), never in git.

Common examples (adjust to reality):
- `OPENAI_API_KEY` (only if AI integrations are enabled in your environment)
- `OPENAI_BASE_URL` (if using a proxy endpoint, e.g. Vocareum)

---

## 6) Quickstart (minimal)

> Keep this section copy-paste friendly. Replace TODOs with real commands as they stabilize.

### 6.1 Start TinyMUX
- Start the MUX server using your standard method (systemd / docker / local build).
- Ensure it listens on the host/port configured for the bridge (commonly localhost).

**TODO:** document the exact start command(s) for TinyMUX.

### 6.2 Run Noesis Bridge
From `services/noesis-bridge/`:

```bash
python src/bridge.py
