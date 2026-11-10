# Crank-Angle Cycle Simulation — Destroyer-01(A)

**Status:** First-pass study complete — `[simulated]`, not experimentally validated  
**Revision:** 0.1.0 — 2026-11-10  
**Engine baseline:** [`Specifications/destroyer-01.json`](../../Specifications/destroyer-01.json)  
**Constraint register:** [`Engineering-Constraints/constraints.md`](../../Engineering-Constraints/constraints.md)  
**Solver:** Cantera 3.2.0 + NumPy 2.5.4, Python 3.12.16 (pinned by `pixi.toml`)

> Every number in this report is a **`[simulated]`** result from the model described below.
> None of it is dyno data. The model is a first-order filling-and-emptying calculation, not a
> wave-action 1-D code, and it has not been calibrated against a running engine.

---

## 1. Purpose and result

This study asks a single question: **can the Destroyer-01(A) baseline geometry and cam make
150 kW at 7000 rpm and 215 N·m at 4800 rpm?** The recorded fallback is 140 kW and 205 N·m at
the same speeds (C-006/C-007).

Short answer: **the baseline meets the fallback targets in the model, but not the stretch
targets at their specified speeds.** It predicts 211.1 N·m at 4800 rpm and 144.0 kW at 7000 rpm.
The model's torque peak is at 3500 rpm, not 4800 rpm, and its power peak is at 7500 rpm, not
7000 rpm. That shape is a direct consequence of the model having no intake or exhaust wave
dynamics: it cannot produce the resonant torque hump that a tuned naturally aspirated engine uses
to hold torque at 4800 rpm.

A modest pressure recovery at the intake (+5 kPa, 106.325 kPa absolute) or stronger charge
cooling (effectiveness 0.50 instead of 0.35) is enough to clear both stretch targets in the
model:

| Case | Torque @ 4800 rpm | Power @ 7000 rpm | Verdict |
|---|---:|---:|---|
| Baseline | 211.1 N·m | 144.0 kW | fallback |
| Intake +5 kPa | 223.9 N·m | 152.9 kW | stretch |
| Charge cooling 0.50 | 222.8 N·m | 152.2 kW | stretch |

Those two cases are **sensitivity studies, not design proposals**. They show how much margin is
missing, not that a particular intake or fuel-system design will deliver it.

---

## 2. What the model is

`cycle_model.py` integrates one cylinder through a complete 720° cycle, starting and ending at
intake-valve closure (IVC = 604° in the conventional 0–720° frame, 0 = TDC firing). It is a
single-zone filling-and-emptying model:

- **Cylinder:** one uniform temperature and pressure; slider-crank volume; no spatial zones.
- **Gas exchange:** separate fresh-charge, residual-gas, and burned-gas masses. Fresh charge and
  residual are tracked independently so that residual gas dilutes the charge instead of
  releasing fuel energy a second time.
- **Valves:** compressible-orifice flow through the minimum of curtain area and port area, with a
  lift-dependent discharge coefficient. Forward and reverse flow are both allowed (intake
  backflow and exhaust reversion).
- **Combustion:** Wiebe heat release, `a = 5`, `m = 2`, duration `45° + 0.003·rpm` (59.4° at
  4800 rpm, 66.0° at 7000 rpm), with a 5° ignition delay between spark and start of combustion.
  The energy release comes from the internal-energy difference between fresh and burned
  composition; no separate LHV term is added.
- **Heat transfer:** Woschni correlation, wall temperature 450 K.
- **Friction:** Chen–Flynn, `FMEP [bar] = 0.25 + 0.004·p_max + 0.05·S̄p + 0.0012·S̄p²`.
- **Properties:** Cantera NASA-7 polynomials tabulated from 250–4200 K at 25 K spacing. The
  mechanism contains 14 species and no kinetics.
- **Solution:** classical RK4 at 0.5° crank steps, repeated for four cycles until residual
  fraction and IVC temperature converge (three cycles already give the same torque at both target
  speeds; six are used for verification). Spark timing is searched on a coarse 5° grid, then
  refined at 2.5° and 1.25° around the best-torque point (MBT).
- **Outputs:** gross and net IMEP, PMEP (positive pumping loss), FMEP, BMEP, torque, power, VE,
  BSFC, brake efficiency, peak pressure, residual fraction, and mass flows.

