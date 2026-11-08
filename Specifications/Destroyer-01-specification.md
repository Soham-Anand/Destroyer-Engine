# Destroyer-01 Specification

**Engine:** Destroyer-01 — ethanol-fueled, naturally aspirated inline-4  
**Status:** Conceptual design target — not validated  
**Revision:** 0.1.0 — 2026-11-08  
**Machine-readable baseline:** [`destroyer-01.json`](destroyer-01.json)  
**Constraint register:** [`../Engineering-Constraints/constraints.md`](../Engineering-Constraints/constraints.md)

> This document defines the **Destroyer-01(A)** naturally aspirated baseline. Values are design
> targets unless tagged `[calculated]`, `[provisional]`, or `[TBD]`. Derived values are
> first-order estimates from the stated geometry and assumptions; they are **not** test data.
> See [`../README.md`](../README.md) for the project-level evidence rules.

---

## 1. Scope

Destroyer-01 is a 2.0 L class, four-cylinder ethanol engine concept intended for a lightweight
performance application. This revision fixes the core geometry, performance targets, and
system architecture so that CAD, calculations, and simulation can proceed from a common
baseline.

The turbocharged variant **Destroyer-01(T)** and the petrol concept **Destroyer-02** are outside this
specification. A turbo variant will require a separate specification with lower compression
ratio, upgraded structural components, and an intercooler.

---

## 2. Architecture

| Item | Baseline | Status |
|---|---|---|
| Layout | Inline-4, longitudinal or transverse installation TBD | `[provisional]` |
| Valvetrain | DOHC, 4 valves per cylinder, bucket tappets | `[target]` |
| Aspiration | Naturally aspirated | `[target]` |
| Fuel system | Port fuel injection (PFI), 4 injectors | `[target]` |
| Ignition | Coil-on-plug | `[target]` |
| Cam phasing | Variable intake cam timing | `[provisional]` |
| Cooling | Liquid-cooled, pressurised | `[target]` |
| Firing order | 1–3–4–2 | `[target]` |
| Cylinder numbering | 1 at front, front-to-rear 1-2-3-4 | `[provisional]` |
| Engine rotation | Clockwise viewed from the front | `[provisional]` |

Direct injection is retained as a future option. It would improve cold-start behaviour and
knock margin, but PFI is the simpler baseline for the concept phase.

---

## 3. Core geometry

| Parameter | Value | Status |
|---|---|---|
| Bore | 86.0 mm | `[target]` |
| Stroke | 86.0 mm | `[target]` |
| Bore / stroke | 1.000 | `[calculated]` |
| Cylinder count | 4 | `[target]` |
| Total displacement | 1998.2 cc | `[calculated]` |
| Swept volume per cylinder | 499.6 cc | `[calculated]` |
| Compression ratio | 12.5 : 1 | `[target]` |
| Clearance volume per cylinder | 43.44 cc | `[calculated]` |
| Connecting-rod length | 143 mm | `[provisional]` |
| Rod length / stroke | 1.663 | `[calculated]` |
| Crank radius / rod length (λ) | 0.3007 | `[calculated]` |
| Cylinder spacing | 96 mm | `[provisional]` |

The clearance volume is the **total** volume above the piston at TDC: combustion-chamber
volume, gasket volume, deck clearance, and piston crown/valve-relief volume. Its allocation
across those features is `[TBD]` and will be fixed during head and piston design.

---

## 4. Performance targets

| Parameter | Target | Status |
|---|---|---|
| Peak power | 150 kW (201 hp) @ 7000 rpm | `[target]` |
| Peak torque | 215 N·m @ 4800 rpm | `[target]` |
| Redline | 7500 rpm | `[target]` |
| Fuel cut | 7600 rpm | `[target]` |
| Idle | 850 rpm | `[target]` |
| Peak-power BMEP | 12.9 bar | `[calculated]` |
| Peak-torque BMEP | 13.5 bar | `[calculated]` |
| Specific power | 75.1 kW/L | `[calculated]` |
| Specific torque | 107.6 N·m/L | `[calculated]` |
| Best BSFC | ≤ 410 g/kWh | `[target]` |
| BSFC at peak power | ≤ 435 g/kWh | `[target]` |

