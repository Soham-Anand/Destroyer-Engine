#!/usr/bin/env python3
"""First-pass engine-sound synthesis for Destroyer-01(A).

This is a qualitative acoustic sketch, not a validated sound prediction.  It
uses the crank-angle cycle model's exhaust and intake valve mass flows as the
excitation, sums four cylinders in the 1-3-4-2 firing order, applies assumed
exhaust/intake transfer functions, and adds a gated broadband turbulence layer.
The result is a 48 kHz mono WAV that is useful for comparing firing order,
speed, and exhaust assumptions.

Usage:
    pixi run python Simulation/Acoustics/engine_sound.py --rpm 4800 --play
    pixi run python Simulation/Acoustics/engine_sound.py --rpm 7000 --plot

The model does not include runner/plenum geometry, muffler transmission loss,
or acoustic radiation.  Those are the next study, after the exhaust layout is
defined.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Simulation" / "Cycle-Simulation"))

from cycle_model import CycleModel  # noqa: E402

SAMPLE_RATE = 48_000
DEFAULT_DURATION_S = 4.0
FIRING_ORDER = (1, 3, 4, 2)
FIRING_ANGLES_DEG = (0.0, 180.0, 360.0, 540.0)
CYLINDER_GAINS = (1.00, 0.99, 1.01, 0.995)
CYLINDER_DELAYS_S = (0.0, 0.00005, -0.00003, 0.00007)


def load_trace(
    model: CycleModel,
    rpm: float,
    spark_advance_deg: float | None = None,
    d_phi: float = 0.5,
) -> tuple[dict[str, list[float]], float]:
    """Run a converged cycle and return its trace plus the spark used."""
    if spark_advance_deg is None:
        best = model.sweep_spark(
            rpm=rpm,
            advances=(20.0, 25.0, 30.0, 35.0, 40.0),
            cycles=4,
            d_phi=d_phi,
        )
        spark = float(best["spark_advance_deg"])
    else:
        spark = float(spark_advance_deg)

    converged = model.run_converged(
        rpm=rpm,
        spark_advance_deg=spark,
        cycles=6,
        d_phi=d_phi,
    )
    result = model.run_cycle(
        converged["initial_state"],  # type: ignore[arg-type]
        rpm=rpm,
        spark_advance_deg=spark,
        d_phi=d_phi,
        store_trace=True,
    )
    return result["trace"], spark  # type: ignore[return-value]


def resample_cycle(
    trace: dict[str, list[float]],
    rpm: float,
    sample_rate: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Resample one 720-degree cycle onto a seamless integer-length buffer."""
    phi = np.asarray(trace["phi"], dtype=float)
    t_cycle = 120.0 / rpm  # 720 crank degrees = two revolutions
    t = phi / 720.0 * t_cycle

    mdot_out = np.asarray(trace["mdot_out"], dtype=float)
    mdot_in = np.asarray(trace["mdot_in"], dtype=float)
    if t[0] > 0.0:
        t = np.concatenate(([0.0], t))
        mdot_out = np.concatenate(([mdot_out[0]], mdot_out))
        mdot_in = np.concatenate(([mdot_in[0]], mdot_in))

    n_cycle = max(2, int(round(t_cycle * sample_rate)))
    t_uniform = np.arange(n_cycle) / sample_rate
    out = np.interp(t_uniform, t, mdot_out)
    intake = np.interp(t_uniform, t, mdot_in)
    return out, intake, n_cycle


def highpass(values: np.ndarray, cutoff_hz: float, sample_rate: int) -> np.ndarray:
    sos = signal.butter(
        2, cutoff_hz, btype="highpass", fs=sample_rate, output="sos"
    )
    return signal.sosfilt(sos, values)


def sum_cylinders(
    cycle: np.ndarray,
    n_cycle: int,
    sample_rate: int,
) -> np.ndarray:
    """Sum four copies of one cylinder's cycle in firing order."""
    total = np.zeros(n_cycle, dtype=float)
    for angle, gain, delay in zip(
        FIRING_ANGLES_DEG, CYLINDER_GAINS, CYLINDER_DELAYS_S
    ):
        shift = int(round(angle / 720.0 * n_cycle + delay * sample_rate))
        total += gain * np.roll(cycle, shift)
    return total


