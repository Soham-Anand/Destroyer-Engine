# Engine-Sound Synthesis — Destroyer-01(A)

**Status:** Qualitative first pass — `[simulated]`, not a validated sound prediction  
**Revision:** 0.1.0 — 2026-11-10  
**Engine baseline:** [`Specifications/destroyer-01.json`](../../Specifications/destroyer-01.json)  
**Excitation source:** [`../Cycle-Simulation/cycle_model.py`](../Cycle-Simulation/cycle_model.py)  
**Synthesizer:** [`engine_sound.py`](engine_sound.py)  
**Tests:** [`test_engine_sound.py`](test_engine_sound.py)

> This study produces an audible sketch, not an acoustic measurement. It has no microphone
> calibration, no exhaust geometry, and no radiation model. Do not quote an absolute sound
> pressure level or dB(A) from it.

---

## 1. Purpose and result

The cycle study predicts the engine's torque curve but says nothing about what the engine sounds
like. This study asks a narrower question: **does the predicted gas-exchange behaviour produce a
plausible four-cylinder exhaust note with the correct firing order and speed scaling?**

The synthesizer renders a 48 kHz mono WAV from the cycle model's exhaust and intake valve mass
flows `[simulated]`. At the two target speeds the strongest low-order component lands on the
second engine order, which is the firing frequency of a four-stroke inline-four:

| Speed | MBT spark | Firing frequency | Strongest low-order component | Order |
|---:|---:|---:|---:|---:|
| 4800 rpm | 30.00° BTDC | 160.0 Hz | 159.7 Hz | 2.00 |
| 7000 rpm | 33.75° BTDC | 233.3 Hz | 233.6 Hz | 2.00 |

That is a consistency check on the firing order and speed scaling. It is **not** evidence that
the real engine will sound like this. The absolute timbre depends on the exhaust runners,
collector, muffler, intake system, and radiation, none of which are in the model.

To listen, regenerate the files and play them on macOS:

```bash
pixi run sound                                   # 4800 rpm, 4 s, writes WAV + spectrogram
pixi run python Simulation/Acoustics/engine_sound.py --rpm 7000 --plot --play
pixi run python Simulation/Acoustics/engine_sound.py --rpm 4800 --play
```

The WAV and PNG files are written to `Simulation/Acoustics/output/`, which is ignored because it
is scratch output. The script and this report are version-controlled.

---

## 2. How the sound is built

1. **Cycle trace.** The crank-angle model is run to convergence at the requested speed with MBT
   spark. The trace supplies exhaust and intake valve mass flow, `mdot_out` and `mdot_in`, at
   0.5° crank resolution.
2. **Resampling.** One 720° cycle is interpolated onto an integer-length audio buffer at 48 kHz.
   The buffer length is rounded so that tiling the cycle is seamless.
3. **Cylinder summation.** Four copies of the single-cylinder flow are summed at 0°, 180°, 360°,
   and 540° in the **1-3-4-2** firing order. Small per-cylinder gain and delay offsets
   (≤ 4 % and ≤ 0.18 ms) break the perfect symmetry.
4. **Exhaust path.** The summed flow is high-passed to remove the mean component, convolved with
   an assumed decaying-resonance impulse response (180, 360, 720, 1440, and 2880 Hz), band-limited
   to 35 Hz–6 kHz, and coloured by a short feedback comb that represents a collector/tailpipe
   reflection.
5. **Intake path.** A separate, weaker path uses 400–3200 Hz resonances and an 80 Hz–7 kHz band.
6. **Turbulence layer.** A reproducible broadband noise layer is gated by each cylinder's flow
   pulse and band-limited to 140 Hz–7.5 kHz. This stands in for turbulent jet noise, which a
   filling-and-emptying model cannot resolve. It bypasses the narrow duct resonances because
   radiated turbulence is less strongly filtered than the pressure pulses.
7. **Mix and master.** Exhaust plus 30 % intake, soft saturation, a 20 Hz DC block, and
   normalization to −1 dBFS peak. Short fades avoid clicks at the ends.