These are **upper-end naturally aspirated targets**. Delivering them requires validated head
flow, a matched cam profile, intake cam phasing, and a tuned intake system. If 1-D simulation
shows a shortfall, the fallback targets are **140 kW @ 7000 rpm** and **205 N·m @ 4800 rpm**.

---

## 5. Fuel, air, and control

| Parameter | Value | Status |
|---|---|---|
| Fuel | E100 ethanol | `[target]` |
| Research octane number | ≥ 108 | `[target]` |
| Motor octane number | ≥ 89 | `[target]` |
| Stoichiometric AFR (mass) | 9.0 : 1 | `[target]` |
| WOT lambda | 0.85 ± 0.03 | `[target]` |
| Idle lambda | 1.00 ± 0.02 | `[target]` |
| Lower heating value | 26.8 MJ/kg | `[target]` |
| Fuel density at 20 °C | 789 kg/m³ | `[target]` |
| Latent heat of vaporization | ≈ 840 kJ/kg | `[target]` |
| Injection pressure | 4.0 bar | `[target]` |
| Injector count | 4 | `[target]` |
| Max injector duty at peak power | 80 % | `[target]` |
| Injector static flow target | 500 cc/min | `[target]` |
| Fuel pump flow target | ≥ 120 L/h at 4 bar | `[provisional]` |
| ECU | Standalone, sequential injection, coil-on-plug | `[target]` |
| Lambda feedback | Wideband, ethanol-calibrated | `[target]` |
| Knock control | Cylinder-selective knock sensor | `[target]` |

E100 has a high latent heat of vaporization and low vapour pressure compared with petrol.
Cold starting therefore needs a dedicated strategy (cranking enrichment, injector phasing, and
possibly a heated intake or injector seats). This is an open item, not a solved part of the
baseline.

---

## 6. Valvetrain and ports

All values in this section are `[provisional]` and intended as a starting point for 1-D
simulation and head design.

| Parameter | Intake | Exhaust |
|---|---|---|
| Valve diameter | 35.5 mm | 30.5 mm |
| Valve lift | 11.5 mm | 10.5 mm |
| Lift / diameter | 0.324 | 0.344 |
| Duration at 0.050 in (1.27 mm) | 260° | 256° |
| Open | 16° BTDC | 56° BBDC |
| Close | 64° ABDC | 20° ATDC |
| Port diameter | 33 mm | 28 mm |
| Valve overlap | 36° | — |

The cam profile, ramp rates, spring specification, and retainer/keeper design are `[TBD]`.
Valve float must remain at least 500 rpm above the redline.

---

## 7. Thermal management

| Parameter | Value | Status |
|---|---|---|
| Coolant | 50/50 ethylene glycol / water | `[target]` |
| Coolant outlet target | 90 °C | `[target]` |
| Coolant maximum continuous | 105 °C | `[limit]` |
| Coolant ΔT across engine | 10 K | `[target]` |
| Oil target | 110 °C | `[target]` |
| Oil maximum continuous | 130 °C | `[limit]` |
| Oil ΔT across engine | 20 K | `[target]` |
| Heat to coolant | 40 % of rejected heat | `[target]` |
| Heat to oil | 10 % of rejected heat | `[target]` |
| Heat to exhaust | 46 % of rejected heat | `[target]` |
| Radiation and other losses | 4 % of rejected heat | `[target]` |

At the peak-power target the estimated fuel power is 485.8 kW, of which 335.8 kW is rejected.
The resulting first-order heat loads are approximately 134.3 kW to coolant, 33.6 kW to oil,
154.4 kW to exhaust, and 13.4 kW to radiation. Required flow rates at the stated ΔT are about
**217 L/min** coolant and **59 L/min** oil. These values size the pumps, radiator, and oil
cooler; they are not yet validated by thermal simulation.

---

## 8. Mechanical loads and limits

