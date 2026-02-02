# LAYERS-ATTRS.md — Attribute Contract (v1)

This document defines the **attribute-level contract** for reality layers in TinyMUX.
Rules and semantics are in `LAYERS.md`. Numeric bit assignments live in `BITMASKS.md`.

---

## 1) Goals

- Make layer logic **predictable** and **debuggable**
- Avoid mixing *travel (LOC)* with *perception (SEE)* and *interaction (TOUCH)*
- Keep stealth/detection **separate** from layers
- Enable clean, temporary “buff” overrides (e.g., Auspex adds SEE bits)

---

## 2) Attribute naming conventions

Prefix:
- `A_` for attributes stored on objects (players, rooms, exits, items)

Bitmask-like values are stored as integers (decimal string), unless your MUX prefers hex.
(Recommended: store decimal; provide helper commands for viewing in hex.)

---

## 3) Core attributes (required)

### 3.1 Player (viewer) attributes

| Attribute | Type | Meaning | Required | Notes |
|---|---|---|:---:|---|
| `A_LAYER_LOC` | int (single-bit) | Current travel layer (exactly one bit) | ✅ | Must satisfy: popcount == 1 |
| `A_LAYER_SEE_BASE` | int (bitmask) | Baseline perception mask | ✅ | Must include LOC |
| `A_LAYER_TOUCH_BASE` | int (bitmask) | Baseline interaction mask | ✅ | Default equals LOC |

Computed (not stored, or stored for debugging only):
- `SEE = A_LAYER_SEE_BASE | A_LAYER_SEE_BONUS`
- `TOUCH = A_LAYER_TOUCH_BASE | A_LAYER_TOUCH_BONUS`

### 3.2 Entity attributes (rooms/objects/characters)

| Attribute | Type | Meaning | Required | Notes |
|---|---|---|:---:|---|
| `A_LAYERS` | int (bitmask) | Where this entity exists/renders | ✅ | Used by visibility and interaction rules |

---

## 4) Optional attributes (recommended)

### 4.1 Player bonus masks (buff-friendly)

| Attribute | Type | Meaning | Notes |
|---|---|---|---|
| `A_LAYER_SEE_BONUS` | int | Temporary additional perception bits | Usually 0; modified by powers |
| `A_LAYER_TOUCH_BONUS` | int | Temporary additional interaction bits | Keep rare; explicit powers only |

**Invariant enforcement:**
- `SEE` must always include `LOC` (even after buffs)
- If a buff ends, the bonus mask must be cleared

### 4.2 Room descriptions per layer (rendering)

Rooms may have per-layer “description sections”:

| Attribute | Type | Meaning |
|---|---|---|
| `A_DESC_MATERIAL` | text | Room description for MATERIAL |
| `A_DESC_UMBRA` | text | Room description for UMBRA |
| `A_DESC_SHADOWLANDS` | text | Room description for SHADOWLANDS |
| `A_DESC_DREAMING` | text | Room description for DREAMING |

If your MUX prefers a single attribute, use:
- `A_DESC_LAYER_<LAYERNAME>` pattern, or a structured block format.

### 4.3 Exit layer gating

| Attribute | Type | Meaning |
|---|---|---|
| `A_EXIT_LAYERS_ALLOWED` | int (bitmask) | In which LOC layers the exit is usable |

If absent, default policy:
- `A_EXIT_LAYERS_ALLOWED = MATERIAL` (or “same as source room LOC” if you have such logic)

---

## 5) Who owns the truth?

### 5.1 Authoritative sources (recommended)

- **Player** owns:
  - `A_LAYER_LOC`
  - `A_LAYER_SEE_BASE`
  - `A_LAYER_TOUCH_BASE`
  - bonuses (if buffs are implemented on the player)

- **Entity (room/object/exit)** owns:
  - `A_LAYERS`
  - `A_DESC_*` (rooms)
  - `A_EXIT_LAYERS_ALLOWED` (exits)

### 5.2 What code is allowed to change what?

**Only layer system commands** should mutate these:
- `A_LAYER_LOC`, `A_LAYER_SEE_*`, `A_LAYER_TOUCH_*`
- `A_LAYER_*_BONUS`

Builders/admin tools may set entity attributes:
- `A_LAYERS`, `A_DESC_*`, `A_EXIT_LAYERS_ALLOWED`

---

## 6) Derived values & helper macros (conceptual)

### 6.1 Derived masks

- `SEE(viewer) = A_LAYER_SEE_BASE | A_LAYER_SEE_BONUS`
- `TOUCH(viewer) = A_LAYER_TOUCH_BASE | A_LAYER_TOUCH_BONUS`

### 6.2 Validation checks (must exist somewhere)

- `popcount(A_LAYER_LOC) == 1`
- `(SEE(viewer) & A_LAYER_LOC) != 0`
- default policy: if `A_LAYER_TOUCH_BASE` is empty, set it to `A_LAYER_LOC`

> If you don’t have popcount, enforce single-bit by restricting LOC setters to known constants.

---

## 7) Debug attributes (optional but sanity-saving)

| Attribute | Type | Meaning |
|---|---|---|
| `A_LAYER_DEBUG` | text | last layer change reason / actor |
| `A_LAYER_LAST_CHANGE_TS` | text/int | timestamp of last LOC change |
| `A_LAYER_LAST_RUNID` | text | run/session correlation id |

---

## 8) Recommended defaults (bootstrap)

### Player default (most splats)
- `A_LAYER_LOC = MATERIAL`
- `A_LAYER_SEE_BASE = MATERIAL`
- `A_LAYER_TOUCH_BASE = MATERIAL`
- bonuses = 0

### Wraith default
- `A_LAYER_LOC = SHADOWLANDS`
- `A_LAYER_SEE_BASE = SHADOWLANDS | MATERIAL`
- `A_LAYER_TOUCH_BASE = SHADOWLANDS`

### Changeling default (choose a policy from LAYERS.md)
Option A:
- `A_LAYER_SEE_BASE = MATERIAL | DREAMING`
- `A_LAYER_TOUCH_BASE = MATERIAL`
Option B:
- `A_LAYER_SEE_BASE = MATERIAL | DREAMING`
- `A_LAYER_TOUCH_BASE = MATERIAL | DREAMING`

---

## 9) Stealth / detection (explicitly not layers)

Do not encode stealth via layers.
Use separate attributes like:

- `A_STEALTH_FLAGS` (bitmask)
- `A_STEALTH_TICKS_LEFT` (int)
- `A_DETECT_FLAGS` (bitmask) or skill checks

Layer perception buffs may expand `A_LAYER_SEE_BONUS`,
but “revealing hidden things” should still require a check.

---

## 10) Cross-reference

- Semantics & rules: `LAYERS.md`
- Bit assignments: `BITMASKS.md`
- Buff timing (Obfuscate/Auspex): your buff pack docs
