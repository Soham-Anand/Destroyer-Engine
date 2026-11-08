# Destroyer-01 Engineering Constraints

**Revision:** 0.1.0 — 2026-11-08  
**Status:** Conceptual — constraints are targets or limits, not validated requirements  
**Applies to:** Destroyer-01(A), naturally aspirated ethanol baseline  
**Specification:** [`../Specifications/Destroyer-01-specification.md`](../Specifications/Destroyer-01-specification.md)

---

## How to read this register

| Type | Meaning |
|---|---|
| `target` | A chosen design goal. Misses are acceptable only through a recorded revision. |
| `limit` | A hard design or operating limit that the concept must not exceed. |
| `interface` | An external requirement or boundary condition. |

| Status | Meaning |
|---|---|
| `defined` | Value is fixed for this revision. |
| `provisional` | Value is a placeholder pending detailed design. |
| `TBD` | Not yet established. |
| `verified` | Supported by calculation, simulation, or test evidence. |

Evidence tags used in project documents: `[target]`, `[calculated]`, `[simulated]`,
`[measured]`, `[provisional]`, `[TBD]`. A target is not evidence.

---

## 1. Performance and geometry

| ID | Constraint | Value | Type | Verification | Status |
|---|---|---|---|---|---|
| C-001 | Fuel | E100 ethanol, RON ≥ 108, MON ≥ 89 | interface | Fuel certificate | defined |
| C-002 | Architecture | Inline-4, DOHC 16-valve, naturally aspirated | target | Design review | defined |
| C-003 | Bore × stroke | 86.0 × 86.0 mm | target | CAD / measurement | defined |
| C-004 | Total displacement | 1998 cc ± 1 % | target | Calculation / CAD | defined |
| C-005 | Compression ratio | 12.5 ± 0.2 : 1 | target | Volume measurement | defined |
| C-006 | Peak power | 150 kW ± 5 % @ 7000 rpm | target | Dyno | defined |
| C-007 | Peak torque | 215 N·m ± 5 % @ 4800 rpm | target | Dyno | defined |
| C-008 | Redline / fuel cut | 7500 / 7600 rpm | limit | ECU calibration | defined |
| C-009 | Peak-torque BMEP | 13.5 bar | target | Dyno | defined |
| C-010 | Peak-power BMEP | 12.9 bar | target | Dyno | defined |
| C-011 | Specific power | 75 kW/L | target | Dyno | defined |
| C-012 | Best BSFC | ≤ 410 g/kWh | target | Dyno | defined |
| C-013 | BSFC at peak power | ≤ 435 g/kWh | target | Dyno | defined |
| C-014 | WOT lambda | 0.85 ± 0.03 | target | Wideband lambda | defined |
| C-015 | Idle lambda | 1.00 ± 0.02 | target | Wideband lambda | defined |

**Notes**

- C-004 is checked against the declared 1998.2 cc in `destroyer-01.json`.
- C-006 and C-007 are stretch targets. The recorded fallback is 140 kW @ 7000 rpm and
  205 N·m @ 4800 rpm if 1-D simulation shows a shortfall. The fallback is an alternative
  baseline, not a pass band; adopting it requires a specification revision.
- C-012 and C-013 convert to brake efficiencies of approximately 32.8 % and 30.9 % using
  E100's lower heating value of 26.8 MJ/kg.

---

## 2. Mechanical and structural

| ID | Constraint | Value | Type | Verification | Status |
|---|---|---|---|---|---|
| C-016 | Mean piston speed | ≤ 22 m/s at redline | limit | Calculation | defined |
| C-017 | Peak cylinder pressure (NA) | ≤ 100 bar | limit | 1-D simulation / FEA | defined |
| C-018 | Rod compressive load | ≤ 120 kN | limit | FEA | defined |
| C-019 | Rod tensile load | ≤ 35 kN | limit | FEA | defined |
| C-020 | Reciprocating mass | ≤ 0.60 kg | target | CAD mass properties / weighing | provisional |
| C-021 | Fatigue safety factor | ≥ 1.5 on crank, rod, and piston | target | FEA | TBD |
| C-022 | Valve float margin | ≥ 500 rpm above redline | limit | Spintron / test | TBD |
| C-023 | Valve lift / diameter | 0.25–0.40 | target | CAD | provisional |
| C-024 | Intake port mean velocity at peak power | 70–110 m/s | target | CFD / flow bench | provisional |
| C-025 | Intake valve-curtain mean velocity at peak power | 55–75 m/s | target | CFD / flow bench | provisional |

**Notes**

- C-016 gives 21.5 m/s at 7500 rpm with the 86 mm stroke.
- C-017 produces a 58.1 kN gas force on the 86 mm bore. The rod limit of 120 kN is a design
  limit, not a predicted load; final loads require a pressure–crank-angle trace.
- C-020 is a provisional reciprocating-mass target for the piston, pin, rings, and small-end
  rod. Replace it with CAD mass properties as soon as the piston and rod models exist.

---

## 3. Thermal and operating

