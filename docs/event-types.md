# Noesis — Event Types

This document defines the canonical event types used by Noesis.
It specifies what kinds of events may exist and what guarantees they provide.

This list is intentionally minimal.
New event types should be added only when they represent a distinct
ontological category, not a convenience.

---

## Event taxonomy

All events in Noesis belong to one of three categories:

1. **Attempt events** — intentions entering the world
2. **World events** — accepted, factual changes
3. **Refusal events** — explicit denials by the world

No event may belong to more than one category.

---

## 1. Attempt events

Attempt events represent an intention submitted for world evaluation.
They do not modify world state.

They exist to:
- anchor causality,
- provide temporal ordering,
- allow explicit refusal events.

### Characteristics

- Generated before validation
- Never change world state
- Always followed by either a world event or a refusal event

### Canonical attempt events

#### `MOVE_ATTEMPT`
An entity attempts to move through a specific exit or direction.

Payload (conceptual):
- actor
- origin location
- target exit or direction

---

#### `INTERACT_ATTEMPT`
An entity attempts to interact with another entity or object.

Payload:
- actor
- target
- interaction type

---

#### `SAY_ATTEMPT`
An entity attempts to produce audible output in a location.

Payload:
- actor
- location
- content reference (opaque)

---

#### `POSE_ATTEMPT`
An entity attempts to produce expressive output.

Payload:
- actor
- location
- content reference (opaque)

---

## 2. World events (state facts)

World events represent accepted, realized changes to world state.
They are globally true and persistent.

### Characteristics

- Modify world state
- Anchored in world time
- Independent of perception
- May generate zero or more information projections

### Canonical world events

#### `ENTITY_ENTERED`
An entity successfully enters a location.

Effects:
- updates entity-location relation
- creates new co-presence relations

---

#### `ENTITY_LEFT`
An entity successfully leaves a location.

Effects:
- dissolves entity-location relation

---

#### `ATTRIBUTE_CHANGED`
A world attribute changes value.

Effects:
- modifies entity or object state

---

#### `OBJECT_CREATED`
A new object enters existence.

Effects:
- creates a new world entity
- assigns initial relations and attributes

---

#### `OBJECT_DESTROYED`
An object ceases to exist.

Effects:
- removes entity
- dissolves all relations

---

#### `PERCEPTION_CHANGED`
An entity’s perception capabilities change.

Effects:
- updates Rx and/or Tx levels
- alters future information access

---

## 3. Refusal events

Refusal events represent explicit denials by the world.
They are factual outcomes, not errors.

### Characteristics

- Do not modify world state
- Are globally real
- Must always correspond to a prior attempt event

### Canonical refusal events

#### `MOVE_DENIED`
A movement attempt is rejected.

Common causes:
- blocked exit
- insufficient access
- structural constraint

---

#### `ACTION_BLOCKED`
An interaction attempt is rejected.

Common causes:
- permission failure
- invalid target
- structural rule violation

---

#### `SAY_BLOCKED`
An attempt to produce audible output is rejected.

Common causes:
- silence effects
- perception constraints
- location rules

---

## Event pairing invariant

Every attempt event must result in exactly one of:

- a world event, or
- a refusal event.

No attempt may terminate silently.

---

## Event visibility

All events are global facts.
Visibility is determined exclusively by the Perception model.

- An event may generate information for some entities
- The same event may generate no information for others
- Lack of information does not imply lack of event

---

## Payload constraints

Event payloads must be:

- minimal,
- factual,
- free of interpretation,
- opaque with respect to narrative content.

Textual content (speech, pose) must be treated as uninterpreted data.

---

## Non-events

The following are explicitly not events:

- narrative descriptions
- emotional reactions
- inferred causes
- summaries or aggregates
- delayed interpretations

These may exist only as narrative artifacts.

---

## Extension rules

New event types may be introduced only if they:

- represent a distinct ontological change or refusal,
- cannot be expressed as a combination of existing events,
- do not encode narrative meaning.

Convenience or presentation is not sufficient justification.

---

## Summary

Event types define the vocabulary of change in Noesis.

They:
- constrain what may happen,
- anchor causality in time,
- protect world truth from interpretation.

Anything not listed here is either:
- an intention,
- information,
- or narrative.

And none of those are events.
