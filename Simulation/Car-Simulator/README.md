# Car Sound Simulator — Destroyer-01(A)

**Status:** Interactive prototype — `[simulated]` audio and vehicle model  
**Revision:** 0.1.0 — 2026-11-10

A video-game-style sandbox for listening to the Destroyer-01(A) engine note while
driving a simplified transmission and vehicle model.  Only instruments are drawn:
tachometer, speedometer, gear, throttle/brake bars, clutch, waveform, and spectrum.
No car is rendered.

## Controls

| Key | Action |
|---|---|
| Up / Down | Throttle / brake (hold) |
| Left / Right | Shift down / up |
| Space | Clutch (hold to disengage) |
| R | Reset |
| Esc / Q | Quit |

## How it works

- Engine loops are pre-generated from [`../Acoustics/engine_sound.py`](../Acoustics/engine_sound.py)
  at 250 rpm intervals (1000–7500 rpm) and cached in `cache/` (ignored).
- All loops play simultaneously at zero volume; each frame their volumes are set from a
  triangular weight based on the current engine RPM, giving a click-free crossfade.
- Engine torque comes from the cycle-simulation sweep (`sweep.csv`); vehicle drag, rolling
  resistance, and a simple clutch/gearbox model set the acceleration.
- The waveform and spectrum panels mix the active loops with the same weights.

## Run

```bash
pixi run car-sim            # generates loops on first run
pixi run car-sim-loops       # regenerate loops explicitly
```

## Files

| Item | Path |
|---|---|
| Simulator | [`car_sim.py`](car_sim.py) |
| Loop generator | [`generate_loops.py`](generate_loops.py) |
| Engine sound synth | [`../Acoustics/engine_sound.py`](../Acoustics/engine_sound.py) |
| Torque data | [`../Cycle-Simulation/sweep.csv`](../Cycle-Simulation/sweep.csv) |
| Cache (ignored) | `cache/` |

## Limitations

- The vehicle model is a 1-D point-mass with a simplified clutch and no gear-shift
  inertia, tyre slip, or driveline backlash.
- Audio is a crossfade of pre-rendered loops, not real-time synthesis; very rapid RPM
  changes can sound slightly phasey.
- The engine note is the same qualitative `[simulated]` sketch as the acoustics study:
  no exhaust geometry, radiation, or calibration.
- Requires a display and audio device; under headless/CI use `SDL_VIDEODRIVER=dummy`
  and `SDL_AUDIODRIVER=dummy`.
