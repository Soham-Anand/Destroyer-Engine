# Simulation

Numerical studies that support design decisions.

## Planned studies

| Study | Purpose | Constraints |
|---|---|---|
| 1-D gas dynamics | Torque curve, volumetric efficiency, intake/exhaust tuning | C-006, C-007, C-012, C-013, C-024, C-025 |
| Structural FEA | Rod, piston, crank, and block stresses at peak load | C-017–C-021 |
| Thermal / CFD | Coolant jacket, oil circuit, radiator, and airflow | C-026–C-034 |
| Valvetrain dynamics | Cam profile, spring, and valve-float margin | C-022 |
| Knock / combustion | Compression-ratio and ignition-timing limits | C-005, C-017 |

## Rules

- Tag every result `[simulated]` and record the solver, version, mesh, boundary conditions,
  and input files.
- Keep inputs and reports under version control; ignore only scratch output.
- A simulation supports a design decision. It does not replace a measurement where a
  measurement is practical.
- Update the specification and constraint register when a study changes a controlled value.

## Status

Not started. The first study should be a 1-D model of the 150 kW / 215 N·m target, because it
determines whether the performance baseline is credible or the fallback targets are needed.
