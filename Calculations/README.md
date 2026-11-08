# Calculations

First-order hand-calculation helpers for the Destroyer-01 baseline.

| File | Purpose |
|---|---|
| [`calculations.py`](calculations.py) | Geometry, piston kinematics, performance, fuel/air, thermal, load, and port calculations |
| [`analyse_spec.py`](analyse_spec.py) | Loads `Specifications/destroyer-01.json`, computes the baseline, and checks consistency |
| [`test_calculations.py`](test_calculations.py) | Unit tests for the helper functions |

## Run

```bash
python3 Calculations/test_calculations.py
python3 Calculations/analyse_spec.py
```

`analyse_spec.py` exits non-zero if a hard consistency check fails. It is the quickest way
to catch a specification edit that no longer agrees with the geometry or targets.

## Conventions

- SI units unless a name says otherwise (`_mm`, `_cc`, `_bar`, `_rpm`, `_kw` are only used in
  prose; the functions use metres, cubic metres, pascals, watts, and radians).
- Crank angle inputs are in radians. Valve durations and events in the specification are in
  crank degrees.
- All results are `[calculated]` estimates. They are not validation and must not be reported
  as measured data.
- The JSON specification is the numeric source of truth for `analyse_spec.py`; update it and
  `Specifications/Destroyer-01-specification.md` together.
- Add a unit test for every new helper, and keep the existing public function names stable.
