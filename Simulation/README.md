# Simulation

Numerical studies that support design decisions.

## Studies

| Study | Tool | Purpose | Constraints | Status |
|---|---|---|---|---|
| Cycle simulation | Python + Cantera | First-pass torque curve, volumetric efficiency, target check | C-006, C-007, C-012, C-013 | Complete — see [`Cycle-Simulation/`](Cycle-Simulation/README.md) |
| 1-D gas dynamics | OpenWAM | Wave-action cross-check and intake/exhaust tuning | C-006, C-007, C-024, C-025 | Planned |
| Structural FEA | FreeCAD FEM + CalculiX | Rod, piston, crank, and block stresses at peak load | C-017–C-021 | Planned |
| Thermal / CFD | OpenFOAM + ParaView | Coolant jacket, oil circuit, radiator, and airflow | C-026–C-034 | Planned |
| Valvetrain dynamics | FreeCAD + Python | Cam profile, spring, and valve-float margin | C-022 | Planned |
| Knock / combustion | Cantera | Compression-ratio and ignition-timing limits | C-005, C-017 | Planned |

## Rules

- Tag every result `[simulated]` and record the solver, version, mesh, boundary conditions,
  and input files.
- Keep inputs and reports under version control; ignore only scratch output.
- A simulation supports a design decision. It does not replace a measurement where a
  measurement is practical.
- Update the specification and constraint register when a study changes a controlled value.

## Status

The toolchain is selected and documented in [`../Software-Stack.md`](../Software-Stack.md).

The first study — a crank-angle filling-and-emptying model of the Destroyer-01(A) baseline — is
complete. It predicts **211.1 N·m at 4800 rpm** and **144.0 kW at 7000 rpm** `[simulated]`, which
meets the recorded fallback targets but not the 215 N·m / 150 kW stretch targets at those speeds.
A +5 kPa intake-pressure case or a stronger charge-cooling case reaches the stretch targets in
the model. The full report, assumptions, sensitivity band, and limitations are in
[`Cycle-Simulation/README.md`](Cycle-Simulation/README.md).

The model is a single-zone filling-and-emptying calculation; it does not resolve intake or exhaust
wave dynamics. A wave-action cross-check in OpenWAM is the next simulation step.