The excitation is therefore physical in its timing and firing order, but the transfer functions,
the turbulence level, and the per-cylinder scatter are **voicing assumptions**. They were chosen
to produce a recognisable four-cylinder character, not fitted to a recording.

---

## 3. Assumptions

| Area | Assumption | Basis / limitation |
|---|---|---|
| Source | Valve mass flow from the single-zone cycle model | No port pressure or wave dynamics; the model's smooth lift profile underestimates the sharp blowdown edge |
| Firing order | 1-3-4-2, 180° spacing | Matches the inline-four crank layout |
| Cylinder scatter | Gains 0.93–1.04, delays −0.08 to +0.18 ms | Voicing choice, not measured |
| Exhaust resonances | 180/360/720/1440/2880 Hz, decays 5–25 ms | Assumed; no runner or collector geometry exists yet |
| Comb reflection | 2.2 ms delay, −0.28 feedback | Stand-in for a collector/tailpipe reflection |
| Intake | 30 % of exhaust level, 400–3200 Hz resonances | Assumed; no plenum or runner geometry |
| Turbulence | Band-limited noise at 35 % of the shaped exhaust RMS | Qualitative stand-in; level is not predicted |
| Output | 48 kHz mono, 4 s, −1 dBFS peak | Listening convenience, not a delivery format |
| Radiation | None | No directivity, distance, or room model |

The cycle model itself carries the assumptions and uncertainty documented in
[`../Cycle-Simulation/README.md`](../Cycle-Simulation/README.md). In particular, its torque
result is a first-order estimate with roughly ±5–10 % uncertainty, so the operating point used
for the sound inherits that uncertainty.

---

## 4. What this study does not establish

- **No absolute level.** The WAV is normalized for listening. It says nothing about dB(A) at a
  microphone, at the driver's ear, or at a pass-by position.
- **No validated timbre.** There is no measured recording to compare against. The resonant
  frequencies and the turbulence balance are assumptions.
- **No exhaust or intake geometry.** Runner length, collector volume, muffler transmission loss,
  and airbox resonances are not modelled. Those features dominate a real engine note.
- **No sharp blowdown.** The cycle model's valve lift rises smoothly from the seat, so the
  predicted mass-flow pulse lacks the initial choked-flow spike of a real exhaust event. The
  synthesizer does not invent that spike.
- **No transient or load effects.** The render is steady-speed, wide-open-throttle, and
  cycle-averaged. It does not cover tip-in, overrun, idle stability, or knock.
- **No cycle-to-cycle variation.** The only irregularity is the fixed per-cylinder gain/delay
  scatter and the random turbulence seed.

A credible absolute prediction needs a 1-D wave-action model or CFD for the exhaust pressure at
the valve, the actual runner/collector/muffler geometry, a radiation model, and microphone
calibration against a running engine.

---

## 5. Files and reproducibility

| Item | Path |
|---|---|
| Synthesizer | [`engine_sound.py`](engine_sound.py) |
| Unit tests | [`test_engine_sound.py`](test_engine_sound.py) |
| Cycle model | [`../Cycle-Simulation/cycle_model.py`](../Cycle-Simulation/cycle_model.py) |
| Cycle report | [`../Cycle-Simulation/README.md`](../Cycle-Simulation/README.md) |
| Engine specification | [`../../Specifications/destroyer-01.json`](../../Specifications/destroyer-01.json) |
| Scratch output | `Simulation/Acoustics/output/` (ignored) |

Run the tests with:

```bash
pixi run test-sound
pixi run test          # calculations + cycle + sound
```

The five sound tests check cycle resampling, firing-angle placement, noise reproducibility, a
short render's dominant frequency, and WAV round-trip. They do **not** validate the sound against
a recording.

---

## 6. Next steps

1. Build the exhaust and intake geometry in FreeCAD so runner lengths, collector volume, and
   muffler layout are defined.
2. Run OpenWAM (or a 1-D code) to obtain exhaust port pressure and mass flow at the valve, then
   replace the current flow excitation with the wave-action trace.
3. Add a transmission-loss model for the muffler and a simple radiation model.
4. Record the running engine at a known distance and calibrate the synthesis against measured
   spectra and levels.
5. Only then report an absolute sound level or a validated engine note.