The cycle is solved from IVC to IVC, so the intake and exhaust strokes of the *next* cycle are
included. This is why the model can predict volumetric efficiency and gas-exchange work at all.

### What it is not

It is **not** a 1-D gas-dynamics code. There are no runners, plenum, wave propagation, or
acoustic tuning. The intake and exhaust are boundary pressures (`101.325 kPa` and `105 kPa`).
That is the main reason the predicted torque curve is flat and peaks at 3500 rpm. The model is
useful for magnitude and trend, not for cam-event or runner-length optimization.

---

## 3. Inputs and solver record

| Item | Value |
|---|---|
| Engine specification | [`Specifications/destroyer-01.json`](../../Specifications/destroyer-01.json) |
| Fuel | E100 ethanol, LHV 26.8 MJ/kg, stoichiometric AFR 9.0, WOT λ 0.85 |
| Geometry | 86.0 mm bore × 86.0 mm stroke, 143 mm rod, 12.5:1 CR, 4 cylinders |
| Intake valve | 35.5 mm, 11.5 mm lift, 260° at 0.050 in, opens 16° BTDC |
| Exhaust valve | 30.5 mm, 10.5 mm lift, 256° at 0.050 in, opens 56° BBDC |
| Thermodynamic mechanism | [`mechanisms/ethanol-air.yaml`](mechanisms/ethanol-air.yaml) |
| Model code | [`cycle_model.py`](cycle_model.py) |
| Sweep driver | [`run_sweep.py`](run_sweep.py) |
| Unit tests | [`test_cycle_model.py`](test_cycle_model.py) |
| Python / Cantera / NumPy | 3.12.16 / 3.2.0 / 2.5.4 |
| Reference air density | 1.184 kg/m³ (25 °C, 101.325 kPa) |

The 14-species mechanism (`C2H5OH, O2, N2, Ar, CO2, H2O, CO, H2, OH, O, H, N, NO, NO2`) uses
NASA-7 thermodynamic data extracted from the `nasa_gas.yaml` database bundled with Cantera 3.2
(NASA TM-4513). It contains **no reaction kinetics**; combustion is represented by the Wiebe
function. The mechanism is therefore a thermodynamic property library, not a chemistry model.

The mechanism was checked against Cantera directly: tabulated internal energy agrees with
`ct.Solution` within 1 J/kg, and `cp` and `cv` agree within 1 J/kg·K over the fitted range.

---

## 4. Assumptions

| Area | Assumption | Basis / sensitivity |
|---|---|---|
| Inlet state | 101.325 kPa, 298.15 K | Spec reference condition |
| Charge cooling | 35 % of fuel latent heat absorbed by intake charge; intake temperature 266.0 K | Calibration assumption; 50 % case reported below |
| Exhaust boundary | 105 kPa, 900 K | Typical NA backpressure; +2 kPa test changed torque < 0.3 % |
| Wall temperature | 450 K | Typical loaded coolant/oil average |
| Combustion | Wiebe `a = 5`, `m = 2`, duration 45° + 0.003·rpm, 5° ignition delay | No knock model; MBT spark is unconstrained by knock |
| Burned gas | Equilibrium composition at 1200 K, then frozen | Mid-expansion freeze; sensitivity 900–1800 K reported below |
| Residual gas | Burned composition; no NOx or unburned HC | Single-zone simplification |
| Valve flow | `Cd` = 0.72 intake, 0.68 exhaust; 0.050 in duration treated as seat-to-seat | No flow-bench data; `Cd` +5 % changed torque < 0.7 % |
| Friction | Chen–Flynn with no accessory or oil-pump detail | Standard first-order correlation |
| Heat transfer | Woschni, 450 K walls | Standard first-order correlation |
| Blowby / crevices | None | Negligible at this fidelity |
| Cylinder-to-cylinder | All four cylinders identical | Steady-state WOT sweep |
| Valve timing | Fixed at the baseline events; no VVT | VVT is `[provisional]` in the specification |

Lambda is fixed at the WOT value of 0.85. The model does not trim individual cylinders or protect
against knock; the reported MBT spark is a thermodynamic optimum, not a validated calibration.

---

## 5. Baseline results

`[simulated]` WOT sweep, 0.5° step, MBT spark at each speed. Full data:
[`sweep.csv`](sweep.csv).

