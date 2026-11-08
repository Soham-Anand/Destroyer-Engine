# Specifications

This directory holds the controlled engineering baseline for each engine variant.

| File | Purpose |
|---|---|
| [`Destroyer-01-specification.md`](Destroyer-01-specification.md) | Human-readable Destroyer-01(A) baseline |
| [`destroyer-01.json`](destroyer-01.json) | Machine-readable baseline used by the calculation scripts |

## Rules

- `destroyer-01.json` is the numeric source of truth for scripts. Update it and the Markdown
  specification together.
- Every numeric value must carry an evidence status in the Markdown document:
  `[target]`, `[calculated]`, `[provisional]`, `[TBD]`, `[simulated]`, or `[measured]`.
- Design targets are not validation. A value moves to `[simulated]` or `[measured]` only when
  the supporting study or test is recorded.
- A variant that changes compression ratio, aspiration, or structural limits gets its own
  specification file; do not overload the Destroyer-01 baseline.

## Current baseline

Destroyer-01(A): 1998 cc inline-4, 86.0 × 86.0 mm, 12.5:1 compression ratio, naturally aspirated,
port fuel injection, E100 ethanol, 150 kW / 215 N·m targets, 7500 rpm redline.
