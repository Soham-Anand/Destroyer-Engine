#!/usr/bin/env python3
"""Interactive car sound simulator for Destroyer-01(A).

A video-game-style sandbox: arrow keys drive a simple transmission and vehicle
model, the engine note is synthesized from the cycle model's torque curve and
crossfaded between pre-generated RPM loops, and a tachometer/speedometer/waveform/
spectrum are drawn in real time.  No car is rendered -- only instruments.

Controls:
    Up / Down    throttle / brake (hold)
    Left / Right shift down / up
    Space        clutch (hold to disengage)
    R            reset
    Esc / Q      quit
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import numpy as np
import pygame
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Simulation" / "Cycle-Simulation"))
sys.path.insert(0, str(ROOT / "Simulation" / "Acoustics"))

CACHE_DIR = Path(__file__).resolve().parent / "cache"
SAMPLE_RATE = 22050
FPS = 60
WINDOW = (1120, 720)

# Vehicle parameters
MASS_KG = 1200.0
WHEEL_RADIUS_M = 0.30
GEAR_RATIOS = [3.50, 2.10, 1.40, 1.00, 0.75, 0.60]
FINAL_DRIVE = 3.90
DRIVETRAIN_EFF = 0.85
CD = 0.32
FRONTAL_AREA_M2 = 2.0
RHO_AIR = 1.20
CRR = 0.015
MAX_BRAKE_N = 9000.0
IDLE_RPM = 800.0
REDLINE_RPM = 7500.0
MAX_RPM = 8000.0

TORQUE_CSV = ROOT / "Simulation" / "Cycle-Simulation" / "sweep.csv"


def load_torque_map() -> tuple[np.ndarray, np.ndarray]:
    rpms, torques = [], []
    with TORQUE_CSV.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rpms.append(float(row["rpm"]))
            torques.append(float(row["torque_nm"]))
    return np.asarray(rpms), np.asarray(torques)


def torque_at(rpm: float, xs: np.ndarray, ys: np.ndarray) -> float:
    rpm = float(np.clip(rpm, xs[0], xs[-1]))
    return float(np.interp(rpm, xs, ys))


def ensure_cache() -> None:
    if not CACHE_DIR.exists() or not any(CACHE_DIR.glob("engine-*.wav")):
        print("Cache missing -- generating engine loops (this takes ~10 s)...")
        import subprocess

        subprocess.run(
            [sys.executable, str(Path(__file__).parent / "generate_loops.py")],
            check=True,
        )


def load_loops() -> tuple[list[int], list[pygame.mixer.Sound], list[np.ndarray]]:
    rpms = []
    sounds = []
    arrays = []
    for path in sorted(CACHE_DIR.glob("engine-*.wav")):
        rpm = int(path.stem.split("-")[1])
        sr, data = wavfile.read(path)
        if data.dtype != np.int16:
            data = (data * 32767).astype(np.int16)
        arr = data.astype(np.float32) / 32768.0
        sound = pygame.sndarray.make_sound((arr * 32767).astype(np.int16))
        rpms.append(rpm)
        sounds.append(sound)
        arrays.append(arr)
    order = np.argsort(rpms)
    return [rpms[i] for i in order], [sounds[i] for i in order], [arrays[i] for i in order]


def main() -> int:
    pygame.mixer.pre_init(SAMPLE_RATE, -16, 1, 512)
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.set_num_channels(32)

    ensure_cache()
    rpms, sounds, arrays = load_loops()
    n_loops = len(rpms)
    # Play every loop at zero volume so crossfading is click-free.
    channels = []
    for s in sounds:
        ch = s.play(loops=-1)
        ch.set_volume(0.0)
        channels.append(ch)

    torque_xs, torque_ys = load_torque_map()

    screen = pygame.display.set_mode(WINDOW)
    pygame.display.set_caption("Destroyer-01(A) -- Car Sound Simulator")
    clock = pygame.time.Clock()
    font_big = pygame.font.SysFont("Menlo", 48, bold=True)
    font_med = pygame.font.SysFont("Menlo", 26, bold=True)
    font_small = pygame.font.SysFont("Menlo", 16)

    # State
    speed = 0.0  # m/s
    gear = 0  # -1 reverse, 0 neutral, 1..6
    clutch = 1.0  # 1 = engaged
    throttle = 0.0
    brake = 0.0
    rpm = IDLE_RPM
    playhead = 0
    window_len = 1024
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_LEFT:
                    if gear > -1:
                        gear -= 1
                elif event.key == pygame.K_RIGHT:
                    if gear < 6:
                        gear += 1
                elif event.key == pygame.K_r:
                    speed = 0.0
                    rpm = IDLE_RPM
                    gear = 0
                    throttle = 0.0
                    brake = 0.0
                    clutch = 1.0

        keys = pygame.key.get_pressed()
        # Throttle / brake ramping
        if keys[pygame.K_UP]:
            throttle = min(1.0, throttle + 2.5 * dt)
        else:
            throttle = max(0.0, throttle - 1.5 * dt)
        if keys[pygame.K_DOWN]:
            brake = min(1.0, brake + 4.0 * dt)
        else:
            brake = max(0.0, brake - 3.0 * dt)
        # Clutch: hold Space to disengage
        clutch_target = 0.0 if keys[pygame.K_SPACE] else 1.0
        clutch += (clutch_target - clutch) * min(1.0, 8.0 * dt)

        # Engine RPM
        if gear == 0 or clutch < 0.05:
            # Free revving
            target_rpm = IDLE_RPM + throttle * (REDLINE_RPM - IDLE_RPM)
            rpm += (target_rpm - rpm) * min(1.0, 6.0 * dt)
        else:
            gr = GEAR_RATIOS[gear - 1]
            target_rpm = speed * gr * FINAL_DRIVE * 60.0 / (2 * math.pi * WHEEL_RADIUS_M)
            target_rpm = max(IDLE_RPM, target_rpm)
            # clutch slip blends free-rev and locked
            free_rpm = IDLE_RPM + throttle * (REDLINE_RPM - IDLE_RPM)
            rpm = clutch * (target_rpm) + (1 - clutch) * free_rpm
            rpm = max(IDLE_RPM, min(MAX_RPM, rpm))

        # Vehicle dynamics
        if gear != 0 and clutch > 0.05:
            gr = GEAR_RATIOS[gear - 1]
            tq = torque_at(rpm, torque_xs, torque_ys)
            drive_force = tq * gr * FINAL_DRIVE * DRIVETRAIN_EFF * clutch / WHEEL_RADIUS_M
        else:
            drive_force = 0.0
        brake_force = brake * MAX_BRAKE_N
        drag = 0.5 * RHO_AIR * CD * FRONTAL_AREA_M2 * speed * abs(speed)
        rolling = CRR * MASS_KG * 9.81 * (1.0 if speed >= 0 else -1.0)
        if abs(speed) < 0.1:
            rolling = 0.0
        net = drive_force - brake_force - drag - rolling
        # Reverse
        if gear == -1:
            net = -net
        accel = net / MASS_KG
        speed += accel * dt
        speed = max(-5.0, min(60.0, speed))

        rpm = float(np.clip(rpm, IDLE_RPM, MAX_RPM))

        # Audio crossfade weights
        step = rpms[1] - rpms[0]
        weights = []
        for r in rpms:
            w = max(0.0, 1.0 - abs(rpm - r) / step)
            weights.append(w)
        wsum = sum(weights) or 1.0
        weights = [w / wsum for w in weights]
        for i, ch in enumerate(channels):
            ch.set_volume(float(weights[i]))

        # Playhead for visualization
        playhead = (playhead + int(SAMPLE_RATE / FPS * (rpm / 3000.0 + 0.5))) % len(arrays[0])
        # Mix a window for visualization
        mix = np.zeros(window_len, dtype=np.float32)
        for i, arr in enumerate(arrays):
            seg = arr[playhead : playhead + window_len]
            if len(seg) < window_len:
                seg = np.concatenate([seg, arr[: window_len - len(seg)]])
            mix += (weights[i] * seg).astype(np.float32)

        # Spectrum
        spec = np.abs(np.fft.rfft(mix * np.hanning(window_len)))
        spec = spec[:64]

        # Draw
        screen.fill((12, 14, 20))
        # Tachometer
        cx, cy, rad = 200, 200, 130
        pygame.draw.circle(screen, (40, 44, 55), (cx, cy), rad, 6)
        # Redline arc
        # ticks
        for i in range(0, 9):
            a = math.radians(135 + i * 30)
            x1 = cx + (rad - 12) * math.cos(a)
            y1 = cy + (rad - 12) * math.sin(a)
            x2 = cx + rad * math.cos(a)
            y2 = cy + rad * math.sin(a)
            color = (200, 60, 60) if i >= 7 else (180, 185, 200)
            pygame.draw.line(screen, color, (x1, y1), (x2, y2), 3)
        # needle
        ang = math.radians(135 + (rpm / MAX_RPM) * 240)
        nx = cx + (rad - 20) * math.cos(ang)
        ny = cy + (rad - 20) * math.sin(ang)
        pygame.draw.line(screen, (240, 200, 80), (cx, cy), (nx, ny), 4)
        pygame.draw.circle(screen, (240, 200, 80), (cx, cy), 8)
        screen.blit(font_big.render(f"{int(rpm)}", True, (240, 200, 80)), (cx - 40, cy + 40))
        screen.blit(font_small.render("RPM", True, (150, 155, 170)), (cx - 18, cy + 90))

        # Speedometer
        screen.blit(font_big.render(f"{int(speed * 3.6)}", True, (120, 200, 240)), (440, 170))
        screen.blit(font_small.render("km/h", True, (150, 155, 170)), (470, 225))

        # Gear
        glabel = "N" if gear == 0 else ("R" if gear == -1 else str(gear))
        screen.blit(font_big.render(glabel, True, (240, 240, 240)), (780, 170))
        screen.blit(font_small.render("GEAR", True, (150, 155, 170)), (785, 225))

        # Throttle / brake bars
        def bar(x, y, w, h, val, color):
            pygame.draw.rect(screen, (40, 44, 55), (x, y, w, h))
            pygame.draw.rect(screen, color, (x, y + h * (1 - val), w, h * val))

        bar(950, 80, 40, 200, throttle, (80, 200, 120))
        screen.blit(font_small.render("THR", True, (150, 155, 170)), (952, 285))
        bar(1010, 80, 40, 200, brake, (200, 80, 80))
        screen.blit(font_small.render("BRK", True, (150, 155, 170)), (1012, 285))
        # Clutch
        screen.blit(font_small.render(f"clutch {clutch:.2f}", True, (150, 155, 170)), (950, 320))

        # Waveform panel
        wpx, wpy, wpw, wph = 40, 420, 520, 200
        pygame.draw.rect(screen, (20, 24, 32), (wpx, wpy, wpw, wph))
        pygame.draw.rect(screen, (40, 44, 55), (wpx, wpy, wpw, wph), 2)
        mid = wpy + wph // 2
        pts = []
        for i in range(wpw):
            idx = playhead + i * (window_len // wpw)
            idx %= len(mix)
            y = mid - int(mix[idx] * (wph // 2) * 0.9)
            pts.append((wpx + i, y))
        if len(pts) > 1:
            pygame.draw.lines(screen, (120, 200, 240), False, pts, 2)
        screen.blit(font_small.render("waveform", True, (150, 155, 170)), (wpx + 8, wpy + 6))

        # Spectrum panel
        spx, spy, spw, sph = 580, 420, 500, 200
        pygame.draw.rect(screen, (20, 24, 32), (spx, spy, spw, sph))
        pygame.draw.rect(screen, (40, 44, 55), (spx, spy, spw, sph), 2)
        bar_w = spw // len(spec)
        for i, v in enumerate(spec):
            h = int(np.clip(v / (spec.max() + 1e-9) * (sph - 10), 0, sph - 10))
            pygame.draw.rect(screen, (80, 200, 120), (spx + i * bar_w, spy + sph - h, bar_w - 1, h))
        screen.blit(font_small.render("spectrum", True, (150, 155, 170)), (spx + 8, spy + 6))

        # Help line
        screen.blit(
            font_small.render(
                "Up/Down throttle/brake  Left/Right shift  Space clutch  R reset  Esc quit",
                True,
                (120, 125, 140),
            ),
            (40, 690),
        )

        pygame.display.flip()

    for ch in channels:
        ch.stop()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