def tiled_cylinder_envelopes(
    cycle: np.ndarray,
    n_total: int,
    sample_rate: int,
) -> list[np.ndarray]:
    """Tile one cylinder's flow cycle and shift each cylinder in firing order."""
    n_cycle = len(cycle)
    repeats = int(np.ceil(n_total / n_cycle))
    base = np.tile(cycle, repeats)[:n_total]
    index = np.arange(n_total)
    envelopes = []
    for angle, gain, delay in zip(
        FIRING_ANGLES_DEG, CYLINDER_GAINS, CYLINDER_DELAYS_S
    ):
        shift = int(round(angle / 720.0 * n_cycle + delay * sample_rate))
        envelopes.append(gain * base[(index - shift) % n_cycle])
    return envelopes


def turbulent_noise(
    envelopes: list[np.ndarray],
    sample_rate: int,
    seed: int,
    band_hz: tuple[float, float] = (160.0, 7500.0),
    exponent: float = 0.8,
) -> np.ndarray:
    """Assumed broadband exhaust noise gated by each cylinder's flow pulse.

    The cycle model predicts valve mass flow, not turbulence.  This component
    is a qualitative stand-in: independent noise per cylinder, shaped to the
    exhaust band and amplitude-modulated by the pulsed flow.  Its level is an
    assumption, not a prediction.
    """
    rng = np.random.default_rng(seed)
    sos = signal.butter(
        2, band_hz, btype="bandpass", fs=sample_rate, output="sos"
    )
    total = np.zeros_like(envelopes[0])
    for envelope in envelopes:
        noise = signal.sosfilt(sos, rng.standard_normal(len(envelope)))
        noise /= max(float(np.std(noise)), 1e-12)
        gate = envelope - float(envelope.min())
        gate /= max(float(gate.max()), 1e-12)
        total += gate**exponent * noise
    return total / max(float(np.std(total)), 1e-12)


def match_level(
    values: np.ndarray, reference: np.ndarray, fraction: float
) -> np.ndarray:
    """Scale values to the given RMS fraction of a reference signal."""
    scale = fraction * float(np.std(reference)) / max(float(np.std(values)), 1e-12)
    return values * scale


def resonant_ir(
    sample_rate: int,
    resonances: tuple[tuple[float, float, float], ...],
    length_s: float = 0.06,
) -> np.ndarray:
    """Build a short decaying-resonance impulse response."""
    n = max(1, int(length_s * sample_rate))
    t = np.arange(n) / sample_rate
    ir = np.zeros(n, dtype=float)
    ir[0] = 1.0
    for frequency, amplitude, decay in resonances:
        ir += amplitude * np.exp(-t / decay) * np.sin(
            2.0 * np.pi * frequency * t
        )
    peak = float(np.max(np.abs(ir)))
    if peak > 0.0:
        ir /= peak
    return ir


def exhaust_transfer(values: np.ndarray, sample_rate: int) -> np.ndarray:
    """Assumed exhaust path: band-limit, resonances, and a duct reflection."""
    ir = resonant_ir(
        sample_rate,
        (
            (180.0, 0.55, 0.025),
            (360.0, 0.40, 0.018),
            (720.0, 0.28, 0.012),
            (1440.0, 0.16, 0.008),
            (2880.0, 0.08, 0.005),
        ),
    )
    shaped = signal.fftconvolve(values, ir, mode="same")
    sos = signal.butter(
        2, [35.0, 6000.0], btype="bandpass", fs=sample_rate, output="sos"
    )
    shaped = signal.sosfilt(sos, shaped)

    # A short feedback comb represents a reflection from the collector or
    # tailpipe.  It creates the characteristic exhaust "box" resonance.
    delay = max(1, int(round(0.0022 * sample_rate)))
    b = np.zeros(delay + 1)
    a = np.zeros(delay + 1)
    b[0] = 1.0
    a[0] = 1.0
    a[delay] = -0.28
    shaped = signal.lfilter(b, a, shaped)
    return shaped


