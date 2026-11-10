#!/usr/bin/env python3
"""Run the Destroyer-01(A) crank-angle cycle sweep.

Usage:
    pixi run sweep
    pixi run sweep -- --intake-pressure-kpa 106.325 --output sweep-tuned.csv

The script writes a CSV next to itself and prints a Markdown summary table.
Every value is a first-order ``[simulated]`` estimate, not test data.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cycle_model import CycleModel  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_RPMS = [
    1000,
    1500,
    2000,
    2500,
    3000,
    3500,
    4000,
    4500,
    4800,
    5000,
    5500,
    6000,
    6500,
    7000,
    7500,
]

FIELDS = [
    "rpm",
    "spark_advance_deg",
    "torque_nm",
    "power_kw",
    "bmep_bar",
    "imep_net_bar",
    "imep_gross_bar",
    "pmep_bar",
    "fmep_bar",
    "volumetric_efficiency",
    "bsfc_g_per_kwh",
    "brake_efficiency",
    "peak_pressure_bar",
    "residual_fraction",
    "fuel_mass_flow_kg_s",
    "air_mass_flow_kg_s",
]

TARGET_TORQUE_NM = 215.0
TARGET_TORQUE_RPM = 4800.0
TARGET_POWER_KW = 150.0
TARGET_POWER_RPM = 7000.0
FALLBACK_TORQUE_NM = 205.0
FALLBACK_POWER_KW = 140.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rpm-min", type=float, default=1000.0)
    parser.add_argument("--rpm-max", type=float, default=7500.0)
    parser.add_argument("--rpm-step", type=float, default=500.0)
    parser.add_argument(
        "--rpm",
        type=float,
        nargs="*",
        default=None,
        help="Explicit RPM points; overrides the min/step/max sweep.",
    )
    parser.add_argument(
        "--cycles", type=int, default=4, help="Cycles per spark setting."
    )
    parser.add_argument(
        "--dphi", type=float, default=0.5, help="Crank-angle step in degrees."
    )
    parser.add_argument(
        "--intake-pressure-kpa", type=float, default=101.325
    )
    parser.add_argument("--exhaust-pressure-kpa", type=float, default=105.0)
    parser.add_argument("--charge-cooling", type=float, default=0.35)
    parser.add_argument(
        "--burned-freeze-k",
        type=float,
        default=1200.0,
        help=(
            "Freeze the burned-gas composition at this temperature. "
            "Use 0 or a negative value for the full equilibrium table."
        ),
    )
    parser.add_argument(
        "--output", type=Path, default=HERE / "sweep.csv"
    )
    parser.add_argument(
        "--spark-min", type=float, default=10.0, help="Coarse spark sweep lower bound."
    )
    parser.add_argument(
        "--spark-max", type=float, default=50.0, help="Coarse spark sweep upper bound."
    )
    parser.add_argument(
        "--spark-step", type=float, default=5.0, help="Coarse spark sweep step."
    )
    return parser.parse_args(argv)


def rpm_points(args: argparse.Namespace) -> list[float]:
    if args.rpm:
        points = sorted(set(float(value) for value in args.rpm))
    else:
        points = []
        rpm = args.rpm_min
        while rpm <= args.rpm_max + 1e-9:
            points.append(float(rpm))
            rpm += args.rpm_step
        # Always include the two target speeds so the comparison is direct.
        for target in (TARGET_TORQUE_RPM, TARGET_POWER_RPM):
            if target not in points:
                points.append(target)
        points.sort()
    return points


def spark_grid(args: argparse.Namespace) -> tuple[float, ...]:
    count = int(round((args.spark_max - args.spark_min) / args.spark_step)) + 1
    return tuple(
        args.spark_min + i * args.spark_step for i in range(max(count, 1))
    )


def run_sweep(model: CycleModel, rpms: list[float], args: argparse.Namespace) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    advances = spark_grid(args)
    for rpm in rpms:
        result = model.sweep_spark(
            rpm=rpm,
            advances=advances,
            cycles=args.cycles,
            d_phi=args.dphi,
        )
        row = {field: float(result[field]) for field in FIELDS}  # type: ignore[arg-type]
        rows.append(row)
        print(
            f"{rpm:6.0f} rpm  spark {row['spark_advance_deg']:5.2f} BTDC  "
            f"{row['torque_nm']:6.1f} Nm  {row['power_kw']:6.1f} kW  "
            f"VE {row['volumetric_efficiency']:.3f}  "
            f"BSFC {row['bsfc_g_per_kwh']:.0f}  "
            f"p_max {row['peak_pressure_bar']:.1f} bar",
            flush=True,
        )
    return rows


def write_csv(rows: list[dict[str, float]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {path}")


def nearest(
    rows: list[dict[str, float]], rpm: float
) -> dict[str, float] | None:
    candidate = min(rows, key=lambda row: abs(row["rpm"] - rpm))
    if abs(candidate["rpm"] - rpm) > 0.5:
        return None
    return candidate


def target_verdict(
    value: float | None, target: float, fallback: float
) -> str:
    if value is None:
        return "not swept"
    if value >= target:
        return "target"
    if value >= fallback:
        return "fallback"
    return "short"


def print_summary(rows: list[dict[str, float]]) -> None:
    print("\n## Sweep results\n")
    print(
        "| RPM | Spark | Torque | Power | BMEP | VE | BSFC | Peak p | Residual |"
    )
    print(
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for row in rows:
        print(
            f"| {row['rpm']:.0f} | {row['spark_advance_deg']:.2f} | "
            f"{row['torque_nm']:.1f} | {row['power_kw']:.1f} | "
            f"{row['bmep_bar']:.2f} | {row['volumetric_efficiency']:.3f} | "
            f"{row['bsfc_g_per_kwh']:.0f} | {row['peak_pressure_bar']:.1f} | "
            f"{row['residual_fraction']:.3f} |"
        )

    peak_torque = max(rows, key=lambda row: row["torque_nm"])
    peak_power = max(rows, key=lambda row: row["power_kw"])
    at_torque_rpm = nearest(rows, TARGET_TORQUE_RPM)
    at_power_rpm = nearest(rows, TARGET_POWER_RPM)
    torque_at_target = (
        f"{at_torque_rpm['torque_nm']:.1f} N·m" if at_torque_rpm else "not swept"
    )
    power_at_target = (
        f"{at_power_rpm['power_kw']:.1f} kW" if at_power_rpm else "not swept"
    )

    print("\n## Target comparison\n")
    print("| Metric | Simulated | Target | Fallback | Verdict |")
    print("|---|---:|---:|---:|---|")
    print(
        f"| Peak torque | {peak_torque['torque_nm']:.1f} N·m @ "
        f"{peak_torque['rpm']:.0f} rpm | {TARGET_TORQUE_NM:.1f} N·m @ "
        f"{TARGET_TORQUE_RPM:.0f} rpm | {FALLBACK_TORQUE_NM:.1f} N·m | "
        f"{target_verdict(peak_torque['torque_nm'], TARGET_TORQUE_NM, FALLBACK_TORQUE_NM)} |"
    )
    print(
        f"| Peak power | {peak_power['power_kw']:.1f} kW @ "
        f"{peak_power['rpm']:.0f} rpm | {TARGET_POWER_KW:.1f} kW @ "
        f"{TARGET_POWER_RPM:.0f} rpm | {FALLBACK_POWER_KW:.1f} kW | "
        f"{target_verdict(peak_power['power_kw'], TARGET_POWER_KW, FALLBACK_POWER_KW)} |"
    )
    print(
        f"| Torque at {TARGET_TORQUE_RPM:.0f} rpm | "
        f"{torque_at_target} | {TARGET_TORQUE_NM:.1f} N·m | "
        f"{FALLBACK_TORQUE_NM:.1f} N·m | "
        f"{target_verdict(at_torque_rpm['torque_nm'] if at_torque_rpm else None, TARGET_TORQUE_NM, FALLBACK_TORQUE_NM)} |"
    )
    print(
        f"| Power at {TARGET_POWER_RPM:.0f} rpm | "
        f"{power_at_target} | {TARGET_POWER_KW:.1f} kW | "
        f"{FALLBACK_POWER_KW:.1f} kW | "
        f"{target_verdict(at_power_rpm['power_kw'] if at_power_rpm else None, TARGET_POWER_KW, FALLBACK_POWER_KW)} |"
    )
    print(
        f"| Best BSFC | {min(row['bsfc_g_per_kwh'] for row in rows):.0f} g/kWh | "
        f"410 g/kWh | — | "
        f"{'pass' if min(row['bsfc_g_per_kwh'] for row in rows) <= 410 else 'fail'} |"
    )
    print(
        f"| Peak cylinder pressure | "
        f"{max(row['peak_pressure_bar'] for row in rows):.1f} bar | 100 bar limit | — | "
        f"{'pass' if max(row['peak_pressure_bar'] for row in rows) <= 100 else 'over limit'} |"
    )
    print(
        f"| VE range | {min(row['volumetric_efficiency'] for row in rows):.3f}–"
        f"{max(row['volumetric_efficiency'] for row in rows):.3f} | 0.90–1.10 | — | "
        f"{'pass' if min(row['volumetric_efficiency'] for row in rows) >= 0.90 and max(row['volumetric_efficiency'] for row in rows) <= 1.10 else 'check'} |"
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    freeze_k = args.burned_freeze_k if args.burned_freeze_k > 0.0 else None
    model = CycleModel(
        intake_pressure_pa=args.intake_pressure_kpa * 1000.0,
        exhaust_pressure_pa=args.exhaust_pressure_kpa * 1000.0,
        charge_cooling_effectiveness=args.charge_cooling,
        cam_ramp_deg=0.0,
        cam_profile_exponent=2.0,
        burned_freeze_temperature_k=freeze_k,
    )
    rpms = rpm_points(args)
    print(
        f"Destroyer-01(A) cycle sweep: {len(rpms)} speeds, "
        f"intake {args.intake_pressure_kpa:.1f} kPa, "
        f"charge cooling {args.charge_cooling:.2f}, "
        f"dphi {args.dphi:.2f} deg\n"
    )
    rows = run_sweep(model, rpms, args)
    write_csv(rows, args.output)
    print_summary(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
