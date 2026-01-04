# Noesis — Proof of Concept (PoC)

This document defines the first executable proof of concept for Noesis.

Its purpose is not to demonstrate features,
but to validate the core architectural loop:
**truth → event → perception → information**.

---

## Goal

Demonstrate that:

1. A single world event exists as an objective fact
2. The same event produces different information for different entities
3. Perception, not narration, determines visibility
4. No duplicate or “per-player” events are created

If this loop holds, Noesis is viable.

---

## Scope

This PoC intentionally limits scope to the absolute minimum.

### Included
- One location
- Two player entities
- One perception asymmetry
- Two event types: `SAY` and `MOVE`

### Explicitly excluded
- Discord integration
- AI narration
- Complex mechanics
- Persistence beyond runtime
- Multiple locations

---

## World setup

### Location
- One room: `Room_1`

### Entities

#### Entity A
- Type: Player
- Rx: `Real`
- Tx: `Real`

#### Entity B
- Type: Player
- Rx: `Real`
- Tx: `Obf2` (obfuscated)

Both entities are located in `Room_1`.

---

## Perception rules

- `Real` entities cannot perceive `Obf2`
- No Auspex or enhanced perception is present
- Entity B is fully invisible to Entity A
- Entity B perceives Entity A normally

---

## Scenario 1 — SAY event

### Action
Entity B attempts to speak.

### Event flow
1. `SAY_ATTEMPT` (by Entity B)
2. World validates the attempt
3. `SAY_EVENT` is generated

### Expected perception
- Entity B receives information about the event
- Entity A receives **no information**
- Event exists globally regardless of perception

### Success criteria
- One canonical SAY event exists
- Zero information packets for Entity A
- One information packet for Entity B

---

## Scenario 2 — MOVE event

### Action
Entity B attempts to move through an exit.

### Event flow
1. `MOVE_ATTEMPT` (by Entity B)
2. World validates the attempt
3. `ENTITY_LEFT` and `ENTITY_ENTERED` events occur

### Expected perception
- Entity B perceives its own movement
- Entity A perceives **no arrival or departure**
- Location relations update globally

### Success criteria
- Movement events exist in world state
- Entity A remains unaware of Entity B’s movement
- No perception leakage occurs

---

## Observability

### World log
The world layer must record:
- all events,
- in correct temporal order,
- independent of perception.

### Bridge output (if present)
The integration layer may output:
- event ID
- event type
- actor
- location
- list of perceiving entities

Narrative content is not required.

---

## Failure conditions

The PoC is considered failed if any of the following occur:

- Separate events are created per observer
- Entity A receives any information about Entity B
- Event existence depends on perception
- Narrative assumptions fill missing information
- Perception logic exists outside the world layer

---

## Success condition

The PoC is successful if:

> One event exists,  
> different entities know different things about it,  
> and the system does not attempt to reconcile that difference.

---

## Rationale

This PoC validates the core promise of Noesis:

> A shared world does not require shared experience.

If this cannot be demonstrated at minimal scale,
no further complexity is justified.

---

## Next steps (out of scope)

If the PoC succeeds, the next phases may include:
- Discord as a presentation layer
- AI as a narrative interpreter
- Additional perception layers
- Expanded event vocabulary

None of these should be attempted before this PoC passes.