def intake_transfer(values: np.ndarray, sample_rate: int) -> np.ndarray:
    """Assumed intake path: brighter and weaker than the exhaust."""
    ir = resonant_ir(
        sample_rate,
        (
            (400.0, 0.40, 0.012),
            (800.0, 0.35, 0.009),
            (1600.0, 0.25, 0.006),
            (3200.0, 0.12, 0.004),
        ),
    )
    shaped = signal.fftconvolve(values, ir, mode="same")
    sos = signal.butter(
        2, [80.0, 7000.0], btype="bandpass", fs=sample_rate, output="sos"
    )
    return signal.sosfilt(sos, shaped)


def duct_impulse_response(
    sample_rate: int,
    length_m: float = 1.2,
    area_m2: float = 0.0028,
    c_m_s: float = 550.0,
    rho_kg_m3: float = 0.6,
    damping: float = 0.0015,
    duration_s: float = 0.12,
    n_modes: int = 6,
) -> np.ndarray:
    """Impulse response of an open-open exhaust duct (modal expansion).

    The duct is treated as a uniform pipe open at both ends (cylinder volume
    at the valve end, open tailpipe at the far end).  Its natural frequencies
    are f_n = n * c / (2 L), so the resonances are set by the geometry
    rather than by hand-tuned frequencies.  Each mode decays exponentially;
    higher modes decay faster.  This is the linear-acoustic (small-signal)
    solution of the 1-D wave equation for the duct.
    """
    n_steps = max(1, int(round(duration_s * sample_rate)))
    t = np.arange(n_steps) / sample_rate
    f1 = c_m_s / (2.0 * length_m)
    h = np.zeros(n_steps, dtype=float)
    for n in range(1, n_modes + 1):
        frequency = n * f1
        decay = 0.05 / n  # higher modes decay faster
        if decay <= 0.0:
            decay = 0.001
        h += (1.0 / n) * np.exp(-t / decay) * np.sin(
            2.0 * np.pi * frequency * t
        )
    peak = float(np.max(np.abs(h)))
    if peak > 0.0:
        h /= peak
    return h


def duct_transfer(
    values: np.ndarray,
    sample_rate: int,
    length_m: float = 1.2,
    area_m2: float = 0.0028,
    c_m_s: float = 550.0,
    rho_kg_m3: float = 0.6,
    damping: float = 0.0015,
) -> np.ndarray:
    """Filter a source signal through the assumed exhaust duct."""
    h = duct_impulse_response(
        sample_rate,
        length_m=length_m,
        area_m2=area_m2,
        c_m_s=c_m_s,
        rho_kg_m3=rho_kg_m3,
        damping=damping,
    )
    shaped = signal.fftconvolve(values, h, mode="same")
    sos = signal.butter(
        2, [80.0, 6000.0], btype="bandpass", fs=sample_rate, output="sos"
    )
    shaped = signal.sosfilt(sos, shaped)
    # A short feedback comb represents a downstream reflection (muffler or
    # tailpipe tip) that the single open-ended duct does not capture.
    delay = max(1, int(round(0.0022 * sample_rate)))
    b = np.zeros(delay + 1)
    a = np.zeros(delay + 1)
    b[0] = 1.0
    a[0] = 1.0
    a[delay] = -0.22
    shaped = signal.lfilter(b, a, shaped)
    return shaped


def direct_noise_path(values: np.ndarray, sample_rate: int) -> np.ndarray:
    """Band-limit turbulence noise without the narrow duct resonances.

    Turbulent jet noise radiates more directly than the pressure pulses that
    excite the pipe resonances, so this layer bypasses the resonant transfer.
    """
    sos = signal.butter(
        2, [140.0, 7500.0], btype="bandpass", fs=sample_rate, output="sos"
    )
    return signal.sosfilt(sos, values)


