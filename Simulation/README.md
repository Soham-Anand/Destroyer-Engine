# Simulation

Numerical studies that support design decisions.

## Studies

| Study | Tool | Purpose | Constraints | Status |
|---|---|---|---|---|
| Cycle simulation | Python + Cantera | First-pass torque curve, volumetric efficiency, target check | C-006, C-007, C-012, C-013 | Complete — see [`Cycle-Simulation/`](Cycle-Simulation/README.md) |
| Engine sound | Python + SciPy | Qualitative exhaust note from the cycle trace | — | First pass — see [`Acoustics/`](Acoustics/README.md) |
| Car sound simulator | Python + Pygame | Interactive transmission/vehicle sandbox with live engine note | — | Prototype — see [`Car-Simulator/`](Car-Simulator/README.md) |
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

A follow-on acoustics sketch uses the same exhaust and intake mass-flow traces to synthesize a
qualitative 1-3-4-2 engine note at 4800 and 7000 rpm `[simulated]`. The strongest low-order
component lands on the 2nd engine order (160.0 Hz at 4800 rpm, 233.3 Hz at 7000 rpm), which is the
expected firing frequency. The sound is not a validated acoustic prediction: exhaust and intake
geometry, muffler transmission loss, radiation, and microphone calibration are still missing. See
[`Acoustics/README.md`](Acoustics/README.md).

A Pygame-based car sound simulator wraps the same loops in a 1-D vehicle and transmission model
so the note can be auditioned while shifting gears. It is an interactive prototype, not a validated
driving simulator. See [`Car-Simulator/README.md`](Car-Simulator/README.md).