| RPM | Spark (BTDC) | Torque (N·m) | Power (kW) | BMEP (bar) | VE | BSFC (g/kWh) | Peak p (bar) | Residual |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1000 | 16.25 | 191.6 | 20.1 | 12.05 | 0.883 | 408 | 60.8 | 0.028 |
| 1500 | 20.00 | 202.2 | 31.8 | 12.71 | 0.895 | 392 | 68.2 | 0.029 |
| 2000 | 22.50 | 208.3 | 43.6 | 13.10 | 0.906 | 385 | 72.9 | 0.028 |
| 2500 | 23.75 | 211.8 | 55.5 | 13.32 | 0.914 | 382 | 74.5 | 0.028 |
| 3000 | 25.00 | 213.6 | 67.1 | 13.43 | 0.919 | 381 | 75.8 | 0.027 |
| 3500 | 26.25 | 214.0 | 78.4 | 13.46 | 0.923 | 382 | 77.0 | 0.027 |
| 4000 | 27.50 | 213.5 | 89.4 | 13.43 | 0.926 | 384 | 78.1 | 0.027 |
| 4500 | 28.75 | 212.2 | 100.0 | 13.34 | 0.927 | 387 | 79.0 | 0.026 |
| 4800 | 30.00 | 211.1 | 106.1 | 13.27 | 0.927 | 389 | 80.7 | 0.026 |
| 5000 | 30.00 | 210.2 | 110.0 | 13.22 | 0.927 | 391 | 79.9 | 0.026 |
| 5500 | 31.25 | 207.5 | 119.5 | 13.05 | 0.927 | 396 | 80.7 | 0.026 |
| 6000 | 32.50 | 204.3 | 128.4 | 12.85 | 0.925 | 401 | 81.5 | 0.026 |
| 6500 | 32.50 | 200.7 | 136.6 | 12.62 | 0.923 | 408 | 79.3 | 0.026 |
| 7000 | 33.75 | 196.5 | 144.0 | 12.36 | 0.921 | 415 | 80.0 | 0.026 |
| 7500 | 35.00 | 191.9 | 150.7 | 12.07 | 0.918 | 424 | 80.6 | 0.027 |

Peak values: **214.0 N·m at 3500 rpm**, **150.7 kW at 7500 rpm**. Best BSFC is **381 g/kWh at
3000 rpm**. Peak cylinder pressure is **81.5 bar**, below the 100 bar screening limit. Residual
fraction is 2.6–2.9 %.

The low-speed VE (0.883 at 1000 rpm) is below the 0.90–1.10 band used by the sweep driver's
screening check. That is a real limitation of a fixed-cam model at low speed, not a design
failure: the baseline cam is intended for the upper rev range and has no VVT in this study.

### Target comparison

`[simulated]` values against C-006/C-007. The fallback column is applied when the stretch target
is not met at the specified speed.

| Metric | Simulated | Target | Fallback | Verdict |
|---|---:|---:|---:|---|
| Torque at 4800 rpm | 211.1 N·m | 215.0 N·m | 205.0 N·m | fallback (+1.8 % short) |
| Power at 7000 rpm | 144.0 kW | 150.0 kW | 140.0 kW | fallback (−4.0 % short) |
| Peak torque | 214.0 N·m @ 3500 rpm | 215.0 N·m @ 4800 rpm | 205.0 N·m | magnitude near target, speed wrong |
| Peak power | 150.7 kW @ 7500 rpm | 150.0 kW @ 7000 rpm | 140.0 kW | magnitude met, speed wrong |
| Best BSFC (C-012) | 381 g/kWh @ 3000 rpm | ≤ 410 g/kWh | — | pass |
| BSFC at 7000 rpm (C-013) | 415 g/kWh | ≤ 435 g/kWh | — | pass |
| Peak cylinder pressure | 81.5 bar | ≤ 100 bar | — | pass |

The model therefore supports the **fallback** performance claim, not the stretch claim. The
distinction matters: 211.1 N·m is within 2 % of 215 N·m, but the target also specifies 4800 rpm,
and the model puts the peak at 3500 rpm.

Both fallback margins are only about 3 %, smaller than the ±5–10 % uncertainty expected of a
first-order model. The fallback result is a consistency check, not a guarantee.

---

## 6. Sensitivity studies

All three cases below use the same model and MBT search; only the listed input changes. Full data
files are linked.

### 6.1 Intake pressure +5 kPa (106.325 kPa absolute)

`[simulated]` — [`sweep-tuned-intake.csv`](sweep-tuned-intake.csv)

