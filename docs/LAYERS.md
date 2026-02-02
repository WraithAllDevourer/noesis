# LAYERS.md — Reality Layers (v1)

This document defines **reality layers** in TinyMUX: what they mean, how they render, and how interaction rules work.
Numeric/hex bit assignments live in **BITMASKS.md** (or your existing bitmask cheat-sheets). This file defines the **rules**.

---

## 1) Mental model

A **layer** is a *reality filter* applied to the same physical room.

We keep three separate concepts:

- **LOC** — where you *are* (exactly **one** travel layer at a time)
- **SEE** — what you can *perceive* (can include multiple layers)
- **TOUCH** — what you can *interact with* (defaults to LOC; expanded only by explicit powers)

> Stealth (e.g., Obfuscate) is **not** a layer. It is a visibility modifier *inside a layer*.

---

## 2) Canonical layer set (v1)

These are the only layers guaranteed by this spec:

| Layer | Meaning | Travel (LOC)? | Notes |
|---|---|:---:|---|
| MATERIAL | Physical world / “Skinlands” | ✅ | Default for most beings |
| UMBRA | Spirit world | ✅ | Includes Penumbra/Near Umbra as v1 “bucket” |
| SHADOWLANDS | Dead world | ✅ | Near the living world, but “across the Shroud” |
| DREAMING | Chimerical / Dreaming | ✅ | Changeling-style dream layer |

**Stability rule:** these names are stable. If you add new layers later, do **not** repurpose existing bits.

---

## 3) Data contract (minimum)

Every entity that should appear in a specific layer must have a **layer mask**:

- `LAYERS` — bitmask describing where the entity exists / renders

Every player character (or viewer) must have:

- `LOC` — a **single-bit** travel layer (exactly one layer)
- `SEE` — bitmask; must always include `LOC`
- `TOUCH` — bitmask; defaults to `LOC`

### 3.1 Invariants (must always hold)

1. `LOC` is a single bit: `popcount(LOC) == 1`
2. `SEE` includes `LOC`: `(SEE & LOC) != 0`
3. Default interaction: `TOUCH == LOC` (unless explicitly overridden)

---

## 4) Visibility and interaction rules

### R1. Visibility
An entity is visible if the viewer can perceive at least one of the entity’s layers:

- **Visible(viewer, entity)** iff `(entity.LAYERS & viewer.SEE) != 0`

### R2. Interaction
By default you interact only within your LOC:

- default `viewer.TOUCH = viewer.LOC`

An interaction is allowed if:

- **Touchable(viewer, entity)** iff `(entity.LAYERS & viewer.TOUCH) != 0`

Cross-layer interaction is an explicit exception enabled by a specific power (expand `TOUCH` temporarily, or use special verbs).

---

## 5) Room rendering rules (`look`)

Rendering must be deterministic and readable.

### R3. Rendering order
1) Render the **LOC** description first (the “primary reality”).
2) Render additional layer sections for remaining bits in `SEE`, in a fixed order.

Recommended order (v1):
- `MATERIAL → DREAMING → SHADOWLANDS → UMBRA`

3) List contents filtered by **R1 Visibility**.

### R4. Multi-layer entities (dedup)
If an entity exists in multiple visible layers, it must be listed **once**:
- Prefer listing it under the highest-priority visible layer (using the render order above).
- Optionally annotate (e.g., `[...]`) if you need clarity.

---

## 6) Movement and exits

Exits have their own layer rules.

### R5. Exit gating
Each exit has `EXIT.LAYERS_ALLOWED` (bitmask).

The exit can be used iff:
- `(EXIT.LAYERS_ALLOWED & viewer.LOC) != 0`

### Layer shifts (changing LOC)
“World travel” powers change LOC (and therefore SEE/TOUCH invariants must be restored):
- Step Sideways: `LOC = UMBRA`
- Crossing the Shroud: `LOC = SHADOWLANDS`
- Entering the Dreaming: `LOC = DREAMING`