| ID | Constraint | Value | Type | Verification | Status |
|---|---|---|---|---|---|
| C-026 | Coolant outlet target | 90 °C | target | Dyno | defined |
| C-027 | Coolant maximum continuous | 105 °C | limit | Dyno | defined |
| C-028 | Oil target | 110 °C | target | Dyno | defined |
| C-029 | Oil maximum continuous | 130 °C | limit | Dyno | defined |
| C-030 | Coolant ΔT across engine | 10 K | target | Dyno | defined |
| C-031 | Oil ΔT across engine | 20 K | target | Dyno | defined |
| C-032 | Heat rejection to coolant at peak power | ≈ 135 kW | target | Thermal calculation / test | defined |
| C-033 | Coolant flow at peak power | ≈ 217 L/min | target | Pump sizing / test | defined |
| C-034 | Oil flow at peak power | ≈ 59 L/min | target | Pump sizing / test | defined |
| C-035 | Ambient temperature | −10 °C to 45 °C | interface | Environmental test | defined |
| C-036 | Altitude | ≤ 2000 m | interface | Calibration / test | defined |
| C-037 | Coolant | 50/50 ethylene glycol / water | interface | Build specification | defined |

**Notes**

- C-032 to C-034 assume 40 % of rejected heat goes to coolant and 10 % to oil, with a 10 K
  coolant ΔT and 20 K oil ΔT. They are first-order sizing values.
- The cooling system must also cover idle, low-speed high-load, and heat-soak cases; the
  peak-power case alone is not sufficient for radiator sizing.

---

## 4. Fuel, materials, and control

| ID | Constraint | Value | Type | Verification | Status |
|---|---|---|---|---|---|
| C-038 | Fuel-system materials | No zinc or brass in the fuel path; bare aluminium not permitted in continuous liquid-fuel contact; intake-port surfaces to be assessed | interface | Material review | defined |
| C-039 | Elastomer compatibility | FKM / PTFE or equivalent for E100 | interface | Material review | defined |
| C-040 | Injector duty at peak power | ≤ 80 % | limit | Calculation / bench | defined |
| C-041 | Injector static flow | ≈ 500 cc/min at 4 bar | target | Injector datasheet / bench | defined |
| C-042 | Fuel pump flow | ≥ 120 L/h at 4 bar | target | Bench | provisional |
| C-043 | Fuel pressure | 4.0 bar | target | Bench | defined |
| C-044 | Lambda feedback | Wideband, ethanol-calibrated | interface | ECU calibration | defined |
| C-045 | Knock control | Cylinder-selective knock sensor | interface | ECU calibration | defined |
| C-046 | Ignition | Coil-on-plug | interface | Build specification | defined |
| C-047 | Cold start | Strategy TBD; must start at −10 °C | target | Cold-chamber test | TBD |
| C-048 | Emissions aftertreatment | TBD; aldehyde control to be assessed | target | Emissions test | TBD |

**Notes**

- C-040 is checked at the peak-power fuel flow of 65.25 kg/h (82.7 L/h). Four injectors at
  80 % duty require about 431 cc/min each; 500 cc/min gives useful margin for richer
  calibration and injector aging.
- E100 cold start is a known risk. The fuel system must support cranking enrichment and
  adequate atomization; heated injector seats or a heated intake are options, not baseline.

---

## 5. Packaging, mass, and life

| ID | Constraint | Value | Type | Verification | Status |
|---|---|---|---|---|---|
| C-049 | Dry mass (dressed, no fluids) | ≤ 160 kg | target | CAD BOM / weighing | provisional |
| C-050 | Envelope length | ≤ 650 mm | target | CAD | provisional |
| C-051 | Envelope width | ≤ 600 mm | target | CAD | provisional |
| C-052 | Envelope height | ≤ 700 mm | target | CAD | provisional |
| C-053 | Design life | 100,000 km / 2,000 hours | target | Durability plan | TBD |
| C-054 | Oil change interval | 10,000 km (provisional, ethanol dilution) | target | Oil analysis | TBD |

**Notes**

- C-050 to C-052 exclude the radiator, exhaust system, and ECU harness unless the packaging
  definition says otherwise.
- C-054 is provisional because ethanol dilution can reduce oil life. The final interval must
  be set from oil analysis, not from a petrol-derived schedule.

---

## 6. Verification plan

| Stage | Method | Constraints covered |
|---|---|---|
| Concept check | `Calculations/analyse_spec.py` | C-004, C-009–C-011, C-016, C-024, C-025, C-032–C-034 |
| 1-D gas dynamics | Intake/exhaust and full-load simulation | C-006, C-007, C-012, C-013, C-017, C-024, C-025 |
| Structural FEA | Rod, piston, crank, block | C-017–C-021 |
| Thermal / CFD | Coolant jacket, oil circuit, radiator | C-026–C-034 |
| Flow bench | Head and port development | C-024, C-025 |
| Dyno | Performance, BSFC, lambda, thermal | C-006–C-015, C-026–C-034 |
| Durability | Endurance and cold-start testing | C-047, C-053, C-054 |

A constraint may move from `defined` to `verified` only when the evidence is recorded and
traceable. Simulation supports a design decision; it does not replace a measurement where a
measurement is practical.

---

## 7. Change rules

1. Change a constraint only by editing the specification, this register, and
   `Specifications/destroyer-01.json` together.
2. Record the reason and the new revision in the specification's revision history.
3. Re-run `python3 Calculations/analyse_spec.py` after any numeric change.
4. Do not silently relax a limit to make a calculation pass. Record the change and its
   consequence.
