"""Tests for the Destroyer-01 first-pass engine-sound synthesis."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine_sound as es  # noqa: E402


class ResampleTests(unittest.TestCase):
    def test_resample_length_and_finiteness(self):
        phi = np.arange(0.0, 720.5, 0.5)
        flow = 0.05 + 0.05 * np.sin(2.0 * np.pi * phi / 720.0)
        trace = {
            "phi": phi.tolist(),
            "mdot_out": flow.tolist(),
            "mdot_in": flow.tolist(),
        }
        exhaust, intake, n_cycle = es.resample_cycle(trace, 4800.0, 48_000)

        expected = int(round(120.0 / 4800.0 * 48_000))
        self.assertEqual(n_cycle, expected)
        self.assertEqual(len(exhaust), n_cycle)
        self.assertEqual(len(intake), n_cycle)
        self.assertTrue(np.isfinite(exhaust).all())
        self.assertTrue(np.isfinite(intake).all())
        # The cycle boundary should be nearly continuous for a periodic trace.
        self.assertAlmostEqual(exhaust[0], exhaust[-1], delta=0.01)


class FiringOrderTests(unittest.TestCase):
    def test_impulses_land_on_firing_angles(self):
        n_cycle = 720  # one sample per crank degree
        cycle = np.zeros(n_cycle)
        cycle[0] = 1.0
        summed = es.sum_cylinders(cycle, n_cycle, sample_rate=720)

        active = np.flatnonzero(summed > 0.5)
        np.testing.assert_array_equal(active, np.array([0, 180, 360, 540]))

    def test_noise_is_reproducible(self):
        envelope = [np.linspace(0.0, 1.0, 4000) for _ in range(4)]
        first = es.turbulent_noise(envelope, 48_000, seed=11)
        second = es.turbulent_noise(envelope, 48_000, seed=11)
        np.testing.assert_allclose(first, second)
        self.assertTrue(np.isfinite(first).all())


class RenderTests(unittest.TestCase):
    def test_short_render_has_firing_tone(self):
        sample_rate = 24_000
        rpm = 2400.0
        audio, spark = es.render(
            rpm=rpm,
            duration_s=0.4,
            sample_rate=sample_rate,
            spark_advance_deg=25.0,
            d_phi=2.0,
        )

        self.assertEqual(len(audio), int(round(0.4 * sample_rate)))
        self.assertTrue(np.isfinite(audio).all())
        self.assertLessEqual(float(np.max(np.abs(audio))), 0.9)
        self.assertAlmostEqual(spark, 25.0)

        frequencies, power = signal.welch(audio, fs=sample_rate, nperseg=4096)
        mask = (frequencies > 20.0) & (frequencies < 600.0)
        peak = float(frequencies[mask][np.argmax(power[mask])])
        firing_frequency = rpm / 30.0
        self.assertAlmostEqual(peak, firing_frequency, delta=12.0)

    def test_wav_round_trip(self):
        audio = 0.5 * np.sin(2.0 * np.pi * 440.0 * np.arange(4800) / 48_000.0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            es.write_wav(audio, path, 48_000)
            sample_rate, decoded = wavfile.read(path)

        self.assertEqual(sample_rate, 48_000)
        self.assertEqual(len(decoded), len(audio))
        self.assertLessEqual(int(np.max(np.abs(decoded))), 32767)


if __name__ == "__main__":
    unittest.main(verbosity=2)
