# Noesis — Event Model

This document defines the event model used by Noesis.
It formalizes what an event is, what it is not, and how events relate to
world state, perception, and information.

This model is foundational.

---

## Definition

An **event** in Noesis is:

> A factual occurrence or refusal within the world,
> anchored in time and structure,
> independent of perception or narration.

An event exists whether or not it is observed.
An event may generate information, but is not itself information.

---

## Event vs Information

### Event (ontological fact)

An event:
- happens at a specific point in world time,
- has a cause within world structure,
- may modify world state or explicitly refuse to do so,
- is globally real.

Events answer the question:

> *What actually happened in the world?*

---

### Information (epistemic artifact)

Information:
- is always about an event,
- is produced through perception,
- is partial, local, and situated,
- may omit cause, scope, or consequence.

Information answers the question:

> *What can this entity know about what happened?*

---

### Core separation

Event and information must never be conflated.

- An unobserved event is still an event.
- A perceived change without an event is not possible.
- Lack of information is a valid and meaningful outcome.

---

## Event lifecycle

All interaction in Noesis follows a strict lifecycle:
Intention
↓
World evaluation
↓
Event (fact or refusal)
↓
Perception filtering
↓
Information
↓
Narrative interpretation

Only the **Event** step is authoritative.

---

## Event categories

### 1. Action attempt events

These represent an intention entering the world for evaluation.

Examples:
- `MOVE_ATTEMPT`
- `SAY_ATTEMPT`
- `INTERACT_ATTEMPT`

They are not outcomes.
They do not modify world state.

Their purpose is to anchor causality.

---

### 2. World events (state facts)

These represent accepted, realized changes.

Examples:
- `ENTITY_ENTERED`
- `ENTITY_LEFT`
- `ATTRIBUTE_CHANGED`
- `OBJECT_CREATED`
- `OBJECT_DESTROYED`

World events:
- always modify world state,
- are globally true,
- persist regardless of perception.

---

### 3. Refusal events

These represent explicit denial by the world.

Examples:
- `MOVE_DENIED`
- `ACTION_BLOCKED`
- `ACCESS_REFUSED`

Refusal is not absence.
Refusal is a factual outcome.

> The world saying “no” is as real as the world saying “yes”.

---

## Events and time

Events are strictly ordered in world time.

- Events define temporal progression.
- World state at time *t+1* is the result of applying event *t*.
- Narration and perception do not affect ordering.

Temporal anchoring is mandatory.
An event without time is invalid.

---

## Events and structure

An event must be structurally valid.

- If an action violates structural rules, no world event occurs.
- Instead, a refusal event is generated.

Structure defines:
- which event types are possible,
- which transitions are allowed,
- what constitutes a valid cause.

Events instantiate structure in time.

---

## Events and relations

Events are the only mechanism that may:
- create relations,
- alter relations,
- dissolve relations.

Relations do not change spontaneously.
They are always the result of an event.

---

## Events and perception

Events are global.
Perception is not.

A single event may result in:
- full information for one entity,
- partial information for another,
- no information for a third.

This does not create multiple events.
It creates multiple informational projections of the same event.

---

## Visibility constraint

An entity may only receive information derived from events
that pass perception filtering.

If perception denies access:
- the event still exists,
- the entity receives no information,
- the event is indistinguishable from non-existence for that entity.

This is intentional.

---

## Events and narrative

Narrative systems:
- do not generate events,
- do not modify events,
- do not reinterpret events globally.

Narrative systems may:
- describe perceived information,
- speculate about unseen causes,
- assign meaning to experience.

Narrative output has no authority.

---

## Invariants

The following statements must always remain true:

- Every change in world state corresponds to an event
- Every refusal corresponds to an event
- No event depends on being perceived
- No information exists without an originating event
- No narrative alters event history

Violation of any invariant constitutes a design failure.

---

## Summary

Events are the temporal backbone of Noesis.

They are:
- objective,
- irreversible,
- perception-independent,
- structurally constrained.

Information and narrative exist only in relation to events,
never in place of them.
