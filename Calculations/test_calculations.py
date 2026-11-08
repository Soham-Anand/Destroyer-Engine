"""Unit tests for the Destroyer-Engine calculation helpers.

Run with:
    python3 Calculations/test_calculations.py
"""

import math
import unittest

import calculations as calc


class GeometryTests(unittest.TestCase):
    def test_displacement_single_86x86(self):
        self.assertAlmostEqual(
            calc.displacement_single(0.086, 0.086), 0.0004995572142, delta=1e-9
        )

    def test_total_displacement_86x86x4(self):
        self.assertAlmostEqual(
            calc.total_displacement(0.086, 0.086, 4), 0.001998228857, delta=1e-9
        )

    def test_clearance_volume_at_12_5(self):
        vs = calc.displacement_single(0.086, 0.086)
        vc = calc.clearance_volume(vs, 12.5)
        self.assertAlmostEqual(vc, 4.343975776e-05, delta=1e-10)
        self.assertAlmostEqual(calc.compression_ratio(vs, vc), 12.5, delta=1e-9)

    def test_compression_ratio_rejects_invalid_clearance(self):
        with self.assertRaises(ValueError):
            calc.compression_ratio(0.0005, 0.0)

    def test_bore_stroke_ratio(self):
        self.assertAlmostEqual(calc.bore_stroke_ratio(0.086, 0.086), 1.0, delta=1e-12)

    def test_rod_ratios(self):
        self.assertAlmostEqual(
            calc.rod_length_ratio(0.143, 0.086), 1.6627906977, delta=1e-9
        )
        self.assertAlmostEqual(
            calc.crank_radius_ratio(0.143, 0.086), 0.3006993007, delta=1e-9
        )

    def test_mean_piston_speed(self):
        self.assertAlmostEqual(calc.mean_piston_speed(0.086, 7500), 21.5, delta=1e-12)
        self.assertAlmostEqual(calc.mean_piston_speed(0.086, 7000), 20.0666666667, delta=1e-9)


class KinematicsTests(unittest.TestCase):
    def setUp(self):
        self.stroke = 0.086
        self.rod = 0.143
        self.r = self.stroke / 2.0
        self.lam = self.r / self.rod

    def test_piston_position_dead_centres(self):
        self.assertAlmostEqual(calc.piston_position(0.0, self.stroke, self.rod), 0.0, delta=1e-15)
        self.assertAlmostEqual(
            calc.piston_position(math.pi, self.stroke, self.rod), self.stroke, delta=1e-12
        )

    def test_piston_position_at_90_degrees(self):
        expected = self.r + self.rod - math.sqrt(self.rod**2 - self.r**2)
        self.assertAlmostEqual(
            calc.piston_position(math.pi / 2.0, self.stroke, self.rod), expected, delta=1e-12
        )

    def test_piston_velocity_zero_at_dead_centres(self):
        self.assertAlmostEqual(
            calc.piston_velocity(0.0, self.stroke, self.rod, 7500), 0.0, delta=1e-9
        )
        self.assertAlmostEqual(
            calc.piston_velocity(math.pi, self.stroke, self.rod, 7500), 0.0, delta=1e-9
        )

    def test_piston_acceleration_tdc_and_bdc(self):
        omega = 2.0 * math.pi * 7500 / 60.0
        expected_tdc = omega**2 * self.r * (1.0 + self.lam)
        expected_bdc = -omega**2 * self.r * (1.0 - self.lam)
        self.assertAlmostEqual(
            calc.piston_acceleration(0.0, self.stroke, self.rod, 7500),
            expected_tdc,
            delta=1e-6,
        )
        self.assertAlmostEqual(
            calc.piston_acceleration(math.pi, self.stroke, self.rod, 7500),
            expected_bdc,
            delta=1e-6,
        )

    def test_max_piston_acceleration_helper(self):
        omega = 2.0 * math.pi * 7500 / 60.0
        expected = omega**2 * self.r * (1.0 + self.lam)
        self.assertAlmostEqual(
            calc.max_piston_acceleration(self.stroke, self.rod, 7500), expected, delta=1e-6
        )

    def test_max_piston_velocity_is_positive(self):
        value = calc.max_piston_velocity(self.stroke, self.rod, 7500)
        self.assertGreater(value, calc.mean_piston_speed(self.stroke, 7500))
        self.assertLess(value, 40.0)

    def test_rod_angle_at_90_degrees(self):
        self.assertAlmostEqual(
            calc.rod_angle(math.pi / 2.0, self.stroke, self.rod),
            math.asin(self.lam),
            delta=1e-12,
        )


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.vd = calc.total_displacement(0.086, 0.086, 4)

    def test_bmep_torque_round_trip(self):
        bmep = 13.5e5
        torque = calc.torque_from_bmep(bmep, self.vd)
        self.assertAlmostEqual(calc.bmep_from_torque(torque, self.vd), bmep, delta=1e-6)

    def test_power_torque_consistency(self):
        self.assertAlmostEqual(
            calc.power_from_torque(215.0, 4800) / 1000.0, 108.0707873, delta=1e-6
        )
        self.assertAlmostEqual(
            calc.torque_from_power(150000.0, 7000), 204.6277840, delta=1e-6
        )

    def test_bmep_from_power(self):
        bmep = calc.bmep_from_power(150000.0, self.vd, 7000)
        self.assertAlmostEqual(bmep / 1e5, 12.8685389, delta=1e-6)

    def test_specific_power_and_torque(self):
        self.assertAlmostEqual(calc.specific_power_kw_per_l(150000.0, self.vd), 75.0664767, delta=1e-6)
        self.assertAlmostEqual(calc.specific_torque_nm_per_l(215.0, self.vd), 107.5952833, delta=1e-6)

    def test_otto_efficiency(self):
        self.assertAlmostEqual(calc.otto_efficiency(12.5), 0.6358871594, delta=1e-9)