This is a proxy for intake ram/pressure recovery from a tuned intake and a low-loss airbox. It is
applied at every speed, which is optimistic: a real ram effect is strongest near one tuned speed,
not at both 4800 and 7000 rpm.

| Metric | Simulated | Target | Verdict |
|---|---:|---:|---|
| Torque at 4800 rpm | 223.9 N·m | 215.0 N·m | target (+4.1 %) |
| Power at 7000 rpm | 152.9 kW | 150.0 kW | target (+1.9 %) |
| Peak torque | 227.0 N·m @ 3500 rpm | 215.0 N·m @ 4800 rpm | target magnitude |
| Peak power | 160.1 kW @ 7500 rpm | 150.0 kW @ 7000 rpm | target magnitude |
| Best BSFC | 379 g/kWh | ≤ 410 g/kWh | pass |
| Peak cylinder pressure | 85.7 bar | ≤ 100 bar | pass |
| VE range | 0.936–0.975 | screening 0.90–1.10 | pass |

### 6.2 Charge-cooling effectiveness 0.50

`[simulated]` — [`sweep-charge-cooling.csv`](sweep-charge-cooling.csv)

This assumes 50 % of the fuel's latent heat is absorbed by the incoming charge, giving an intake
temperature of about 252 K instead of 266 K. It is an optimistic PFI assumption; port wetting and
wall-film effects would reduce it.

| Metric | Simulated | Target | Verdict |
|---|---:|---:|---|
| Torque at 4800 rpm | 222.8 N·m | 215.0 N·m | target (+3.6 %) |
| Power at 7000 rpm | 152.2 kW | 150.0 kW | target (+1.5 %) |
| Peak torque | 225.7 N·m @ 3500 rpm | 215.0 N·m @ 4800 rpm | target magnitude |
| Peak power | 159.4 kW @ 7500 rpm | 150.0 kW @ 7000 rpm | target magnitude |
| Best BSFC | 379 g/kWh | ≤ 410 g/kWh | pass |
| Peak cylinder pressure | 84.8 bar | ≤ 100 bar | pass |
| VE range | 0.923–0.972 | screening 0.90–1.10 | pass |

### 6.3 Burned-gas composition

`[simulated]` — fixed spark (30° BTDC at 4800, 33.75° BTDC at 7000), six cycles, 0.5° step.

The reference case freezes the burned-gas composition at 1200 K. Varying that choice is a small
effect:

| Burned-gas model | Torque @ 4800 rpm | Power @ 7000 rpm | BSFC @ 7000 rpm |
|---|---:|---:|---:|
| Frozen at 900 K | 212.0 N·m | 144.7 kW | 413 g/kWh |
| Frozen at 1200 K (reference) | 211.1 N·m | 144.0 kW | 415 g/kWh |
| Frozen at 1500 K | 210.5 N·m | 143.6 kW | 416 g/kWh |
| Frozen at 1800 K | 210.1 N·m | 143.3 kW | 417 g/kWh |
| Full equilibrium table | 209.3 N·m | 142.7 kW | 419 g/kWh |

The spread is within about **1 %** of the reference, so the conclusion is not sensitive to the
composition-freeze assumption. It is much more sensitive to intake pressure and charge
temperature.

### 6.4 Other checks

| Change | Effect at 4800 / 7000 rpm |
|---|---|
| Exhaust backpressure 105 → 102 kPa | +0.3 % / +0.3 % torque |
| Valve `Cd` +5 % | +0.2 % / +0.6 % torque |
| Friction −10 % | +1.1 % / +1.6 % torque |

These are second-order compared with the intake-pressure and charge-cooling effects above.

---

## 7. Verification

No experimental validation is possible at this stage. The following checks were completed:

- **Unit tests:** 14/14 pass (`pixi run test-cycle`). They cover slider-crank volume and its
  derivative against finite differences, valve lift and effective area, choked and subsonic
  orifice flow against the analytic formula, Wiebe shape and monotonicity, Cantera property-table
  agreement, burned-table monotonicity, rich-mixture energy release, full-cycle sanity bounds,
  spark-advance/peak-pressure trend, and IVC mass accounting.
- **Grid convergence:** at fixed spark, changing the crank step from 1.0° to 0.5° to 0.25°
  changes torque by less than **0.05 %** at both 4800 and 7000 rpm.
- **Geometry:** the model reproduces 1998.2 cm³ displacement and 12.5:1 compression ratio from
  the specification; TDC/BDC volumes and `dV/dθ` are tested analytically.