def high_shelf(
    values: np.ndarray,
    sample_rate: int,
    gain_db: float = 5.0,
    corner_hz: float = 650.0,
) -> np.ndarray:
    """Lift the presence band with a first-order-style shelving filter."""
    sos = signal.butter(
        2, corner_hz, btype="highpass", fs=sample_rate, output="sos"
    )
    high = signal.sosfilt(sos, values)
    return values + (10.0 ** (gain_db / 20.0) - 1.0) * high


def render(
    rpm: float,
    duration_s: float,
    sample_rate: int,
    spark_advance_deg: float | None = None,
    d_phi: float = 0.5,
    duct_length_m: float = 1.2,
    duct_damping: float = 0.0015,
) -> tuple[np.ndarray, float]:
    """Render a steady-speed engine note."""
    model = CycleModel(cam_ramp_deg=0.0, cam_profile_exponent=2.0)
    trace, spark = load_trace(model, rpm, spark_advance_deg, d_phi=d_phi)
    mdot_out, mdot_in, n_cycle = resample_cycle(trace, rpm, sample_rate)

    # The acoustic source is the unsteady valve flow.  A high-pass removes the
    # mean flow and emphasises the blowdown and closing edges.
    exhaust_cycle = sum_cylinders(
        highpass(mdot_out, 40.0, sample_rate), n_cycle, sample_rate
    )
    intake_cycle = sum_cylinders(
        highpass(mdot_in, 60.0, sample_rate), n_cycle, sample_rate
    )

    # Tile first, then filter, so the IIR/convolution reaches steady state.
    n_total = int(round((duration_s + 0.5) * sample_rate))
    repeats = int(np.ceil(n_total / n_cycle))
    exhaust = np.tile(exhaust_cycle, repeats)[:n_total]
    intake = np.tile(intake_cycle, repeats)[:n_total]

    # Turbulent flow noise is not resolved by a filling-and-emptying model.
    # Add a reproducible, clearly assumed broadband layer gated by each
    # cylinder's exhaust and intake flow pulse.
    exhaust_envelopes = tiled_cylinder_envelopes(
        np.maximum(mdot_out, 0.0), n_total, sample_rate
    )
    intake_envelopes = tiled_cylinder_envelopes(
        np.maximum(mdot_in, 0.0), n_total, sample_rate
    )
    exhaust_noise = turbulent_noise(
        exhaust_envelopes, sample_rate, seed=4800 + int(round(rpm))
    )
    intake_noise = turbulent_noise(
        intake_envelopes,
        sample_rate,
        seed=7000 + int(round(rpm)),
        band_hz=(300.0, 7000.0),
        exponent=1.0,
    )

    exhaust = duct_transfer(
        exhaust, sample_rate, length_m=duct_length_m, damping=duct_damping
    )
    intake = intake_transfer(intake, sample_rate)
    exhaust = high_shelf(exhaust, sample_rate, gain_db=4.0, corner_hz=650.0)
    intake = high_shelf(intake, sample_rate, gain_db=2.0, corner_hz=1000.0)
    # Match the assumed noise layer to the shaped tonal level.  The narrow
    # resonances boost the low-order tones far more than the broadband layer,
    # so the balance has to be set after the transfer function.
    exhaust += match_level(
        direct_noise_path(exhaust_noise, sample_rate), exhaust, 0.35
    )
    intake += match_level(
        direct_noise_path(intake_noise, sample_rate), intake, 0.22
    )

    trim = int(round(0.25 * sample_rate))
    n_out = int(round(duration_s * sample_rate))
    exhaust = exhaust[trim : trim + n_out]
    intake = intake[trim : trim + n_out]

    exhaust /= max(float(np.max(np.abs(exhaust))), 1e-12)
    intake /= max(float(np.max(np.abs(intake))), 1e-12)

    mix = exhaust + 0.30 * intake
    mix = np.tanh(0.80 * mix)
    # Remove the small DC offset left by asymmetric pulses.
    sos = signal.butter(2, 20.0, btype="highpass", fs=sample_rate, output="sos")
    mix = signal.sosfilt(sos, mix)
    mix *= 0.89 / max(float(np.max(np.abs(mix))), 1e-12)

    fade = max(1, int(round(0.03 * sample_rate)))
    mix[:fade] *= np.linspace(0.0, 1.0, fade)
    mix[-fade:] *= np.linspace(1.0, 0.0, fade)
    return mix, spark


