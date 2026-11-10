"""Crank-angle filling-and-emptying model for the Destroyer-01(A) engine.

The model is a single-zone, two-composition cycle simulation:

* fresh charge (ethanol + air at the WOT lambda),
* residual / burned gas (equilibrium products of the fresh charge).

Fresh charge and residual are tracked separately so that residual gas acts as an
inert diluent instead of releasing chemical energy a second time.  Combustion is
prescribed by a Wiebe function; the energy release comes from the difference
between the internal energy of the fresh charge and the burned products, both
evaluated with Cantera NASA polynomials.  Heat transfer uses Woschni, friction
uses Chen-Flynn, and valve flow uses a compressible orifice equation.

All calculations are first-order engineering estimates, not test data.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import cantera as ct
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "Specifications" / "destroyer-01.json"
MECH_PATH = Path(__file__).resolve().parent / "mechanisms" / "ethanol-air.yaml"

# Engine cycle reference: the simulation starts at intake-valve closure (IVC)
# and runs one complete 720-degree cycle to the next IVC.  In the conventional
# 0-720 degree frame (0 = TDC firing), IVC is at 604 degrees for this cam.
IVC_ANGLE_DEG = 604.0


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EngineGeometry:
    """Slider-crank geometry for one cylinder."""

    bore_m: float
    stroke_m: float
    rod_length_m: float
    compression_ratio: float
    cylinder_count: int

    @property
    def piston_area_m2(self) -> float:
        return math.pi / 4.0 * self.bore_m**2

    @property
    def swept_volume_m3(self) -> float:
        return self.piston_area_m2 * self.stroke_m

    @property
    def clearance_volume_m3(self) -> float:
        return self.swept_volume_m3 / (self.compression_ratio - 1.0)

    @property
    def displacement_m3(self) -> float:
        return self.swept_volume_m3 * self.cylinder_count

    def volume_m3(self, theta_deg: float) -> float:
        """Cylinder volume at crank angle theta (0 = TDC firing)."""
        r = self.stroke_m / 2.0
        lam = r / self.rod_length_m
        theta = math.radians(theta_deg % 360.0)
        s = math.sin(theta)
        piston_from_tdc = r * (1.0 - math.cos(theta)) + self.rod_length_m * (
            1.0 - math.sqrt(max(0.0, 1.0 - (lam * s) ** 2))
        )
        return self.clearance_volume_m3 + self.piston_area_m2 * piston_from_tdc

    def dv_dtheta_m3_per_deg(self, theta_deg: float) -> float:
        """dVolume/dtheta in m^3 per crank degree."""
        r = self.stroke_m / 2.0
        lam = r / self.rod_length_m
        theta = math.radians(theta_deg % 360.0)
        s = math.sin(theta)
        c = math.cos(theta)
        root = math.sqrt(max(1e-12, 1.0 - (lam * s) ** 2))
        ds_dtheta = r * (s + lam * s * c / root)
        return self.piston_area_m2 * ds_dtheta * math.pi / 180.0


# ---------------------------------------------------------------------------
# Valves
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Valve:
    """One valve family (all intake or all exhaust valves).

    ``duration_deg`` and ``open_deg`` describe the 0.050 in (1.27 mm) event
    from the specification.  The baseline model treats that duration as the
    seat-to-seat event and uses a raised-cosine lift profile.  ``ramp_deg`` and
    ``profile_exponent`` are available for a more realistic cam sensitivity:
    adding ramp moves the seat-to-seat event outside the 0.050 in window, and
    lowering the exponent fills out the low-lift flanks.
    """

    diameter_m: float
    max_lift_m: float
    duration_deg: float
    open_deg: float
    port_diameter_m: float
    valve_count: int
    cd_max: float
    ramp_deg: float = 15.0
    profile_exponent: float = 1.2

    @property
    def seat_duration_deg(self) -> float:
        return self.duration_deg + 2.0 * self.ramp_deg

    @property
    def seat_open_deg(self) -> float:
        return self.open_deg - self.ramp_deg

    def phase_deg(self, theta_deg: float) -> float | None:
        """Position inside the seat-to-seat event, or None when closed."""
        phase = (theta_deg - self.seat_open_deg) % 720.0
        if phase <= self.seat_duration_deg:
            return phase
        return None

    def lift_m(self, theta_deg: float) -> float:
        phase = self.phase_deg(theta_deg)
        if phase is None:
            return 0.0
        return self.max_lift_m * math.sin(
            math.pi * phase / self.seat_duration_deg
        ) ** self.profile_exponent

    def curtain_area_m2(self, theta_deg: float) -> float:
        lift = self.lift_m(theta_deg)
        per_valve = math.pi * self.diameter_m * lift
        return self.valve_count * per_valve

    def port_area_m2(self) -> float:
        return self.valve_count * math.pi / 4.0 * self.port_diameter_m**2

    def discharge_coefficient(self, theta_deg: float) -> float:
        lift = self.lift_m(theta_deg)
        if lift <= 0.0:
            return 0.0
        x = lift / self.diameter_m
        # Smooth rise from the low-lift seat regime to the high-lift plateau.
        return self.cd_max * math.sqrt(x / (x + 0.02))

    def effective_area_m2(self, theta_deg: float) -> float:
        lift = self.lift_m(theta_deg)
        if lift <= 0.0:
            return 0.0
        area = min(self.curtain_area_m2(theta_deg), self.port_area_m2())
        return area * self.discharge_coefficient(theta_deg)


# ---------------------------------------------------------------------------
# Gas properties
# ---------------------------------------------------------------------------


class GasTable:
    """Tabulated ideal-gas properties for one fixed composition."""

    def __init__(
        self,
        gas: ct.Solution,
        mass_fractions: np.ndarray,
        t_min: float = 250.0,
        t_max: float = 4200.0,
        d_t: float = 25.0,
        equilibrium: bool = False,
    ) -> None:
        self.gas = gas
        self.mass_fractions = np.asarray(mass_fractions, dtype=float)
        self.temperature = np.arange(t_min, t_max + d_t, d_t)
        self.internal_energy = np.empty_like(self.temperature)
        self.cv = np.empty_like(self.temperature)
        self.cp = np.empty_like(self.temperature)
        self.gas_constant = np.empty_like(self.temperature)

        for i, temperature in enumerate(self.temperature):
            gas.TPY = temperature, ct.one_atm, self.mass_fractions
            if equilibrium:
                gas.equilibrate("TP")
            self.internal_energy[i] = gas.int_energy_mass
            self.cv[i] = gas.cv_mass
            self.cp[i] = gas.cp_mass
            self.gas_constant[i] = gas.cp_mass - gas.cv_mass

    def _interp(self, values: np.ndarray, temperature: float) -> float:
        return float(
            np.interp(
                min(max(temperature, self.temperature[0]), self.temperature[-1]),
                self.temperature,
                values,
            )
        )

    def u(self, temperature: float) -> float:
        return self._interp(self.internal_energy, temperature)

    def cv_at(self, temperature: float) -> float:
        return self._interp(self.cv, temperature)

    def cp_at(self, temperature: float) -> float:
        return self._interp(self.cp, temperature)

    def r(self, temperature: float) -> float:
        return self._interp(self.gas_constant, temperature)

    def h(self, temperature: float) -> float:
        return self.u(temperature) + self.r(temperature) * temperature


@dataclass
class MixtureState:
    """Instantaneous cylinder contents."""

    m_fresh: float
    m_residual: float
    m_burned: float
    temperature: float

    @property
    def mass(self) -> float:
        return self.m_fresh + self.m_residual + self.m_burned


# ---------------------------------------------------------------------------
# Cycle model
# ---------------------------------------------------------------------------


class CycleModel:
    """Single-cylinder filling-and-emptying model for Destroyer-01(A)."""

    def __init__(
        self,
        spec_path: Path = SPEC_PATH,
        mech_path: Path = MECH_PATH,
        *,
        lambda_wot: float | None = None,
        intake_pressure_pa: float = 101325.0,
        intake_temperature_k: float = 298.15,
        exhaust_pressure_pa: float = 105000.0,
        exhaust_temperature_k: float = 900.0,
        wall_temperature_k: float = 450.0,
        charge_cooling_effectiveness: float = 0.35,
        cd_scale: float = 1.0,
        friction_scale: float = 1.0,
        heat_transfer_scale: float = 1.0,
        wiebe_a: float = 5.0,
        wiebe_m: float = 2.0,
        burn_duration_base_deg: float = 45.0,
        burn_duration_rpm_slope: float = 0.003,
        ignition_delay_deg: float = 5.0,
        cam_ramp_deg: float = 0.0,
        cam_profile_exponent: float = 2.0,
        burned_freeze_temperature_k: float | None = 1200.0,
    ) -> None:
        with Path(spec_path).open("r", encoding="utf-8") as handle:
            spec = json.load(handle)
        self.spec = spec
        geometry = spec["geometry"]
        valvetrain = spec["valvetrain"]
        fuel = spec["fuel"]
        reference = spec["reference_conditions"]

        self.geometry = EngineGeometry(
            bore_m=geometry["bore_m"],
            stroke_m=geometry["stroke_m"],
            rod_length_m=geometry["rod_length_m"],
            compression_ratio=geometry["compression_ratio"],
            cylinder_count=geometry["cylinder_count"],
        )
        self.intake_valve = Valve(
            diameter_m=valvetrain["intake_valve_diameter_m"],
            max_lift_m=valvetrain["intake_valve_lift_m"],
            duration_deg=valvetrain["intake_duration_deg"],
            open_deg=360.0 - valvetrain["intake_open_deg_btdc"],
            port_diameter_m=valvetrain["intake_port_diameter_m"],
            valve_count=2,
            cd_max=0.72 * cd_scale,
            ramp_deg=cam_ramp_deg,
            profile_exponent=cam_profile_exponent,
        )
        self.exhaust_valve = Valve(
            diameter_m=valvetrain["exhaust_valve_diameter_m"],
            max_lift_m=valvetrain["exhaust_valve_lift_m"],
            duration_deg=valvetrain["exhaust_duration_deg"],
            open_deg=180.0 - valvetrain["exhaust_open_deg_bbdc"],
            port_diameter_m=valvetrain["exhaust_port_diameter_m"],
            valve_count=2,
            cd_max=0.68 * cd_scale,
            ramp_deg=cam_ramp_deg,
            profile_exponent=cam_profile_exponent,
        )

        self.lambda_wot = float(fuel["lambda_wot"] if lambda_wot is None else lambda_wot)
        self.stoich_afr = float(fuel["stoich_afr_mass"])
        self.lhv = float(fuel["lhv_j_per_kg"])
        self.fuel_density = float(fuel["density_kg_per_m3"])
        self.latent_heat = float(fuel["latent_heat_vaporization_kj_per_kg"]) * 1000.0
        self.air_fuel_ratio = self.lambda_wot * self.stoich_afr

        self.intake_pressure = float(intake_pressure_pa)
        self.exhaust_pressure = float(exhaust_pressure_pa)
        self.exhaust_temperature = float(exhaust_temperature_k)
        self.wall_temperature = float(wall_temperature_k)
        self.charge_cooling_effectiveness = float(charge_cooling_effectiveness)
        self.friction_scale = float(friction_scale)
        self.heat_transfer_scale = float(heat_transfer_scale)

        self.wiebe_a = float(wiebe_a)
        self.wiebe_m = float(wiebe_m)
        self.burn_duration_base_deg = float(burn_duration_base_deg)
        self.burn_duration_rpm_slope = float(burn_duration_rpm_slope)
        self.ignition_delay_deg = float(ignition_delay_deg)

        self.gas = ct.Solution(str(mech_path))
        self.species_names = self.gas.species_names

        # Fresh charge: ethanol + air at the WOT lambda.
        y_fuel = 1.0 / (1.0 + self.air_fuel_ratio)
        y_air = 1.0 - y_fuel
        self.y_fuel_fresh = y_fuel
        self.y_air_fresh = y_air
        self.y_fresh = np.zeros(self.gas.n_species)
        self.y_fresh[self.species_names.index("C2H5OH")] = y_fuel
        self.y_fresh[self.species_names.index("O2")] = 0.232 * y_air
        self.y_fresh[self.species_names.index("N2")] = 0.768 * y_air

        # Intake charge is cooled by fuel evaporation.  The effectiveness is a
        # calibration parameter; 0.35 is a conservative PFI estimate.
        cp_fresh = self._cp_of(self.y_fresh, 298.15)
        delta_t_evap = y_fuel * self.latent_heat / cp_fresh
        self.intake_temperature = float(intake_temperature_k) - (
            self.charge_cooling_effectiveness * delta_t_evap
        )
        self.reference_air_density = float(reference["air_density_kg_per_m3"])

        # Burned products: constant-volume equilibrium of the fresh charge.
        # Residual gas is assumed to have this same composition.
        self.fresh_table = GasTable(self.gas, self.y_fresh)
        if burned_freeze_temperature_k is not None:
            # Sensitivity case: freeze the equilibrium composition at a chosen
            # exhaust temperature instead of allowing recombination.
            self.gas.TPY = burned_freeze_temperature_k, ct.one_atm, self.y_fresh
            self.gas.equilibrate("TP")
            self.y_burned = self.gas.Y.copy()
            self.adiabatic_flame_temperature = float(self.gas.T)
            self.burned_table = GasTable(
                self.gas, self.y_burned, t_min=300.0, equilibrium=False
            )
        else:
            self.y_burned, self.adiabatic_flame_temperature = self._equilibrium(
                self.y_fresh
            )
            # The burned gas is allowed to re-equilibrate as it cools.  This
            # releases the chemical energy that a frozen high-temperature
            # composition would lock into CO and H2.
            self.burned_table = GasTable(
                self.gas,
                self.y_burned,
                t_min=300.0,
                equilibrium=True,
            )

    # -- composition helpers -------------------------------------------------

    def _cp_of(self, mass_fractions: np.ndarray, temperature: float) -> float:
        self.gas.TPY = temperature, ct.one_atm, mass_fractions
        return float(self.gas.cp_mass)

    def _equilibrium(
        self, mass_fractions: np.ndarray
    ) -> tuple[np.ndarray, float]:
        self.gas.TPY = 298.15, ct.one_atm, mass_fractions
        self.gas.equilibrate("UV")
        return self.gas.Y.copy(), float(self.gas.T)

    # -- valve flow ----------------------------------------------------------

    @staticmethod
    def _orifice_mdot(
        p_upstream: float,
        t_upstream: float,
        p_downstream: float,
        gamma: float,
        gas_constant: float,
        effective_area: float,
    ) -> float:
        """Compressible orifice mass flow (kg/s), positive upstream to downstream."""
        if effective_area <= 0.0 or p_upstream <= 0.0 or t_upstream <= 0.0:
            return 0.0
        pressure_ratio = p_downstream / p_upstream
        if pressure_ratio >= 1.0:
            return 0.0
        pressure_ratio = max(pressure_ratio, 1e-9)
        critical_ratio = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
        if pressure_ratio <= critical_ratio:
            psi = math.sqrt(gamma / (gas_constant * t_upstream)) * (
                2.0 / (gamma + 1.0)
            ) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        else:
            term = pressure_ratio ** (2.0 / gamma) - pressure_ratio ** (
                (gamma + 1.0) / gamma
            )
            if term <= 0.0:
                return 0.0
            psi = math.sqrt(
                2.0
                * gamma
                / ((gamma - 1.0) * gas_constant * t_upstream)
                * term
            )
        return effective_area * p_upstream * psi

    # -- thermodynamics ------------------------------------------------------

    def _mixture_properties(
        self, state: MixtureState
    ) -> tuple[float, float, float, float, float, float]:
        """Return (u, cv, R, p, h, mass) for the cylinder contents."""
        temperature = state.temperature
        u_f = self.fresh_table.u(temperature)
        u_r = self.burned_table.u(temperature)
        u_b = self.burned_table.u(temperature)
        cv_f = self.fresh_table.cv_at(temperature)
        cv_r = self.burned_table.cv_at(temperature)
        cv_b = self.burned_table.cv_at(temperature)
        r_f = self.fresh_table.r(temperature)
        r_r = self.burned_table.r(temperature)
        r_b = self.burned_table.r(temperature)

        mass = state.mass
        if mass <= 0.0:
            return 0.0, 1.0, 287.0, 0.0, 0.0, 0.0
        internal_energy = (
            state.m_fresh * u_f
            + state.m_residual * u_r
            + state.m_burned * u_b
        ) / mass
        cv = (
            state.m_fresh * cv_f
            + state.m_residual * cv_r
            + state.m_burned * cv_b
        ) / mass
        gas_constant = (
            state.m_fresh * r_f
            + state.m_residual * r_r
            + state.m_burned * r_b
        ) / mass
        return internal_energy, cv, gas_constant, 0.0, 0.0, mass

    # -- kinematics / heat transfer -----------------------------------------

    def _burn_duration_deg(self, rpm: float) -> float:
        return self.burn_duration_base_deg + self.burn_duration_rpm_slope * rpm

    def _wiebe(self, phi_deg: float, spark_phi_deg: float, duration_deg: float) -> tuple[float, float]:
        """Return (burned fraction, d(xb)/d(phi)) for the Wiebe function."""
        if phi_deg <= spark_phi_deg:
            return 0.0, 0.0
        z = (phi_deg - spark_phi_deg) / duration_deg
        if z >= 1.0:
            return 1.0, 0.0
        exponent = self.wiebe_m + 1.0
        burned = 1.0 - math.exp(-self.wiebe_a * z**exponent)
        d_burned = (
            self.wiebe_a
            * exponent
            * z**self.wiebe_m
            * math.exp(-self.wiebe_a * z**exponent)
            / duration_deg
        )
        return burned, d_burned

    def _heat_transfer_coefficient(
        self,
        state: MixtureState,
        pressure: float,
        volume: float,
        rpm: float,
        gas_exchange: bool,
    ) -> float:
        bore = self.geometry.bore_m
        mean_piston_speed = 2.0 * self.geometry.stroke_m * rpm / 60.0
        p_kpa = pressure / 1000.0
        if gas_exchange:
            velocity = 6.18 * mean_piston_speed
        else:
            # Motored pressure reference, using the state at the start of the
            # closed period (intake-valve closure).
            p_ivc = getattr(self, "_p_ivc", pressure)
            t_ivc = getattr(self, "_t_ivc", state.temperature)
            v_ivc = getattr(self, "_v_ivc", volume)
            p_mot = p_ivc * (v_ivc / volume) ** 1.35
            velocity = 2.28 * mean_piston_speed + 3.24e-3 * (
                self.geometry.swept_volume_m3
                * t_ivc
                / ((p_ivc / 1000.0) * v_ivc)
            ) * (p_kpa - p_mot / 1000.0)
        velocity = max(velocity, 0.1)
        h_coeff = (
            3.26
            * bore**-0.2
            * max(p_kpa, 0.1) ** 0.8
            * max(state.temperature, 250.0) ** -0.55
            * velocity**0.8
        )
        return h_coeff * self.heat_transfer_scale

    def _heat_transfer_area(self, volume: float) -> float:
        bore = self.geometry.bore_m
        piston_area = math.pi / 4.0 * bore**2
        return 2.0 * piston_area + 4.0 * volume / bore

    # -- derivative ----------------------------------------------------------

    def _derivatives(
        self,
        phi_deg: float,
        state: MixtureState,
        *,
        rpm: float,
        spark_phi_deg: float,
        burn_duration_deg: float,
        m_fresh_ivc: float,
    ) -> tuple[MixtureState, dict[str, float]]:
        engine_angle = (phi_deg + IVC_ANGLE_DEG) % 720.0
        volume = self.geometry.volume_m3(engine_angle)
        dv_dphi = self.geometry.dv_dtheta_m3_per_deg(engine_angle)
        omega_deg_per_s = 6.0 * rpm
        dv_dt = dv_dphi * omega_deg_per_s

        mass = state.mass
        temperature = min(max(state.temperature, 250.0), 4000.0)
        u_f = self.fresh_table.u(temperature)
        u_r = self.burned_table.u(temperature)
        u_b = self.burned_table.u(temperature)
        cv_f = self.fresh_table.cv_at(temperature)
        cv_r = self.burned_table.cv_at(temperature)
        cv_b = self.burned_table.cv_at(temperature)
        r_f = self.fresh_table.r(temperature)
        r_r = self.burned_table.r(temperature)
        r_b = self.burned_table.r(temperature)

        if mass <= 0.0:
            raise ValueError("cylinder mass must be positive")

        internal_energy = (
            state.m_fresh * u_f
            + state.m_residual * u_r
            + state.m_burned * u_b
        ) / mass
        cv = (
            state.m_fresh * cv_f
            + state.m_residual * cv_r
            + state.m_burned * cv_b
        ) / mass
        gas_constant = (
            state.m_fresh * r_f
            + state.m_residual * r_r
            + state.m_burned * r_b
        ) / mass
        pressure = mass * gas_constant * temperature / volume
        enthalpy = internal_energy + gas_constant * temperature

        burned_fraction, d_burned_dphi = self._wiebe(
            phi_deg, spark_phi_deg, burn_duration_deg
        )
        burn_rate = m_fresh_ivc * d_burned_dphi * omega_deg_per_s

        intake_area = self.intake_valve.effective_area_m2(engine_angle)
        exhaust_area = self.exhaust_valve.effective_area_m2(engine_angle)
        gas_exchange = intake_area > 0.0 or exhaust_area > 0.0

        mdot_intake_forward = 0.0
        mdot_exhaust_back = 0.0
        mdot_out = 0.0
        enthalpy_in = 0.0
        internal_energy_in = 0.0

        gamma_intake = self.fresh_table.cp_at(
            self.intake_temperature
        ) / self.fresh_table.cv_at(self.intake_temperature)
        r_intake = self.fresh_table.r(self.intake_temperature)
        gamma_exhaust = self.burned_table.cp_at(
            self.exhaust_temperature
        ) / self.burned_table.cv_at(self.exhaust_temperature)
        r_exhaust = self.burned_table.r(self.exhaust_temperature)
        gamma_mix = (gas_constant + cv) / cv

        if intake_area > 0.0:
            if self.intake_pressure > pressure:
                mdot_intake_forward = self._orifice_mdot(
                    self.intake_pressure,
                    self.intake_temperature,
                    pressure,
                    gamma_intake,
                    r_intake,
                    intake_area,
                )
                if mdot_intake_forward > 0.0:
                    enthalpy_in += mdot_intake_forward * self.fresh_table.h(
                        self.intake_temperature
                    )
                    internal_energy_in += mdot_intake_forward * u_f
            else:
                backflow = self._orifice_mdot(
                    pressure,
                    temperature,
                    self.intake_pressure,
                    gamma_mix,
                    gas_constant,
                    intake_area,
                )
                mdot_out += backflow

        if exhaust_area > 0.0:
            if pressure > self.exhaust_pressure:
                mdot_out += self._orifice_mdot(
                    pressure,
                    temperature,
                    self.exhaust_pressure,
                    gamma_mix,
                    gas_constant,
                    exhaust_area,
                )
            else:
                mdot_exhaust_back = self._orifice_mdot(
                    self.exhaust_pressure,
                    self.exhaust_temperature,
                    pressure,
                    gamma_exhaust,
                    r_exhaust,
                    exhaust_area,
                )
                if mdot_exhaust_back > 0.0:
                    enthalpy_in += mdot_exhaust_back * self.burned_table.h(
                        self.exhaust_temperature
                    )
                    internal_energy_in += mdot_exhaust_back * u_r

        # Heat transfer.
        h_coeff = self._heat_transfer_coefficient(
            state, pressure, volume, rpm, gas_exchange
        )
        heat_loss = (
            h_coeff
            * self._heat_transfer_area(volume)
            * (temperature - self.wall_temperature)
        )

        # Mass derivatives.
        m_fraction = state.m_fresh / mass
        r_fraction = state.m_residual / mass
        b_fraction = state.m_burned / mass
        dm_fresh = (
            mdot_intake_forward
            - mdot_out * m_fraction
            - burn_rate
        )
        dm_residual = mdot_exhaust_back - mdot_out * r_fraction
        dm_burned = burn_rate - mdot_out * b_fraction

        # Energy derivative.  The (u_f - u_b) * burn_rate term is the chemical
        # energy release; no separate LHV term is added.
        numerator = (
            -pressure * dv_dt
            + enthalpy_in
            - internal_energy_in
            - mdot_out * gas_constant * temperature
            + (u_f - u_b) * burn_rate
            - heat_loss
        )
        d_temperature = numerator / (mass * cv)

        # Guard against numerical excursions at the start of combustion.
        d_temperature = max(min(d_temperature, 5.0e6), -5.0e6)
        # The integrator advances crank angle, so convert the per-second
        # derivatives to per-degree rates.
        dphi_dt = omega_deg_per_s
        derivative = MixtureState(
            m_fresh=dm_fresh / dphi_dt,
            m_residual=dm_residual / dphi_dt,
            m_burned=dm_burned / dphi_dt,
            temperature=d_temperature / dphi_dt,
        )
        diagnostics = {
            "pressure": pressure,
            "volume": volume,
            "burned_fraction": burned_fraction,
            "burn_rate": burn_rate,
            "mdot_in": mdot_intake_forward + mdot_exhaust_back,
            "mdot_out": mdot_out,
            "heat_loss": heat_loss,
            "mass": mass,
        }
        return derivative, diagnostics

    # -- cycle integration ---------------------------------------------------

    def run_cycle(
        self,
        state: MixtureState,
        *,
        rpm: float,
        spark_advance_deg: float,
        d_phi: float = 0.5,
        store_trace: bool = False,
    ) -> dict[str, object]:
        """Integrate one 720-degree cycle from IVC to IVC."""
        spark_phi = (720.0 - spark_advance_deg - IVC_ANGLE_DEG) % 720.0
        soc_phi = spark_phi + self.ignition_delay_deg
        burn_duration = self._burn_duration_deg(rpm)
        m_fresh_ivc = state.m_fresh
        v_ivc = self.geometry.volume_m3(IVC_ANGLE_DEG)
        p_ivc = self._pressure_at(state, IVC_ANGLE_DEG)
        t_ivc = state.temperature

        # Cache the IVC reference for Woschni.
        self._p_ivc = p_ivc
        self._t_ivc = t_ivc
        self._v_ivc = v_ivc

        phi = 0.0
        work = 0.0
        work_closed = 0.0
        work_gas_exchange = 0.0
        peak_pressure = 0.0
        trace = {"phi": [], "pressure": [], "temperature": [], "volume": [], "burned": []}

        while phi < 720.0 - 1e-9:
            step = min(d_phi, 720.0 - phi)
            state, diagnostics, work_step, gas_exchange_step = self._rk4_step(
                phi,
                step,
                state,
                rpm=rpm,
                spark_phi_deg=soc_phi,
                burn_duration_deg=burn_duration,
                m_fresh_ivc=m_fresh_ivc,
            )
            work += work_step
            # Gross indicated work covers IVC to BDC (end of the expansion
            # stroke, 296 degrees after IVC).  The pumping loop is BDC to the
            # next IVC.  This keeps blowdown expansion in the gross work and
            # gives a conventional positive pumping loss.
            if phi >= 296.0:
                work_gas_exchange += gas_exchange_step
            else:
                work_closed += gas_exchange_step
            peak_pressure = max(peak_pressure, diagnostics["pressure"])
            end_angle = (phi + step + IVC_ANGLE_DEG) % 720.0
            peak_pressure = max(peak_pressure, self._pressure_at(state, end_angle))
            if store_trace:
                trace["phi"].append(phi + step)
                trace["pressure"].append(diagnostics["pressure"])
                trace["temperature"].append(state.temperature)
                trace["volume"].append(diagnostics["volume"])
                trace["burned"].append(diagnostics["burned_fraction"])
            phi += step

        if state.temperature < 200.0 or state.mass <= 0.0:
            raise RuntimeError("cycle integration diverged")

        imep_net = work / self.geometry.swept_volume_m3
        imep_gross = work_closed / self.geometry.swept_volume_m3
        pmep = -work_gas_exchange / self.geometry.swept_volume_m3
        mean_piston_speed = 2.0 * self.geometry.stroke_m * rpm / 60.0
        fmep_bar = self.friction_scale * (
            0.25
            + 0.004 * (peak_pressure / 1e5)
            + 0.05 * mean_piston_speed
            + 0.0012 * mean_piston_speed**2
        )
        fmep = fmep_bar * 1e5
        bmep = imep_net - fmep
        torque_cylinder = bmep * self.geometry.swept_volume_m3 / (4.0 * math.pi)
        torque = torque_cylinder * self.geometry.cylinder_count
        power = torque * 2.0 * math.pi * rpm / 60.0
        fuel_per_cycle_cylinder = m_fresh_ivc * self.y_fuel_fresh
        fuel_mass_flow = (
            fuel_per_cycle_cylinder
            * self.geometry.cylinder_count
            * rpm
            / 120.0
        )
        bsfc = (
            fuel_mass_flow / power * 3.6e9
            if power > 0.0
            else float("inf")
        )
        air_per_cycle_cylinder = m_fresh_ivc * self.y_air_fresh
        volumetric_efficiency = air_per_cycle_cylinder / (
            self.reference_air_density * self.geometry.swept_volume_m3
        )
        residual_fraction = state.m_residual / state.mass if state.mass > 0 else 0.0
        efficiency = (
            power / (fuel_mass_flow * self.lhv)
            if fuel_mass_flow > 0.0
            else 0.0
        )

        return {
            "rpm": rpm,
            "spark_advance_deg": spark_advance_deg,
            "imep_net_bar": imep_net / 1e5,
            "imep_gross_bar": imep_gross / 1e5,
            "pmep_bar": pmep / 1e5,
            "fmep_bar": fmep_bar,
            "bmep_bar": bmep / 1e5,
            "torque_nm": torque,
            "power_kw": power / 1000.0,
            "volumetric_efficiency": volumetric_efficiency,
            "bsfc_g_per_kwh": bsfc,
            "brake_efficiency": efficiency,
            "peak_pressure_bar": peak_pressure / 1e5,
            "residual_fraction": residual_fraction,
            "fuel_mass_flow_kg_s": fuel_mass_flow,
            "air_mass_flow_kg_s": air_per_cycle_cylinder
            * self.geometry.cylinder_count
            * rpm
            / 120.0,
            "state": state,
            "trace": trace,
        }

    def _pressure_at(self, state: MixtureState, theta_deg: float) -> float:
        _, _, gas_constant, _, _, mass = self._mixture_properties(state)
        volume = self.geometry.volume_m3(theta_deg)
        return mass * gas_constant * state.temperature / volume

    def _rk4_step(
        self,
        phi: float,
        step: float,
        state: MixtureState,
        *,
        rpm: float,
        spark_phi_deg: float,
        burn_duration_deg: float,
        m_fresh_ivc: float,
    ) -> tuple[MixtureState, dict[str, float], float, float]:
        def f(phi_local: float, s: MixtureState) -> tuple[MixtureState, dict[str, float]]:
            return self._derivatives(
                phi_local,
                s,
                rpm=rpm,
                spark_phi_deg=spark_phi_deg,
                burn_duration_deg=burn_duration_deg,
                m_fresh_ivc=m_fresh_ivc,
            )

        k1, diag1 = f(phi, state)
        k2, _ = f(
            phi + step / 2.0,
            self._add(state, k1, step / 2.0),
        )
        k3, _ = f(
            phi + step / 2.0,
            self._add(state, k2, step / 2.0),
        )
        k4, _ = f(phi + step, self._add(state, k3, step))
        new_state = self._add(state, k1, step / 6.0)
        new_state = self._add(new_state, k2, step / 3.0)
        new_state = self._add(new_state, k3, step / 3.0)
        new_state = self._add(new_state, k4, step / 6.0)
        new_state = MixtureState(
            m_fresh=max(new_state.m_fresh, 0.0),
            m_residual=max(new_state.m_residual, 0.0),
            m_burned=max(new_state.m_burned, 0.0),
            temperature=min(max(new_state.temperature, 200.0), 4200.0),
        )

        volume_start = self.geometry.volume_m3((phi + IVC_ANGLE_DEG) % 720.0)
        volume_end = self.geometry.volume_m3((phi + step + IVC_ANGLE_DEG) % 720.0)
        work_step = 0.5 * (diag1["pressure"] + self._pressure_at(new_state, (phi + step + IVC_ANGLE_DEG) % 720.0)) * (volume_end - volume_start)
        return new_state, diag1, work_step, work_step

    @staticmethod
    def _add(state: MixtureState, derivative: MixtureState, scale: float) -> MixtureState:
        return MixtureState(
            m_fresh=state.m_fresh + derivative.m_fresh * scale,
            m_residual=state.m_residual + derivative.m_residual * scale,
            m_burned=state.m_burned + derivative.m_burned * scale,
            temperature=min(max(state.temperature + derivative.temperature * scale, 250.0), 4000.0),
        )

    # -- convergence ---------------------------------------------------------

    def run_converged(
        self,
        *,
        rpm: float,
        spark_advance_deg: float,
        cycles: int = 6,
        d_phi: float = 0.5,
        initial: MixtureState | None = None,
        tolerance: float = 1e-3,
    ) -> dict[str, object]:
        """Run repeated cycles until residual fraction and IVC state converge."""
        if initial is None:
            x_res = 0.06
            t_ivc = 350.0
            v_ivc = self.geometry.volume_m3(IVC_ANGLE_DEG)
            r_mix = (1.0 - x_res) * self.fresh_table.r(t_ivc) + x_res * self.burned_table.r(t_ivc)
            mass = self.intake_pressure * v_ivc / (r_mix * t_ivc)
            initial = MixtureState(
                m_fresh=(1.0 - x_res) * mass,
                m_residual=x_res * mass,
                m_burned=0.0,
                temperature=t_ivc,
            )
        state = initial
        previous_residual = None
        previous_temperature = None
        result = None
        for _ in range(cycles):
            result = self.run_cycle(
                state,
                rpm=rpm,
                spark_advance_deg=spark_advance_deg,
                d_phi=d_phi,
            )
            end_state: MixtureState = result["state"]  # type: ignore[assignment]
            new_m_residual = end_state.m_residual + end_state.m_burned
            new_state = MixtureState(
                m_fresh=end_state.m_fresh,
                m_residual=new_m_residual,
                m_burned=0.0,
                temperature=end_state.temperature,
            )
            residual = new_state.m_residual / new_state.mass
            converged = (
                previous_residual is not None
                and abs(residual - previous_residual) < tolerance
                and previous_temperature is not None
                and abs(new_state.temperature - previous_temperature) < 1.0
            )
            previous_residual = residual
            previous_temperature = new_state.temperature
            state = new_state
            if converged:
                break
        assert result is not None
        result["initial_state"] = state
        result["residual_fraction"] = state.m_residual / state.mass
        return result

    def sweep_spark(
        self,
        *,
        rpm: float,
        advances: tuple[float, ...] = (10, 15, 20, 25, 30, 35, 40, 45),
        cycles: int = 4,
        d_phi: float = 0.5,
    ) -> dict[str, object]:
        """Evaluate several spark advances and return the best-torque result."""
        best = None
        results = []
        initial = None
        for advance in advances:
            result = self.run_converged(
                rpm=rpm,
                spark_advance_deg=advance,
                cycles=cycles,
                d_phi=d_phi,
                initial=initial,
            )
            results.append(result)
            initial = result["initial_state"]  # type: ignore[assignment]
            if best is None or result["torque_nm"] > best["torque_nm"]:  # type: ignore[operator]
                best = result
        assert best is not None

        # Refine around the coarse optimum with a 2.5-degree step.
        coarse_best_advance = float(best["spark_advance_deg"])  # type: ignore[arg-type]
        refined = False
        for advance in (coarse_best_advance - 2.5, coarse_best_advance + 2.5):
            if advance <= 0.0 or advance >= 60.0:
                continue
            if any(abs(advance - r["spark_advance_deg"]) < 1e-6 for r in results):
                continue
            result = self.run_converged(
                rpm=rpm,
                spark_advance_deg=advance,
                cycles=cycles,
                d_phi=d_phi,
                initial=best["initial_state"],  # type: ignore[arg-type]
            )
            results.append(result)
            refined = True
            if result["torque_nm"] > best["torque_nm"]:  # type: ignore[operator]
                best = result
        if refined:
            # One more refinement pass around the new best, at 1.25 degrees.
            best_advance = float(best["spark_advance_deg"])  # type: ignore[arg-type]
            for advance in (best_advance - 1.25, best_advance + 1.25):
                if advance <= 0.0 or advance >= 60.0:
                    continue
                if any(abs(advance - r["spark_advance_deg"]) < 1e-6 for r in results):
                    continue
                result = self.run_converged(
                    rpm=rpm,
                    spark_advance_deg=advance,
                    cycles=cycles,
                    d_phi=d_phi,
                    initial=best["initial_state"],  # type: ignore[arg-type]
                )
                results.append(result)
                if result["torque_nm"] > best["torque_nm"]:  # type: ignore[operator]
                    best = result

        best["spark_sweep"] = [
            {
                "spark_advance_deg": r["spark_advance_deg"],
                "torque_nm": r["torque_nm"],
                "bmep_bar": r["bmep_bar"],
                "peak_pressure_bar": r["peak_pressure_bar"],
            }
            for r in sorted(results, key=lambda item: item["spark_advance_deg"])  # type: ignore[index]
        ]
        return best
