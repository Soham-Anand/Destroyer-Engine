#!/usr/bin/env python3
"""Pre-generate engine-sound loops for the car simulator.

Run once (or whenever the synthesis changes) to populate the cache directory.
The simulator loads these loops and crossfades between neighbouring RPMs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Simulation" / "Cycle-Simulation"))
sys.path.insert(0, str(ROOT / "Simulation" / "Acoustics"))

from engine_sound import render  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent / "cache"
DEFAULT_RPMS = list(range(1000, 7501, 250))
SAMPLE_RATE = 22050
DURATION_S = 2.0


def generate(rpm: float, d_phi: float = 1.0) -> np.ndarray:
    audio, _spark = render(
        rpm=rpm,
        duration_s=DURATION_S,
        sample_rate=SAMPLE_RATE,
        spark_advance_deg=None,
        d_phi=d_phi,
    )
    return audio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpms", type=float, nargs="*", default=DEFAULT_RPMS)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for rpm in args.rpms:
        path = CACHE_DIR / f"engine-{int(rpm)}.wav"
        if path.exists() and not args.force:
            print(f"  skip {path.name} (exists)")
            continue
        print(f"  rendering {rpm:.0f} rpm ...", flush=True)
        audio = generate(rpm)
        pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767.0)
        wavfile.write(path, SAMPLE_RATE, pcm)
        print(f"    wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