def write_wav(audio: np.ndarray, path: Path, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767.0)
    wavfile.write(path, sample_rate, pcm)


def report_spectrum(
    audio: np.ndarray, rpm: float, sample_rate: int
) -> tuple[float, float]:
    frequencies, power = signal.welch(
        audio,
        fs=sample_rate,
        nperseg=16384,
        noverlap=8192,
        nfft=65536,
    )
    mask = (frequencies >= 20.0) & (frequencies <= 1200.0)
    peak_frequency = float(frequencies[mask][np.argmax(power[mask])])
    firing_frequency = rpm / 30.0
    order = peak_frequency / (rpm / 60.0)
    print(
        f"  strongest low-order component: {peak_frequency:.1f} Hz "
        f"({order:.2f} engine order)"
    )
    print(f"  firing frequency: {firing_frequency:.1f} Hz (2.00 order)")
    return peak_frequency, firing_frequency


def write_spectrogram(
    audio: np.ndarray, rpm: float, path: Path, sample_rate: int
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frequencies, times, spectrum = signal.spectrogram(
        audio, fs=sample_rate, nperseg=2048, noverlap=1536
    )
    fig, ax = plt.subplots(figsize=(9.0, 4.2))
    ax.pcolormesh(
        times,
        frequencies,
        10.0 * np.log10(spectrum + 1e-12),
        shading="gouraud",
        cmap="magma",
    )
    ax.set_ylim(0.0, 5000.0)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title(f"Destroyer-01(A) synthesized note — {rpm:.0f} rpm")
    for order in (2.0, 4.0, 6.0, 8.0):
        frequency = order * rpm / 60.0
        if frequency < 5000.0:
            ax.axhline(frequency, color="cyan", linewidth=0.6, alpha=0.6)
            ax.text(
                times[-1] * 0.01,
                frequency + 25.0,
                f"{order:.0f}×",
                color="cyan",
                fontsize=7,
            )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpm", type=float, default=4800.0)
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION_S)
    parser.add_argument(
        "--spark",
        type=float,
        default=None,
        help="Spark advance in degrees BTDC; default runs the MBT search.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="WAV path; default is Simulation/Acoustics/output/engine-<rpm>.wav.",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play the WAV with macOS afplay after writing it.",
    )
    parser.add_argument(
        "--plot",
        action="store_true",
        help="Write a spectrogram PNG next to the WAV.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.rpm <= 0.0 or args.duration <= 0.0:
        raise SystemExit("rpm and duration must be positive")

    output = args.output
    if output is None:
        output = (
            ROOT
            / "Simulation"
            / "Acoustics"
            / "output"
            / f"engine-{args.rpm:.0f}.wav"
        )

    print(
        f"Destroyer-01(A) sound sketch — {args.rpm:.0f} rpm, "
        f"{args.duration:.1f} s, {SAMPLE_RATE} Hz mono"
    )
    print(f"  firing order: {'-'.join(str(c) for c in FIRING_ORDER)}")
    audio, spark = render(
        rpm=args.rpm,
        duration_s=args.duration,
        sample_rate=SAMPLE_RATE,
        spark_advance_deg=args.spark,
    )
    print(f"  spark: {spark:.2f} deg BTDC")
    write_wav(audio, output, SAMPLE_RATE)
    print(f"  wrote {output} ({output.stat().st_size / 1024.0:.0f} KiB)")
    report_spectrum(audio, args.rpm, SAMPLE_RATE)

    if args.plot:
        plot_path = output.with_suffix(".png")
        write_spectrogram(audio, args.rpm, plot_path, SAMPLE_RATE)
        print(f"  wrote {plot_path}")

    if args.play:
        print("  playing...")
        subprocess.run(["afplay", str(output)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
