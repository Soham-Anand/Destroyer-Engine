#!/usr/bin/env python3
"""First-order consistency check of the Destroyer-01 specification.

Usage:
    python3 Calculations/analyse_spec.py

The script reads Specifications/destroyer-01.json, computes the baseline geometry,
performance, fuel, thermal, valvetrain, and load estimates, and checks that the
numbers agree with the declared targets. It exits non-zero if a hard check
fails. All results are [calculated] first-order estimates.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import calculations as calc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "Specifications" / "destroyer-01.json"
GRAVITY = 9.80665


def load_spec(path=SPEC_PATH):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main():
    spec = load_spec()
    arch = spec["architecture"]
    geom = spec["geometry"]
    perf = spec["performance"]
    fuel = spec["fuel"]
    ref = spec["reference_conditions"]
    targets = spec["targets"]
    thermal = spec["thermal"]
    mech = spec["mechanical"]
    valve = spec["valvetrain"]

    bore = geom["bore_m"]
    stroke = geom["stroke_m"]
    n_cyl = geom["cylinder_count"]
    rod = geom["rod_length_m"]
    cr = geom["compression_ratio"]

    vs_cyl = calc.displacement_single(bore, stroke)
    vd = calc.total_displacement(bore, stroke, n_cyl)
    vc = calc.clearance_volume(vs_cyl, cr)

    torque_at_peak_power = calc.torque_from_power(perf["peak_power_w"], perf["peak_power_rpm"])
    power_at_peak_torque = calc.power_from_torque(perf["peak_torque_nm"], perf["peak_torque_rpm"])
    bmep_torque = calc.bmep_from_torque(perf["peak_torque_nm"], vd)
    bmep_power = calc.bmep_from_power(perf["peak_power_w"], vd, perf["peak_power_rpm"])
    specific_power = calc.specific_power_kw_per_l(perf["peak_power_w"], vd)

    sp_torque = calc.mean_piston_speed(stroke, perf["peak_torque_rpm"])
    sp_power = calc.mean_piston_speed(stroke, perf["peak_power_rpm"])
    sp_redline = calc.mean_piston_speed(stroke, perf["redline_rpm"])
    v_max = calc.max_piston_velocity(stroke, rod, perf["redline_rpm"])
    a_max = calc.max_piston_acceleration(stroke, rod, perf["redline_rpm"])

    eta_peak_power = calc.brake_efficiency_from_bsfc(
        targets["peak_power_bsfc_g_per_kwh"], fuel["lhv_j_per_kg"]
    )
    mdot_f = calc.fuel_mass_flow(
        perf["peak_power_w"], eta_peak_power, fuel["lhv_j_per_kg"]
    )
    fuel_l_h = calc.fuel_volume_flow_l_per_h(mdot_f, fuel["density_kg_per_m3"])
    afr_wot = calc.afr_from_lambda(fuel["lambda_wot"], fuel["stoich_afr_mass"])
    mdot_air = calc.air_mass_flow(mdot_f, afr_wot)
    ve = calc.volumetric_efficiency(
        mdot_air, vd, perf["peak_power_rpm"], ref["air_density_kg_per_m3"]
    )
    injector_cc_min = calc.injector_flow_cc_min(
        mdot_f,
        fuel["density_kg_per_m3"],
        fuel["injector_count"],
        fuel["injector_duty_cycle_max"],
    )

    q_fuel = perf["peak_power_w"] / eta_peak_power
    q_rejected = q_fuel - perf["peak_power_w"]
    q_coolant = q_rejected * thermal["coolant_share_of_rejected_heat"]
    q_oil = q_rejected * thermal["oil_share_of_rejected_heat"]
    q_exhaust = q_rejected * thermal["exhaust_share_of_rejected_heat"]
    q_radiation = q_rejected * thermal["radiation_share_of_rejected_heat"]
    coolant_flow = calc.heat_exchanger_volume_flow_l_per_min(
        q_coolant,
        thermal["coolant_delta_t_k"],
        thermal["coolant_cp_j_per_kgk"],
        thermal["coolant_density_kg_per_m3"],
    )
    oil_flow = calc.heat_exchanger_volume_flow_l_per_min(
        q_oil,
        thermal["oil_delta_t_k"],
        thermal["oil_cp_j_per_kgk"],
        thermal["oil_density_kg_per_m3"],
    )

    intake_port_area = calc.port_area(valve["intake_port_diameter_m"])
    intake_port_velocity = calc.mean_gas_velocity_open_event(
        vs_cyl,
        perf["peak_power_rpm"],
        intake_port_area,
        valve["intake_duration_deg"],
    )
    intake_curtain_area = calc.valve_curtain_area(
        valve["intake_valve_diameter_m"], valve["intake_valve_lift_m"]
    )
    intake_curtain_velocity = calc.mean_gas_velocity_open_event(
        vs_cyl,
        perf["peak_power_rpm"],
        intake_curtain_area,
        valve["intake_duration_deg"],
    )
    lift_dia_intake = calc.lift_to_diameter_ratio(
        valve["intake_valve_lift_m"], valve["intake_valve_diameter_m"]
    )
    lift_dia_exhaust = calc.lift_to_diameter_ratio(
        valve["exhaust_valve_lift_m"], valve["exhaust_valve_diameter_m"]
    )

    gas_force = calc.cylinder_gas_force(
        targets["peak_cylinder_pressure_limit_bar"] * 1e5, bore
    )
    inertia_force = calc.inertia_force_tdc(
        mech["reciprocating_mass_kg"], stroke, rod, perf["redline_rpm"]
    )

    print("Destroyer-01 FIRST-ORDER SPECIFICATION CHECK")
    print("=" * 62)
    print(f"Source: {SPEC_PATH.relative_to(ROOT)}")
    print(f"Status: {spec['status']}")
    print()

    print("ARCHITECTURE")
    print(f"  Layout / aspiration      {arch['layout']}, {arch['aspiration']}")
    print(f"  Valvetrain / fuel         {arch['valvetrain']}; {arch['fuel_system']}")
    print()

    print("GEOMETRY")
    print(f"  Bore x stroke             {bore * 1000:.1f} x {stroke * 1000:.1f} mm")
    print(f"  Displacement              {vd * 1e6:.1f} cc")
    print(f"  Swept volume / cylinder   {vs_cyl * 1e6:.1f} cc")
    print(f"  Clearance volume          {vc * 1e6:.2f} cc")
    print(f"  Compression ratio         {cr:.2f} : 1")
    print(f"  Rod length / stroke       {calc.rod_length_ratio(rod, stroke):.3f}")
    print(f"  Crank radius / rod (lam)  {calc.crank_radius_ratio(rod, stroke):.4f}")
    print()

    print("PERFORMANCE")
    print(f"  Peak power                {perf['peak_power_w'] / 1000:.1f} kW @ {perf['peak_power_rpm']} rpm")
    print(f"  Peak torque               {perf['peak_torque_nm']:.1f} N*m @ {perf['peak_torque_rpm']} rpm")
    print(f"  Torque at peak power      {torque_at_peak_power:.1f} N*m")
    print(f"  Power at peak torque      {power_at_peak_torque / 1000:.1f} kW")
    print(f"  BMEP at peak torque       {bmep_torque / 1e5:.2f} bar")
    print(f"  BMEP at peak power        {bmep_power / 1e5:.2f} bar")
    print(f"  Specific power            {specific_power:.1f} kW/L")
    print(f"  Mean piston speed          {sp_torque:.2f} / {sp_power:.2f} / {sp_redline:.2f} m/s")
    print("                            (peak torque / peak power / redline)")
    print(f"  Max piston speed          {v_max:.1f} m/s @ redline")
    print(f"  Max piston acceleration   {a_max:.0f} m/s^2 ({a_max / GRAVITY:.0f} g) @ TDC")
    print()

    print("FUEL / AIR (at peak power)")
    print(f"  WOT lambda / AFR          {fuel['lambda_wot']:.2f} / {afr_wot:.2f} : 1")
    print(f"  Brake efficiency          {eta_peak_power * 100:.1f} %")
    print(f"  Fuel flow                 {mdot_f * 3600:.2f} kg/h ({fuel_l_h:.1f} L/h)")
    print(f"  Air flow                  {mdot_air:.4f} kg/s")
    print(f"  Volumetric efficiency     {ve * 100:.1f} %")
    print(f"  Injector flow required    {injector_cc_min:.0f} cc/min @ {fuel['injector_duty_cycle_max'] * 100:.0f} % duty")
    print()

    print("THERMAL (at peak power)")
    print(f"  Fuel power                {q_fuel / 1000:.1f} kW")
    print(f"  Rejected heat             {q_rejected / 1000:.1f} kW")
    print(f"  Coolant / oil             {q_coolant / 1000:.1f} kW / {q_oil / 1000:.1f} kW")
    print(f"  Exhaust / radiation       {q_exhaust / 1000:.1f} kW / {q_radiation / 1000:.1f} kW")
    print(f"  Coolant flow              {coolant_flow:.0f} L/min at {thermal['coolant_delta_t_k']:.0f} K")
    print(f"  Oil flow                  {oil_flow:.0f} L/min at {thermal['oil_delta_t_k']:.0f} K")
    print()

    print("VALVETRAIN / PORTS (at peak power)")
    print(f"  Intake port velocity      {intake_port_velocity:.1f} m/s mean over event")
    print(f"  Intake curtain velocity   {intake_curtain_velocity:.1f} m/s mean over event")
    print(f"  Lift / diameter           {lift_dia_intake:.3f} intake, {lift_dia_exhaust:.3f} exhaust")
    print()

    print("LOADS")
    print(f"  Gas force @ {targets['peak_cylinder_pressure_limit_bar']:.0f} bar     {gas_force / 1000:.1f} kN")
    print(f"  Inertia force @ redline   {inertia_force / 1000:.1f} kN")
    print()

    checks = []

    def check(label, ok, detail):
        checks.append((label, bool(ok), detail))

    displacement_error = abs(vd * 1e6 - geom["declared_displacement_cc"]) / geom[
        "declared_displacement_cc"
    ]
    check(
        "displacement matches declared value",
        displacement_error <= 0.001,
        f"{vd * 1e6:.2f} cc vs {geom['declared_displacement_cc']:.1f} cc "
        f"({displacement_error * 100:.4f} % error)",
    )
    check(
        "peak-torque BMEP matches target",
        abs(bmep_torque / 1e5 - targets["peak_torque_bmep_bar"]) <= 0.1,
        f"{bmep_torque / 1e5:.2f} bar vs {targets['peak_torque_bmep_bar']:.1f} bar",
    )
    check(
        "peak-power BMEP matches target",
        abs(bmep_power / 1e5 - targets["peak_power_bmep_bar"]) <= 0.1,
        f"{bmep_power / 1e5:.2f} bar vs {targets['peak_power_bmep_bar']:.1f} bar",
    )
    check(
        "specific power matches target",
        abs(specific_power - targets["specific_power_kw_per_l"]) <= 0.1,
        f"{specific_power:.2f} kW/L vs {targets['specific_power_kw_per_l']:.1f} kW/L",
    )
    check(
        "mean piston speed within limit",
        sp_redline <= targets["max_mean_piston_speed_m_per_s"],
        f"{sp_redline:.2f} m/s <= {targets['max_mean_piston_speed_m_per_s']:.1f} m/s",
    )
    check(
        "volumetric efficiency inside target band",
        targets["min_volumetric_efficiency"] <= ve <= targets["max_volumetric_efficiency"],
        f"{ve * 100:.1f} % inside "
        f"{targets['min_volumetric_efficiency'] * 100:.0f}-"
        f"{targets['max_volumetric_efficiency'] * 100:.0f} %",
    )
    check(
        "intake port velocity inside target band",
        targets["min_intake_port_velocity_m_per_s"]
        <= intake_port_velocity
        <= targets["max_intake_port_velocity_m_per_s"],
        f"{intake_port_velocity:.1f} m/s inside "
        f"{targets['min_intake_port_velocity_m_per_s']:.0f}-"
        f"{targets['max_intake_port_velocity_m_per_s']:.0f} m/s",
    )
    check(
        "intake curtain velocity inside target band",
        targets["min_intake_curtain_velocity_m_per_s"]
        <= intake_curtain_velocity
        <= targets["max_intake_curtain_velocity_m_per_s"],
        f"{intake_curtain_velocity:.1f} m/s inside "
        f"{targets['min_intake_curtain_velocity_m_per_s']:.0f}-"
        f"{targets['max_intake_curtain_velocity_m_per_s']:.0f} m/s",
    )
    check(
        "intake lift/diameter inside target band",
        targets["min_lift_to_diameter_ratio"]
        <= lift_dia_intake
        <= targets["max_lift_to_diameter_ratio"],
        f"{lift_dia_intake:.3f}",
    )
    check(
        "exhaust lift/diameter inside target band",
        targets["min_lift_to_diameter_ratio"]
        <= lift_dia_exhaust
        <= targets["max_lift_to_diameter_ratio"],
        f"{lift_dia_exhaust:.3f}",
    )
    heat_share_sum = (
        thermal["coolant_share_of_rejected_heat"]
        + thermal["oil_share_of_rejected_heat"]
        + thermal["exhaust_share_of_rejected_heat"]
        + thermal["radiation_share_of_rejected_heat"]
    )
    check(
        "rejected-heat shares sum to 1.0",
        abs(heat_share_sum - 1.0) <= 1e-9,
        f"sum = {heat_share_sum:.3f}",
    )
    check(
        "injector flow within selected capacity",
        injector_cc_min <= targets["injector_static_flow_target_cc_min"],
        f"{injector_cc_min:.0f} cc/min <= "
        f"{targets['injector_static_flow_target_cc_min']:.0f} cc/min",
    )
    check(
        "gas force within rod compressive limit",
        gas_force / 1000.0 <= targets["rod_compressive_limit_kn"],
        f"{gas_force / 1000:.1f} kN <= {targets['rod_compressive_limit_kn']:.0f} kN",
    )
    check(
        "inertia force within rod tensile limit",
        inertia_force / 1000.0 <= targets["rod_tensile_limit_kn"],
        f"{inertia_force / 1000:.1f} kN <= {targets['rod_tensile_limit_kn']:.0f} kN",
    )
    check(
        "intake duration consistent with valve events",
        valve["intake_open_deg_btdc"] + 180 + valve["intake_close_deg_abdc"]
        == valve["intake_duration_deg"],
        f"{valve['intake_open_deg_btdc']} + 180 + "
        f"{valve['intake_close_deg_abdc']} = {valve['intake_duration_deg']} deg",
    )
    check(
        "exhaust duration consistent with valve events",
        valve["exhaust_open_deg_bbdc"] + 180 + valve["exhaust_close_deg_atdc"]
        == valve["exhaust_duration_deg"],
        f"{valve['exhaust_open_deg_bbdc']} + 180 + "
        f"{valve['exhaust_close_deg_atdc']} = {valve['exhaust_duration_deg']} deg",
    )
    check(
        "WOT lambda inside rich-power band",
        0.80 <= fuel["lambda_wot"] <= 0.95,
        f"lambda = {fuel['lambda_wot']:.2f}",
    )
    check(
        "coolant heat load within sizing target",
        q_coolant / 1000.0 <= targets["coolant_heat_rejection_target_kw"],
        f"{q_coolant / 1000:.1f} kW <= "
        f"{targets['coolant_heat_rejection_target_kw']:.0f} kW",
    )
    check(
        "coolant and oil targets below limits",
        thermal["coolant_outlet_target_c"] < thermal["coolant_max_continuous_c"]
        and thermal["oil_target_c"] < thermal["oil_max_continuous_c"],
        f"coolant {thermal['coolant_outlet_target_c']}/{thermal['coolant_max_continuous_c']} C, "
        f"oil {thermal['oil_target_c']}/{thermal['oil_max_continuous_c']} C",
    )
    check(
        "compression ratio inside concept band",
        10.0 <= cr <= 14.0,
        f"{cr:.2f} : 1",
    )

    print("CONSISTENCY CHECKS")
    for label, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: {detail}")
    print()

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    print(f"RESULT: {passed}/{total} checks passed")
    if passed != total:
        print("One or more checks failed. Review the specification or calculations.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
