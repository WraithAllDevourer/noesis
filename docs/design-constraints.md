# Noesis — Design Constraints

This document defines explicit constraints that shape Noesis.
These constraints are intentional design decisions, not missing features.

They exist to protect the core ideas of the project over time.

---

## Purpose of constraints

Noesis is designed around a strict separation of:
- world truth,
- perception,
- narrative.

Any feature, extension, or integration that violates this separation
is considered out of scope.

Constraints exist to prevent architectural erosion.

---

## Core constraints

### 1. The world must exist independently of narration

Noesis will never:
- derive world state from narrative output,
- accept narrative descriptions as authoritative facts,
- allow narration (human or AI) to bypass world validation.

Narrative is always downstream from world state.

---

### 2. Perception is explicit, not implied

Noesis will never:
- assume shared visibility by default,
- rely on social conventions (“everyone here sees this”),
- encode perception rules inside narrative text.

If something is perceivable, it must be enforced by the system.

---

### 3. No omniscient participants

Noesis will never:
- provide full world state to any participant by default,
- assume that moderators, narrators, or AI have global knowledge,
- collapse partial perspectives into a single “true view”.

Omniscience is a special case and must be explicit.

---

### 4. Narrative has no write access to the world

Noesis will never:
- allow narrative systems to directly modify world state,
- treat narrative interpretation as an action,
- accept AI-generated outcomes as facts.

All state changes must pass through the World layer.

---

### 5. Ignorance is a supported state

Noesis will never:
- treat lack of information as an error,
- auto-fill missing perception with assumptions,
- guarantee that every action produces a complete explanation.

Not knowing is a valid outcome.

---

## Explicit non-goals

The following are explicitly not goals of the project:

### 1. Full simulation realism
Noesis does not aim to simulate physics, biology, or psychology in detail.
It enforces consistency, not realism.

### 2. Predefined game mechanics
Noesis does not ship with built-in RPG systems, stats, or rulebooks.
All mechanics are external or layered on top.

### 3. Narrative automation
Noesis is not an automatic story generator.
Narrative may be assisted by AI, but is not the purpose of the engine.

### 4. Universal client support
Noesis does not attempt to provide a single canonical user interface.
Clients are integration concerns.

---

## Architectural red lines

Any of the following indicates a design violation:

- Narrative systems inferring hidden world state
- Clients encoding perception logic
- World rules implemented outside the World layer
- Features requiring implicit shared knowledge
- “Convenience” access to global state

Crossing these lines requires revisiting the project’s core assumptions.

---

## Evolution boundaries

Noesis may evolve in:
- scale,
- performance,
- integration methods,
- tooling and orchestration.

Noesis must not evolve in ways that:
- collapse perception into narration,
- decentralize world truth,
- treat interpretation as authority.

---

## Design axiom

Noesis is built on a single axiom:

> A world is only believable if it can refuse to reveal itself.

All constraints derive from this assumption.

---

## Closing note

Constraints are not limitations.
They are commitments.

If a proposed feature feels powerful but violates these constraints,
it is likely powerful in the wrong direction.