- **Plausibility:** BSFC 381–424 g/kWh, peak pressure 81.5 bar, VE 0.88–0.93, and residual
  fraction 2.6–2.9 % are all in the expected range for a 12.5:1 NA ethanol engine. This is a
  sanity check, not proof of accuracy.

The missing validation is a dyno test and an independent wave-action 1-D cross-check (OpenWAM).
Until both exist, the model's absolute accuracy is unknown; a ±5–10 % band is a reasonable
planning assumption for a first-order filling-and-emptying model of this kind.

---

## 8. Limitations

1. **No wave dynamics.** Intake and exhaust are constant-pressure boundaries. The model cannot
   predict ram, resonance, or the torque peak location. This is the dominant limitation and the
   reason the 4800 rpm target is not reproduced.
2. **Single zone.** No temperature stratification, no flame propagation, no knock, no NOx, no
   cycle-to-cycle variation.
3. **Prescribed combustion.** Wiebe parameters are fixed; real burn duration depends on load,
   speed, lambda, and chamber design. MBT spark is unconstrained by knock, which is optimistic
   at 12.5:1.
4. **Fixed cam.** No VVT, no cam-phasing sweep, and the 0.050 in duration is treated as the
   seat-to-seat event. A real cam has ramps and a fuller low-lift profile; the model's VE is
   sensitive to that choice.
5. **Charge cooling is a calibration parameter.** The 0.35 effectiveness is a judgment call, not
   a measurement. The 0.50 case is a bound, not a prediction.
6. **Simplified friction and heat transfer.** Chen–Flynn and Woschni are standard first-order
   correlations. They are not a substitute for measured friction or a wall-temperature map.
7. **No port or curtain velocity output.** C-024/C-025 still require CFD or flow-bench work.
8. **No experimental validation.** The model has not been compared with a dyno, and it has not
   yet been cross-checked against OpenWAM.

The correct use of this study is to size the problem and set priorities: the baseline is close,
the missing margin is a few percent, and the next useful step is a wave-action model or a flow
bench, not more tuning of this zero-dimensional model.

---

## 9. Reproduce

From the repository root:

```bash
pixi run test          # all unit tests (calculations + cycle model)
pixi run test-cycle    # cycle-model tests only
pixi run sweep         # baseline sweep -> sweep.csv
pixi run sweep-tuned   # +5 kPa intake -> sweep-tuned-intake.csv
pixi run sweep-cooling # charge cooling 0.50 -> sweep-charge-cooling.csv
```

Each sweep takes under a minute on an Apple M4. Each run prints a Markdown summary and a target
comparison. The CSV files are tracked because they are small and are the evidence behind this
report; scratch traces and solver logs are not.

To change a case without editing code:

```bash
pixi run python Simulation/Cycle-Simulation/run_sweep.py \
  --intake-pressure-kpa 106.325 \
  --charge-cooling 0.50 \
  --burned-freeze-k 1200 \
  --output Simulation/Cycle-Simulation/sweep-custom.csv
```

`--burned-freeze-k 0` switches to the full equilibrium table. `--rpm`, `--cycles`, `--dphi`, and
`--spark-*` control the numerical sweep.

---

## 10. Files

| File | Role |
|---|---|
| `cycle_model.py` | Geometry, valve flow, gas tables, cycle integration, MBT search |
| `run_sweep.py` | Speed sweep, CSV writer, target comparison |
| `test_cycle_model.py` | 14 unit tests |
| `mechanisms/ethanol-air.yaml` | 14-species NASA-7 thermodynamic mechanism (no kinetics) |
| `sweep.csv` | Baseline `[simulated]` results |
| `sweep-tuned-intake.csv` | +5 kPa intake `[simulated]` results |
| `sweep-charge-cooling.csv` | Charge-cooling 0.50 `[simulated]` results |

## 11. Next steps

- Cross-check the baseline with OpenWAM (wave-action 1-D) to test the torque-curve shape and the
  intake-tuning assumption.
- Add a cam-phasing sweep once the VVT system is defined; the current fixed cam is a placeholder.
- Add a simple knock integral so that MBT spark is constrained at 12.5:1.
- Feed the predicted peak pressure and rod load into the structural FEA study.
- Replace the `+5 kPa` proxy with a real runner/plenum geometry once the intake packaging is
  fixed.