class FuelAirTests(unittest.TestCase):
    def setUp(self):
        self.lhv = 26.8e6
        self.bp = 150000.0
        self.vd = calc.total_displacement(0.086, 0.086, 4)
        self.eta_pp = calc.brake_efficiency_from_bsfc(435.0, self.lhv)
        self.mdot_f = calc.fuel_mass_flow(self.bp, self.eta_pp, self.lhv)

    def test_brake_efficiency_from_bsfc(self):
        self.assertAlmostEqual(self.eta_pp, 0.3088008235, delta=1e-9)

    def test_bsfc_round_trip(self):
        eta = 0.32
        mdot = calc.fuel_mass_flow(self.bp, eta, self.lhv)
        bsfc = calc.bsfc_g_per_kwh(mdot, self.bp)
        self.assertAlmostEqual(bsfc, 419.7761194, delta=1e-6)
        self.assertAlmostEqual(
            calc.brake_efficiency_from_bsfc(bsfc, self.lhv), eta, delta=1e-9
        )

    def test_air_flow_and_volumetric_efficiency(self):
        afr = calc.afr_from_lambda(0.85, 9.0)
        air = calc.air_mass_flow(self.mdot_f, afr)
        self.assertAlmostEqual(air, 0.13865625, delta=1e-9)
        ve = calc.volumetric_efficiency(air, self.vd, 7000, 1.184)
        self.assertAlmostEqual(ve, 1.0046753, delta=1e-6)

    def test_lambda_afr_round_trip(self):
        afr = calc.afr_from_lambda(0.85, 9.0)
        self.assertAlmostEqual(calc.lambda_from_afr(afr, 9.0), 0.85, delta=1e-12)

    def test_fuel_volume_flow(self):
        self.assertAlmostEqual(
            calc.fuel_volume_flow_l_per_h(self.mdot_f, 789.0), 82.6996198, delta=1e-6
        )

    def test_injector_flow(self):
        self.assertAlmostEqual(
            calc.injector_flow_cc_min(self.mdot_f, 789.0, 4, 0.80), 430.7271863, delta=1e-6
        )

    def test_injector_flow_validation(self):
        with self.assertRaises(ValueError):
            calc.injector_flow_cc_min(self.mdot_f, 789.0, 4, 1.5)


class ThermalTests(unittest.TestCase):
    def setUp(self):
        self.eta = calc.brake_efficiency_from_bsfc(435.0, 26.8e6)
        self.q_rejected = calc.rejected_heat(150000.0, self.eta)

    def test_rejected_heat(self):
        self.assertAlmostEqual(self.q_rejected, 335750.0, delta=1e-6)

    def test_heat_shares(self):
        self.assertAlmostEqual(calc.heat_share(150000.0, self.eta, 0.40), 134300.0, delta=1e-6)
        self.assertAlmostEqual(calc.heat_share(150000.0, self.eta, 0.10), 33575.0, delta=1e-6)

    def test_coolant_and_oil_flow(self):
        q_coolant = calc.heat_share(150000.0, self.eta, 0.40)
        q_oil = calc.heat_share(150000.0, self.eta, 0.10)
        self.assertAlmostEqual(
            calc.heat_exchanger_volume_flow_l_per_min(q_coolant, 10.0, 3500.0, 1060.0),
            217.1967655,
            delta=1e-6,
        )
        self.assertAlmostEqual(
            calc.heat_exchanger_volume_flow_l_per_min(q_oil, 20.0, 2000.0, 850.0),
            59.25,
            delta=1e-9,
        )

    def test_heat_exchanger_validation(self):
        with self.assertRaises(ValueError):
            calc.heat_exchanger_mass_flow(1000.0, 0.0, 3500.0)


class LoadTests(unittest.TestCase):
    def test_cylinder_gas_force(self):
        self.assertAlmostEqual(
            calc.cylinder_gas_force(100e5, 0.086), 58088.04816, delta=1e-5
        )

    def test_inertia_force_tdc(self):
        self.assertAlmostEqual(
            calc.inertia_force_tdc(0.60, 0.086, 0.143, 7500), 20700.28741, delta=1e-5
        )


class ValvetrainTests(unittest.TestCase):
    def test_port_area(self):
        self.assertAlmostEqual(calc.port_area(0.033), 0.0008552986, delta=1e-10)

    def test_valve_curtain_area(self):
        self.assertAlmostEqual(
            calc.valve_curtain_area(0.0355, 0.0115), 0.0012825552, delta=1e-10
        )

    def test_lift_to_diameter_ratio(self):
        self.assertAlmostEqual(
            calc.lift_to_diameter_ratio(0.0115, 0.0355), 0.3239436620, delta=1e-9
        )
        self.assertAlmostEqual(
            calc.lift_to_diameter_ratio(0.0105, 0.0305), 0.3442622951, delta=1e-9
        )

    def test_mean_gas_velocity_intake_port(self):
        vs_cyl = calc.displacement_single(0.086, 0.086)
        area = calc.port_area(0.033)
        self.assertAlmostEqual(
            calc.mean_gas_velocity_open_event(vs_cyl, 7000, area, 260),
            94.35032846,
            delta=1e-6,
        )

    def test_mean_gas_velocity_validation(self):
        with self.assertRaises(ValueError):
            calc.mean_gas_velocity_open_event(0.0005, 7000, 0.0, 260)


if __name__ == "__main__":
    unittest.main(verbosity=2)
