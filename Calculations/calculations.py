"""Reusable engine calculation helpers for Destroyer-Engine.

All SI units unless noted. Results are [calculated] first-order estimates from
the stated assumptions, not validated test data. The current baseline lives in
``Specifications/destroyer-01.json``; ``Calculations/analyse_spec.py`` runs the full
specification consistency check.

Sections:
    - geometry
    - piston kinematics
    - performance
    - fuel and air
    - thermal
    - mechanical loads
    - valvetrain and ports
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def displacement_single(bore_m, stroke_m):
    """Swept volume of one cylinder (m^3)."""
    return math.pi / 4.0 * bore_m**2 * stroke_m


def total_displacement(bore_m, stroke_m, n_cyl):
    """Total displacement (m^3)."""
    return displacement_single(bore_m, stroke_m) * n_cyl


def clearance_volume(vs_m3, cr):
    """Clearance volume (m^3) for a target compression ratio."""
    if cr <= 1.0:
        raise ValueError("compression ratio must be greater than 1")
    return vs_m3 / (cr - 1.0)


def compression_ratio(vs_m3, vc_m3):
    """CR = (Vs + Vc)/Vc."""
    if vc_m3 <= 0.0:
        raise ValueError("clearance volume must be positive")
    return (vs_m3 + vc_m3) / vc_m3


def bore_stroke_ratio(bore_m, stroke_m):
    """Bore / stroke (dimensionless)."""
    if stroke_m <= 0.0:
        raise ValueError("stroke must be positive")
    return bore_m / stroke_m


def rod_length_ratio(rod_length_m, stroke_m):
    """Connecting-rod length / stroke (L/S)."""
    if stroke_m <= 0.0:
        raise ValueError("stroke must be positive")
    return rod_length_m / stroke_m


def crank_radius_ratio(rod_length_m, stroke_m):
    """Crank radius / rod length (lambda = r/L), used in piston kinematics."""
    if rod_length_m <= 0.0:
        raise ValueError("rod length must be positive")
    return (stroke_m / 2.0) / rod_length_m


def mean_piston_speed(stroke_m, n_rpm):
    """Mean piston speed (m/s) for a 4-stroke."""
    return 2.0 * stroke_m * n_rpm / 60.0


# ---------------------------------------------------------------------------
# Piston kinematics
# ---------------------------------------------------------------------------


def _omega(n_rpm):
    if n_rpm < 0.0:
        raise ValueError("engine speed cannot be negative")
    return 2.0 * math.pi * n_rpm / 60.0


def piston_position(theta_rad, stroke_m, rod_length_m):
    """Piston position from TDC (m); theta is crank angle from TDC."""
    r = stroke_m / 2.0
    lam = r / rod_length_m
    return r * (1.0 - math.cos(theta_rad)) + rod_length_m * (
        1.0 - math.sqrt(1.0 - (lam * math.sin(theta_rad)) ** 2)
    )


def piston_velocity(theta_rad, stroke_m, rod_length_m, n_rpm):
    """Piston velocity (m/s); positive away from TDC."""
    r = stroke_m / 2.0
    lam = r / rod_length_m
    s = math.sin(theta_rad)
    c = math.cos(theta_rad)
    root = math.sqrt(1.0 - (lam * s) ** 2)
    return _omega(n_rpm) * r * (s + lam * s * c / root)


def piston_acceleration(theta_rad, stroke_m, rod_length_m, n_rpm):
    """Piston acceleration (m/s^2); positive away from TDC."""
    r = stroke_m / 2.0
    lam = r / rod_length_m
    s = math.sin(theta_rad)
    c = math.cos(theta_rad)
    root = math.sqrt(1.0 - (lam * s) ** 2)
    return _omega(n_rpm) ** 2 * r * (
        c + lam * (c * c - s * s) / root + lam**3 * s * s * c * c / root**3
    )


def max_piston_velocity(stroke_m, rod_length_m, n_rpm, samples=3600):
    """Peak piston speed (m/s), sampled over 0-180 deg ATDC."""
    if samples <= 0:
        raise ValueError("samples must be positive")
    return max(
        piston_velocity(math.radians(180.0 * i / samples), stroke_m, rod_length_m, n_rpm)
        for i in range(samples + 1)
    )


def max_piston_acceleration(stroke_m, rod_length_m, n_rpm):
    """Peak positive piston acceleration at TDC (m/s^2)."""
    r = stroke_m / 2.0
    lam = r / rod_length_m
    return _omega(n_rpm) ** 2 * r * (1.0 + lam)


def rod_angle(theta_rad, stroke_m, rod_length_m):
    """Connecting-rod angle from the cylinder axis (rad)."""
    r = stroke_m / 2.0
    lam = r / rod_length_m
    return math.asin(lam * math.sin(theta_rad))


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


def bmep_from_torque(torque_nm, vd_m3):
    """BMEP (Pa) from torque for a 4-stroke: T = BMEP * Vd / (4*pi)."""
    if vd_m3 <= 0.0:
        raise ValueError("displacement must be positive")
    return torque_nm * 4.0 * math.pi / vd_m3


def torque_from_bmep(bmep_pa, vd_m3):
    """Torque (N*m) from BMEP for a 4-stroke."""
    return bmep_pa * vd_m3 / (4.0 * math.pi)


def brake_power_from_bmep(bmep_pa, vd_m3, n_rpm):
    """Brake power (W) for a 4-stroke from BMEP."""
    return bmep_pa * vd_m3 * n_rpm / (2.0 * 60.0)


def brake_power_from_bmeP(bmep_pa, vd_m3, n_rpm):
    """Alias for ``brake_power_from_bmep`` kept for compatibility."""
    return brake_power_from_bmep(bmep_pa, vd_m3, n_rpm)


def bmep_from_power(bp_w, vd_m3, n_rpm):
    """BMEP (Pa) from brake power for a 4-stroke."""
    if vd_m3 <= 0.0:
        raise ValueError("displacement must be positive")
    if n_rpm <= 0.0:
        raise ValueError("engine speed must be positive")
    return bp_w * 2.0 * 60.0 / (vd_m3 * n_rpm)


def power_from_torque(torque_nm, n_rpm):
    """Brake power (W) from torque and engine speed."""
    return torque_nm * 2.0 * math.pi * n_rpm / 60.0


def torque_from_power(bp_w, n_rpm):
    """Torque (N*m) from brake power and engine speed."""
    if n_rpm <= 0.0:
        raise ValueError("engine speed must be positive")
    return bp_w * 60.0 / (2.0 * math.pi * n_rpm)


def specific_power_kw_per_l(bp_w, vd_m3):
    """Specific power (kW/L)."""
    if vd_m3 <= 0.0:
        raise ValueError("displacement must be positive")
    return (bp_w / 1000.0) / (vd_m3 * 1000.0)


def specific_torque_nm_per_l(torque_nm, vd_m3):
    """Specific torque (N*m/L)."""
    if vd_m3 <= 0.0:
        raise ValueError("displacement must be positive")
    return torque_nm / (vd_m3 * 1000.0)


def otto_efficiency(cr, gamma=1.4):
    """Ideal Otto thermal efficiency."""
    if cr <= 0.0:
        raise ValueError("compression ratio must be positive")
    return 1.0 - 1.0 / (cr ** (gamma - 1.0))


# ---------------------------------------------------------------------------
# Fuel and air
# ---------------------------------------------------------------------------


def fuel_mass_flow(bp_w, eta_b, lhv_j_per_kg):
    """Fuel mass flow (kg/s) from brake power, brake efficiency, and LHV."""
    if eta_b <= 0.0:
        raise ValueError("brake efficiency must be positive")
    if lhv_j_per_kg <= 0.0:
        raise ValueError("LHV must be positive")
    return bp_w / (eta_b * lhv_j_per_kg)


def bsfc_g_per_kwh(mdot_f_kg_s, bp_w):
    """BSFC in g/kWh."""
    if bp_w == 0:
        return float("inf")
    return (mdot_f_kg_s * 3600.0 * 1e6) / bp_w


def brake_efficiency_from_bsfc(bsfc_g_per_kwh_value, lhv_j_per_kg):
    """Brake thermal efficiency implied by BSFC and LHV."""
    if bsfc_g_per_kwh_value <= 0.0:
        raise ValueError("BSFC must be positive")
    if lhv_j_per_kg <= 0.0:
        raise ValueError("LHV must be positive")
    return 3.6e9 / (bsfc_g_per_kwh_value * lhv_j_per_kg)


def afr_from_lambda(lambda_value, stoich_afr):
    """Actual air/fuel ratio from lambda and stoichiometric AFR."""
    return lambda_value * stoich_afr


def lambda_from_afr(afr, stoich_afr):
    """Lambda from actual AFR and stoichiometric AFR."""
    if stoich_afr <= 0.0:
        raise ValueError("stoichiometric AFR must be positive")
    return afr / stoich_afr


def air_mass_flow(mdot_f_kg_s, afr):
    """Air mass flow (kg/s) from fuel flow and AFR."""
    return mdot_f_kg_s * afr


def fuel_volume_flow_l_per_h(mdot_f_kg_s, density_kg_per_m3):
    """Fuel volume flow (L/h) from mass flow and density."""
    if density_kg_per_m3 <= 0.0:
        raise ValueError("density must be positive")
    return mdot_f_kg_s / density_kg_per_m3 * 3.6e6


def theoretical_air_flow_m3_s(vd_m3, n_rpm):
    """Ideal 4-stroke intake volume flow at 100 % VE (m^3/s)."""
    return vd_m3 * (n_rpm / 2.0) / 60.0


def volumetric_efficiency(actual_air_kg_s, vd_m3, n_rpm, air_density_kg_per_m3):
    """Volumetric efficiency from measured/estimated air mass flow."""
    if air_density_kg_per_m3 <= 0.0:
        raise ValueError("air density must be positive")
    theoretical = theoretical_air_flow_m3_s(vd_m3, n_rpm) * air_density_kg_per_m3
    if theoretical <= 0.0:
        raise ValueError("theoretical air flow must be positive")
    return actual_air_kg_s / theoretical


def injector_flow_cc_min(
    mdot_f_kg_s, fuel_density_kg_per_m3, n_injectors, max_duty_cycle=0.80
):
    """Required injector static flow (cc/min) at the given max duty cycle."""
    if fuel_density_kg_per_m3 <= 0.0:
        raise ValueError("fuel density must be positive")
    if n_injectors <= 0:
        raise ValueError("injector count must be positive")
    if not 0.0 < max_duty_cycle <= 1.0:
        raise ValueError("duty cycle must be in (0, 1]")
    total_m3_s = mdot_f_kg_s / fuel_density_kg_per_m3
    per_injector_m3_s = total_m3_s / n_injectors / max_duty_cycle
    return per_injector_m3_s * 1e6 * 60.0


def heat_input_rate(mdot_f_kg_s, lhv_j_per_kg):
    """Chemical heat input rate (W)."""
    return mdot_f_kg_s * lhv_j_per_kg


# ---------------------------------------------------------------------------
# Thermal
# ---------------------------------------------------------------------------


def rejected_heat(bp_w, eta_b):
    """Heat rejected to coolant, oil, exhaust, and surroundings (W)."""
    if eta_b <= 0.0 or eta_b >= 1.0:
        raise ValueError("brake efficiency must be in (0, 1)")
    return bp_w * (1.0 - eta_b) / eta_b


def heat_share(bp_w, eta_b, share):
    """Rejected heat allocated to one path (W)."""
    return rejected_heat(bp_w, eta_b) * share


def heat_exchanger_mass_flow(q_w, delta_t_k, cp_j_per_kgk):
    """Mass flow (kg/s) for a heat load and temperature rise."""
    if delta_t_k <= 0.0:
        raise ValueError("temperature difference must be positive")
    if cp_j_per_kgk <= 0.0:
        raise ValueError("specific heat must be positive")
    return q_w / (delta_t_k * cp_j_per_kgk)


def heat_exchanger_volume_flow_l_per_min(q_w, delta_t_k, cp_j_per_kgk, density_kg_per_m3):
    """Volume flow (L/min) for a heat load and temperature rise."""
    if density_kg_per_m3 <= 0.0:
        raise ValueError("density must be positive")
    mdot = heat_exchanger_mass_flow(q_w, delta_t_k, cp_j_per_kgk)
    return mdot / density_kg_per_m3 * 60000.0


# ---------------------------------------------------------------------------
# Mechanical loads
# ---------------------------------------------------------------------------


def cylinder_gas_force(pressure_pa, bore_m):
    """Force on the piston from cylinder pressure (N)."""
    return pressure_pa * math.pi / 4.0 * bore_m**2


def inertia_force_tdc(mass_kg, stroke_m, rod_length_m, n_rpm):
    """Reciprocating inertia force magnitude at TDC (N)."""
    r = stroke_m / 2.0
    lam = r / rod_length_m
    return mass_kg * _omega(n_rpm) ** 2 * r * (1.0 + lam)


# ---------------------------------------------------------------------------
# Valvetrain and ports
# ---------------------------------------------------------------------------


def port_area(diameter_m):
    """Circular port area (m^2)."""
    if diameter_m <= 0.0:
        raise ValueError("port diameter must be positive")
    return math.pi / 4.0 * diameter_m**2


def valve_curtain_area(valve_diameter_m, lift_m):
    """Cylindrical valve-curtain area (m^2), pi * D * L."""
    return math.pi * valve_diameter_m * lift_m


def lift_to_diameter_ratio(lift_m, valve_diameter_m):
    """Valve lift / valve diameter (dimensionless)."""
    if valve_diameter_m <= 0.0:
        raise ValueError("valve diameter must be positive")
    return lift_m / valve_diameter_m


def mean_gas_velocity_open_event(vd_cyl_m3, n_rpm, flow_area_m2, event_duration_deg):
    """Mean gas velocity through an area during one valve event (m/s).

    The cycle-averaged volume flow of one cylinder is divided by the fraction
    of the 720-degree cycle in which the valve is open. This is a sizing
    estimate, not a peak instantaneous velocity.
    """
    if flow_area_m2 <= 0.0:
        raise ValueError("flow area must be positive")
    if not 0.0 < event_duration_deg <= 720.0:
        raise ValueError("event duration must be in (0, 720] degrees")
    q_cycle = vd_cyl_m3 * (n_rpm / 2.0) / 60.0
    q_open = q_cycle / (event_duration_deg / 720.0)
    return q_open / flow_area_m2


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Destroyer-01 baseline geometry. Run analyse_spec.py for the full check.
    B = 0.086
    S = 0.086
    N = 4
    CR = 12.5

    Vd = total_displacement(B, S, N)
    Vs_cyl = displacement_single(B, S)
    Vc = clearance_volume(Vs_cyl, CR)

    print(f"Displacement: {Vd * 1e6:.1f} cc")
    print(f"Swept volume / cylinder: {Vs_cyl * 1e6:.1f} cc")
    print(f"Clearance volume / cylinder: {Vc * 1e6:.2f} cc")
    print(f"Compression ratio: {compression_ratio(Vs_cyl, Vc):.2f}")
    print(f"Mean piston speed @7500 rpm: {mean_piston_speed(S, 7500):.1f} m/s")
    print(f"Peak torque from 13.5 bar BMEP: {torque_from_bmep(13.5e5, Vd):.1f} N*m")
    print(f"Peak power from 215 N*m @4800 rpm: {power_from_torque(215.0, 4800) / 1000:.1f} kW")
    print("Run Calculations/analyse_spec.py for the full specification check.")
