# Engineering Constraints

The constraint register is [`constraints.md`](constraints.md). It records the performance,
structural, thermal, material, packaging, and life limits that the design must respect.

Each constraint has an ID (`C-###`), a type (`target`, `limit`, or `interface`), a
verification method, and a status (`defined`, `provisional`, `TBD`, or `verified`).

Constraints are linked to the baseline in [`../Specifications/Destroyer-01-specification.md`](../Specifications/Destroyer-01-specification.md).
Changing a constraint requires updating the register, the specification, and
`Specifications/destroyer-01.json` together, then re-running `Calculations/analyse_spec.py`.