| Parameter | Value | Status |
|---|---|---|
| Peak cylinder pressure limit (NA) | 100 bar | `[limit]` |
| Gas force at pressure limit | 58.1 kN | `[calculated]` |
| Reciprocating mass target | 0.60 kg | `[provisional]` |
| Inertia force at 7500 rpm | 20.7 kN | `[calculated]` |
| Rod compressive design limit | 120 kN | `[limit]` |
| Rod tensile design limit | 35 kN | `[limit]` |
| Mean piston speed limit | 22 m/s | `[limit]` |
| Fatigue safety factor on crank, rod, and piston | ≥ 1.5 | `[target]` |

The inertia force is calculated at TDC using the reciprocating-mass target. It reduces the
net compressive load at firing TDC and becomes a tensile load at the overlap TDC. Final loads
must come from a pressure–crank-angle trace and a dynamic rod/crank model, not from the
constant-pressure estimate above.

---

## 9. Materials (preliminary)

| Component | Baseline material | Status |
|---|---|---|
| Cylinder block | A356-T6 aluminium with pressed-in iron liners | `[provisional]` |
| Cylinder head | A356-T6 aluminium | `[provisional]` |
| Crankshaft | Forged 4340 steel | `[target]` |
| Connecting rods | Forged 4340 steel | `[target]` |
| Pistons | Forged 2618-T61 aluminium | `[target]` |
| Intake valves | 21-4N stainless steel | `[target]` |
| Exhaust valves | Inconel 751 | `[provisional]` |
| Head gasket | Multi-layer steel (MLS) | `[target]` |
| Seals | FKM / PTFE, ethanol-compatible | `[target]` |

Ethanol compatibility rules: no zinc or brass in the fuel path, no bare aluminium in continuous
liquid-fuel contact, and no standard petrol-only elastomers. Intake-port surfaces exposed to
fuel spray require a compatibility assessment (coating or anodizing if needed). The final
material selection must include corrosion, wear, and fatigue data.

---

## 10. Mass, packaging, and life

| Parameter | Target | Status |
|---|---|---|
| Dry mass (dressed, no fluids) | ≤ 160 kg | `[target]` |
| Length | ≤ 650 mm | `[provisional]` |
| Width | ≤ 600 mm | `[provisional]` |
| Height | ≤ 700 mm | `[provisional]` |
| Design life | 100,000 km / 2,000 hours | `[target]` |
| Ambient temperature | −10 °C to 45 °C | `[interface]` |
| Altitude | ≤ 2000 m | `[interface]` |

Packaging dimensions exclude the radiator, exhaust system, and ECU harness unless stated
otherwise. A mass budget will be maintained from the CAD BOM.

---

## 11. Derived estimates

The following values are produced by [`../Calculations/analyse_spec.py`](../Calculations/analyse_spec.py)
from `destroyer-01.json`. They are `[calculated]` first-order estimates.

| Quantity | Value |
|---|---|
| Swept volume per cylinder | 499.6 cc |
| Total displacement | 1998.2 cc |
| Clearance volume per cylinder | 43.44 cc |
| Torque at peak power | 204.6 N·m |
| Power at peak torque | 108.1 kW |
| BMEP at peak torque | 13.52 bar |
| BMEP at peak power | 12.87 bar |
| Mean piston speed at 4800 / 7000 / 7500 rpm | 13.76 / 20.07 / 21.50 m/s |
| Maximum piston speed at 7500 rpm | 35.3 m/s |
| Maximum piston acceleration at 7500 rpm | 34,500 m/s² (3,518 g) |
| Fuel flow at peak power | 65.25 kg/h (82.7 L/h) |
| Air flow at peak power (λ = 0.85) | 0.1387 kg/s |
| Volumetric efficiency at peak power | 100.5 % |
| Injector flow required at 80 % duty | 431 cc/min |
| Fuel power at peak power | 485.8 kW |
| Rejected heat at peak power | 335.8 kW |
| Coolant heat load / flow | 134.3 kW / 217 L/min |
| Oil heat load / flow | 33.6 kW / 59 L/min |
| Exhaust heat load | 154.4 kW |
| Intake port mean velocity at peak power | 94.4 m/s |
| Intake valve-curtain mean velocity at peak power | 62.9 m/s |
| Gas force at 100 bar | 58.1 kN |
| Reciprocating inertia force at 7500 rpm | 20.7 kN |