After any LOC change:
- Ensure `SEE |= LOC`
- If no explicit exception is active, set `TOUCH = LOC`

---

## 7) Stealth and detection (separate from layers)

Stealth is not solved by layers. It’s solved by **visibility modifiers** within a layer.

### Example policy
- Hidden entities do not appear in room listings even if `(LAYERS & SEE) != 0`.
- Detection powers do two distinct things:
  1) expand **SEE** (e.g., “can perceive SHADOWLANDS”)
  2) run a contest/check to reveal hidden entities in the relevant layer

> Keep these concerns separate, or you’ll end up with “I can’t see you because I’m in the wrong metaphysical layer” when the real problem is “you’re hidden”.

---

## 8) Default splat profiles (recommended)

These are defaults, not hard laws. They give sane behavior out of the box.

### Vampire (VtM)
- `LOC = MATERIAL`
- `SEE = MATERIAL`
- Optional: powers may add `SHADOWLANDS` to `SEE`
- Stealth (Obfuscate) is a modifier inside MATERIAL

### Werewolf (WtA)
- Default `LOC = MATERIAL`
- After Step Sideways: `LOC = UMBRA`
- `SEE` normally equals `LOC` (optionally also include “echo” perception of MATERIAL)
- `TOUCH` normally equals `LOC`

### Mage (MtA)
- Default `LOC = MATERIAL`
- Powers may add layers to `SEE` (and rarely to `TOUCH`)
- Avoid “always-on cross-layer TOUCH” unless you want mages to become accidental admins

### Wraith (WtO)
- `LOC = SHADOWLANDS`
- `SEE = SHADOWLANDS | MATERIAL` (Skinlands as a “negative/echo” perception)
- `TOUCH = SHADOWLANDS`
- Influence on MATERIAL is via explicit actions/powers (special verbs), not general TOUCH

### Changeling (CtD)
Choose one world policy and keep it consistent:

**Option A (simple):**
- Default `LOC = MATERIAL`
- `SEE = MATERIAL | DREAMING` (chimerical overlay)
- `TOUCH = MATERIAL` unless `LOC = DREAMING`

**Option B (more CtD-native):**
- Default `LOC = MATERIAL`
- `SEE = MATERIAL | DREAMING`
- `TOUCH = MATERIAL | DREAMING` (changelings can interact with chimerical entities)

---

## 9) Extending layers (future-proofing)

If you add new layers (e.g., ASTRAL/HORIZON/DEEP_UMBRA):
- allocate a new bit that has never been used before
- add it to this document’s canonical set
- update render order and default profiles
- do not rename or repurpose existing layers/bits

---

## 10) Worked examples

### Example 1 — Vampire with “see the dead” sense
- `LOC = MATERIAL`
- `SEE = MATERIAL | SHADOWLANDS`
- `TOUCH = MATERIAL`

Result:
- Sees SHADOWLANDS entities, but cannot interact with them unless a specific power grants it.

### Example 2 — Werewolf steps sideways
Before:
- `LOC = MATERIAL`, `SEE = MATERIAL`, `TOUCH = MATERIAL`
After:
- `LOC = UMBRA`
- must ensure: `SEE` includes `UMBRA`
- default: `TOUCH = UMBRA`

Result:
- The world description and contents now come from UMBRA.

### Example 3 — Wraith haunting the living
- Wraith has `LOC = SHADOWLANDS`
- Wraith sees MATERIAL as overlay (`SEE |= MATERIAL`)
- Wraith does not get general TOUCH on MATERIAL
- “haunt/whisper” actions are explicit verbs that affect MATERIAL by rule exceptions (not by changing TOUCH)

---

## 11) Cross-reference

- Bit assignments: **BITMASKS.md**
- Stealth timers / buffs (Obfuscate, Auspex, etc.): relevant service/command docs
- Exit templates: see `MANIFEST.md` / your command packs documentation
