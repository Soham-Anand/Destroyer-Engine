"""Unit tests for the Destroyer-01 crank-angle cycle model."""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cantera as ct  # noqa: E402

from cycle_model import (  # noqa: E402
    CycleModel,
    EngineGeometry,
    GasTable,
    IVC_ANGLE_DEG,
    MECH_PATH,
    MixtureState,
    Valve,
)


class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.geom = EngineGeometry(
            bore_m=0.086,
            stroke_m=0.086,
            rod_length_m=0.143,
            compression_ratio=12.5,
            cylinder_count=4,
        )

    def test_tdc_and_bdc_volumes(self):
        self.assertAlmostEqual(self.geom.volume_m3(0.0), self.geom.clearance_volume_m3)
        self.assertAlmostEqual(
            self.geom.volume_m3(180.0),
            self.geom.clearance_volume_m3 + self.geom.swept_volume_m3,
        )
        self.assertAlmostEqual(self.geom.volume_m3(360.0), self.geom.clearance_volume_m3)
        self.assertAlmostEqual(self.geom.volume_m3(720.0), self.geom.clearance_volume_m3)

    def test_compression_ratio(self):
        cr = (self.geom.swept_volume_m3 + self.geom.clearance_volume_m3) / (
            self.geom.clearance_volume_m3
        )
        self.assertAlmostEqual(cr, 12.5, places=10)

    def test_volume_derivative(self):
        for angle in (30.0, 90.0, 150.0, 240.0, 300.0, 400.0, 500.0, 600.0):
            delta = 0.01
            finite_difference = (
                self.geom.volume_m3(angle + delta) - self.geom.volume_m3(angle - delta)
            ) / (2.0 * delta)
            analytic = self.geom.dv_dtheta_m3_per_deg(angle)
            self.assertAlmostEqual(analytic, finite_difference, places=9)


class ValveTests(unittest.TestCase):
    def test_lift_profile(self):
        valve = Valve(
            diameter_m=0.0355,
            max_lift_m=0.0115,
            duration_deg=260.0,
            open_deg=344.0,
            port_diameter_m=0.033,
            valve_count=2,
            cd_max=0.72,
            ramp_deg=15.0,
            profile_exponent=1.2,
        )
        self.assertEqual(valve.lift_m(0.0), 0.0)
        self.assertAlmostEqual(valve.lift_m(valve.seat_open_deg), 0.0, places=12)
        mid = valve.seat_open_deg + valve.seat_duration_deg / 2.0
        self.assertAlmostEqual(valve.lift_m(mid), 0.0115, places=10)
        # The 0.050 in (1.27 mm) point should be close to the specified ramp.
        lift_at_ramp = valve.lift_m(valve.seat_open_deg + valve.ramp_deg)
        self.assertAlmostEqual(lift_at_ramp, 0.00127, delta=0.00012)

    def test_effective_area(self):
        valve = Valve(
            diameter_m=0.0355,
            max_lift_m=0.0115,
            duration_deg=260.0,
            open_deg=344.0,
            port_diameter_m=0.033,
            valve_count=2,
            cd_max=0.72,
            ramp_deg=0.0,
            profile_exponent=2.0,
        )
        self.assertEqual(valve.effective_area_m2(0.0), 0.0)
        mid = valve.open_deg + valve.duration_deg / 2.0
        self.assertGreater(valve.effective_area_m2(mid), 0.0)
        self.assertLessEqual(
            valve.effective_area_m2(mid), valve.port_area_m2()
        )


class FlowTests(unittest.TestCase):
    def test_orifice_choked_flow(self):
        p_up = 5.0e5
        t_up = 500.0
        p_down = 1.0e5
        gamma = 1.4
        r_gas = 287.0
        area = 1.0e-4
        mdot = CycleModel._orifice_mdot(p_up, t_up, p_down, gamma, r_gas, area)
        expected = (
            area
            * p_up
            / math.sqrt(r_gas * t_up)
            * math.sqrt(gamma)
            * (2.0 / (gamma + 1.0)) ** ((gamma + 1.0) / (2.0 * (gamma - 1.0)))
        )
        self.assertAlmostEqual(mdot, expected, places=12)

    def test_orifice_no_flow_and_subsonic(self):
        self.assertEqual(CycleModel._orifice_mdot(1.0e5, 300.0, 1.0e5, 1.4, 287.0, 1e-4), 0.0)
        self.assertEqual(CycleModel._orifice_mdot(1.0e5, 300.0, 1.1e5, 1.4, 287.0, 1e-4), 0.0)
        subsonic = CycleModel._orifice_mdot(2.0e5, 300.0, 1.8e5, 1.4, 287.0, 1e-4)
        choked = CycleModel._orifice_mdot(2.0e5, 300.0, 1.0e5, 1.4, 287.0, 1e-4)
        self.assertGreater(subsonic, 0.0)
        self.assertLess(subsonic, choked)