These values are sensitive to the assumptions for brake efficiency, volumetric efficiency,
heat split, and discharge behaviour. They should be treated as sizing estimates until replaced
by simulation or measurement.

---

## 12. Rationale

- **86.0 × 86.0 mm square bore/stroke.** A square layout balances torque, breathing, and
  piston speed in a proven 2.0 L performance package. It keeps the engine inside the target
  envelope without an unusually long stroke.
- **12.5:1 compression ratio.** E100's high octane rating and charge cooling support a
  compression ratio well above petrol practice. 12.5:1 is a deliberate first target with
  margin for knock, hot spots, and production tolerances; the final value will be set from
  knock testing and 1-D simulation.
- **150 kW / 215 N·m.** This is approximately 75 kW/L and 13.5 bar BMEP, at the upper end of
  naturally aspirated 2.0 L practice. It is retained as a stretch target because ethanol's
  knock resistance and latent heat allow aggressive ignition timing and a high compression
  ratio. The fallback targets protect the project if head flow or charge motion falls short.
- **7500 rpm redline.** Mean piston speed is 21.5 m/s, inside the 22 m/s limit. The resulting
  inertia loads are manageable with forged internals, but rod and piston FEA is still required.
- **PFI baseline.** Port injection avoids the cost and calibration complexity of direct
  injection while remaining compatible with E100. It does place more demand on cold-start
  strategy and fuel vaporization.
- **Lambda 0.85 at WOT.** Rich operation provides charge cooling and protects exhaust valves
  at peak power. The fuel flow and injector sizing above are based on this target.
- **Liquid cooling with a 90 °C outlet.** This is a conventional, serviceable target that
  keeps the head and block within material limits while allowing a pressurised system.
- **Forged steel crank and rods, forged aluminium pistons.** These are selected for the
  7500 rpm and 100 bar load targets, with ethanol-compatible materials in the fuel path.

---

## 13. Open items and risks

1. **Torque-curve validation.** The 150 kW target requires ≈205 N·m at 7000 rpm, about 95 %
   of peak torque. Confirm with 1-D simulation and, if necessary, adopt the fallback targets.
2. **Knock limit.** Validate 12.5:1 on E100; the final compression ratio may move within
   12.0–13.0 depending on chamber design and knock testing.
3. **Head flow and charge motion.** Port shape, valve seat geometry, and cam profile are not
   yet designed. The 94 m/s port-velocity estimate is only a sizing check.
4. **Cold start.** E100's low vapour pressure and high latent heat require a dedicated
   strategy. Define cranking enrichment, injector targeting, and optional heating.
5. **Oil dilution.** Ethanol dilution can degrade oil; define the oil change interval and an
   oil-analysis schedule.
6. **Structural validation.** Perform FEA on the rod, piston, crank, and block at 7500 rpm and
   100 bar. Replace the 0.60 kg reciprocating-mass estimate with CAD mass properties.
7. **Thermal validation.** Size the radiator, coolant pump (≈217 L/min target, check
   cavitation), oil cooler, and fan using a transient thermal model, not only the
   steady-state estimate in this document.
8. **Fuel-system materials and fuel specification.** Verify every wetted material against
   E100; include the tank, pump, regulator, rail, injectors, and seals. Confirm E100
   availability; E85 or blended fuel requires recalibration and a specification revision.
9. **Emissions.** E100 reduces some emissions but aldehyde formation and cold-start behaviour
   still need aftertreatment planning.
10. **Packaging and mass.** Build the CAD BOM and track mass against the 160 kg target.
11. **Turbo variant.** Do not reuse the 12.5:1 baseline for Destroyer-01(T); define a separate
    lower-compression, higher-strength specification.
12. **Cost and manufacturing.** Not yet assessed; can affect block, head, and fuel-system
    choices.

---

## 14. Revision history

| Revision | Date | Change |
|---|---|---|
| 0.1.0 | 2026-11-08 | Initial Destroyer-01(A) baseline: geometry, performance targets, architecture, thermal and material assumptions |