class CombustionTests(unittest.TestCase):
    def setUp(self):
        self.model = CycleModel(
            cam_ramp_deg=0.0,
            cam_profile_exponent=2.0,
        )

    def test_wiebe_shape(self):
        spark = 96.0
        duration = 60.0
        burned_before, rate_before = self.model._wiebe(90.0, spark, duration)
        self.assertEqual(burned_before, 0.0)
        self.assertEqual(rate_before, 0.0)
        burned_end, rate_end = self.model._wiebe(spark + duration, spark, duration)
        self.assertAlmostEqual(burned_end, 1.0, places=12)
        self.assertEqual(rate_end, 0.0)
        previous = -1.0
        for angle in range(1, 61):
            burned, rate = self.model._wiebe(spark + angle, spark, duration)
            self.assertGreaterEqual(burned, previous)
            self.assertGreaterEqual(rate, 0.0)
            previous = burned

    def test_gas_table_matches_cantera(self):
        gas = ct.Solution(str(MECH_PATH))
        table = GasTable(gas, self.model.y_fresh, t_min=300.0, t_max=3000.0)
        for temperature in (300.0, 800.0, 1500.0, 2500.0):
            gas.TPY = temperature, ct.one_atm, self.model.y_fresh
            self.assertAlmostEqual(table.u(temperature), gas.int_energy_mass, delta=1.0)
            self.assertAlmostEqual(table.cp_at(temperature), gas.cp_mass, delta=1.0)
            self.assertAlmostEqual(table.cv_at(temperature), gas.cv_mass, delta=1.0)
            self.assertAlmostEqual(
                table.cp_at(temperature) - table.cv_at(temperature),
                gas.cp_mass - gas.cv_mass,
                delta=1.0,
            )

    def test_burned_table_is_monotonic(self):
        energy = self.model.burned_table.internal_energy
        self.assertTrue(bool((energy[1:] > energy[:-1]).all()))

    def test_rich_mixture_energy_release(self):
        release = self.model.fresh_table.u(298.15) - self.model.burned_table.u(300.0)
        # Rich ethanol/air at lambda 0.85 releases roughly 2.5 MJ per kg mixture.
        self.assertGreater(release, 2.2e6)
        self.assertLess(release, 3.2e6)


class CycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = CycleModel(cam_ramp_deg=0.0, cam_profile_exponent=2.0)

    def test_full_cycle_sanity(self):
        result = self.model.run_converged(
            rpm=4800.0,
            spark_advance_deg=28.75,
            cycles=5,
            d_phi=1.0,
        )
        self.assertGreater(result["torque_nm"], 180.0)
        self.assertLess(result["torque_nm"], 240.0)
        self.assertGreater(result["volumetric_efficiency"], 0.85)
        self.assertLess(result["volumetric_efficiency"], 1.05)
        self.assertGreater(result["peak_pressure_bar"], 50.0)
        self.assertLess(result["peak_pressure_bar"], 120.0)
        self.assertGreater(result["bsfc_g_per_kwh"], 300.0)
        self.assertLess(result["bsfc_g_per_kwh"], 500.0)
        self.assertGreater(result["residual_fraction"], 0.005)
        self.assertLess(result["residual_fraction"], 0.15)
        self.assertGreater(result["imep_net_bar"], result["bmep_bar"])
        self.assertGreater(result["bmep_bar"], 0.0)
        self.assertGreater(result["imep_gross_bar"], result["imep_net_bar"])
        self.assertGreater(result["pmep_bar"], 0.0)
        self.assertAlmostEqual(
            result["imep_gross_bar"] - result["pmep_bar"],
            result["imep_net_bar"],
            places=9,
        )

    def test_advance_increases_peak_pressure(self):
        low = self.model.run_converged(
            rpm=4800.0, spark_advance_deg=15.0, cycles=4, d_phi=1.0
        )
        high = self.model.run_converged(
            rpm=4800.0, spark_advance_deg=35.0, cycles=4, d_phi=1.0
        )
        self.assertGreater(high["peak_pressure_bar"], low["peak_pressure_bar"])

    def test_ivc_state_mass_accounting(self):
        result = self.model.run_converged(
            rpm=4800.0, spark_advance_deg=25.0, cycles=4, d_phi=1.0
        )
        state: MixtureState = result["initial_state"]  # type: ignore[assignment]
        self.assertGreater(state.m_fresh, 0.0)
        self.assertGreaterEqual(state.m_residual, 0.0)
        self.assertEqual(state.m_burned, 0.0)
        self.assertAlmostEqual(
            state.mass,
            state.m_fresh + state.m_residual + state.m_burned,
            places=12,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
