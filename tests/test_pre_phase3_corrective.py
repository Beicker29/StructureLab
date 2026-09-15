from __future__ import annotations

import unittest

from app.domain.case_payload import build_validated_case_payload
from app.services.case_service import merge_optimization_defaults
from rc_shear_torsion.design import (
    DemandScenario,
    RegionDemand,
    candidate_to_region_result,
    classify_torsion_state,
    evaluate_candidate,
    optimize_region,
    optimize_region_exhaustive,
    select_longitudinal_independent,
    spacing_domain_for_region,
)
from rc_shear_torsion.models import (
    DEFAULT_STIRRUP_SPACING_MIN_MM,
    DEFAULT_STIRRUP_SPACING_STEP_MM,
    LEGACY_FIXED_STIRRUP_SPACING_MM,
    OptimizationConfig,
    VariablesConfig,
)
from rc_shear_torsion.span_coupled import optimize_span_coupled
from rc_shear_torsion.tolerances import torsion_zero_tolerance
from rc_shear_torsion.results_model import to_canonical_region_result


def _scenario(
    *,
    v_rebar: float,
    t_transverse: float,
    t_longitudinal: float,
    station_mm: float = 0.0,
) -> DemandScenario:
    return DemandScenario(
        source="SEISMIC",
        station_mm=station_mm,
        x_relative=0.0,
        region_id="R2",
        v_rebar_mm2_per_m=v_rebar,
        t_transverse_mm2_per_m=t_transverse,
        t_longitudinal_mm2=t_longitudinal,
        torsion_state=classify_torsion_state(t_transverse, t_longitudinal),
        source_row=2,
    )


def _region(
    *scenarios: DemandScenario,
    detailing: str = "DMI",
    region_type: str = "NC",
    width_mm: float = 150.0,
    height_mm: float = 750.0,
    d_mm: float = 675.0,
    db_bar: str = "#6",
    min_branches: int | None = 2,
    region_length_mm: float = 3000.0,
    d_source: str | None = None,
    d_ratio: float | None = None,
) -> RegionDemand:
    return RegionDemand(
        beam_id="B389",
        span_id="389",
        region_id="R2",
        region_type=region_type,  # type: ignore[arg-type]
        beam_detailing=detailing,  # type: ignore[arg-type]
        d_mm=d_mm,
        db_bar=db_bar,
        min_branches=min_branches,
        width_mm=width_mm,
        height_mm=height_mm,
        cover_side_mm=40.0,
        cover_top_mm=40.0,
        cover_bottom_mm=40.0,
        scenarios=tuple(scenarios),
        fc_mpa=28.0,
        fy_mpa=420.0,
        region_length_mm=region_length_mm,
        d_source=d_source,  # type: ignore[arg-type]
        d_ratio=d_ratio,
    )


def _variables(*, spacings: list[int]) -> VariablesConfig:
    return VariablesConfig(
        E_bars=["#3"],
        G_bars=["#3"],
        G_counts=[0],
        stirrup_spacing_mm=spacings,
        longitudinal_bars=["#4", "#5"],
        longitudinal_bar_counts=[2, 4],
    )


class PrePhase3CorrectiveTests(unittest.TestCase):
    def test_code_rule_controls_when_it_is_the_smallest_technical_limit(self) -> None:
        candidate = evaluate_candidate(
            _region(_scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0), detailing="DMO"),
            e_bar="#3",
            g_bar="#3",
            g_count=0,
            spacing_mm=330,
            long_bar="",
            long_count=0,
            check_longitudinal=True,
        )

        self.assertEqual(candidate.status, "ok")
        self.assertEqual(candidate.controlling_limit, "ACI318_25_18_4_2_5_D_OVER_2")
        self.assertEqual(candidate.governing_code_rule, "ACI318_25_18_4_2_5_D_OVER_2")
        self.assertEqual(candidate.governing_code_limit_mm, 337.5)
        self.assertIsNone(candidate.governing_demand_check)

        checks = {check.rule_id: check for check in candidate.rule_checks}
        general = checks["ACI318_25_9_7_6_2_2_LOW_D_LIMIT"]
        seismic = checks["ACI318_25_18_4_2_5_D_OVER_2"]
        self.assertEqual(general.status.value, "PASS")
        self.assertEqual(seismic.status.value, "PASS")
        self.assertEqual(general.required_value, 337.5)
        self.assertEqual(seismic.required_value, 337.5)

    def test_shear_demand_controls_below_every_aci_limit(self) -> None:
        region = _region(_scenario(v_rebar=1000.0, t_transverse=0.0, t_longitudinal=0.0))
        candidate = evaluate_candidate(
            region,
            e_bar="#3",
            g_bar="#3",
            g_count=0,
            spacing_mm=140,
            long_bar="",
            long_count=0,
            check_longitudinal=True,
        )

        self.assertEqual(candidate.status, "ok")
        self.assertEqual(candidate.controlling_limit, "SHEAR_DEMAND")
        self.assertEqual(candidate.governing_demand_check, "SHEAR_DEMAND")
        self.assertEqual(candidate.governing_demand_spacing_limit_mm, 142.0)
        self.assertGreater(candidate.governing_code_limit_mm or 0.0, 142.0)
        self.assertNotEqual(candidate.controlling_limit, "d/2")

        dynamic_variables = VariablesConfig(
            E_bars=["#3"],
            G_bars=["#3"],
            G_counts=[0],
            longitudinal_bars=["#4"],
            longitudinal_bar_counts=[2],
        )
        domain = spacing_domain_for_region(region, dynamic_variables, [0])
        selected = optimize_region_exhaustive(region, dynamic_variables).selected
        self.assertEqual(domain[-1], 140)
        self.assertEqual(selected.spacing_mm, 140)
        self.assertEqual(selected.controlling_limit, "SHEAR_DEMAND")

    def test_combined_shear_torsion_demand_is_identified(self) -> None:
        candidate = evaluate_candidate(
            _region(
                _scenario(v_rebar=500.0, t_transverse=300.0, t_longitudinal=200.0),
                width_mm=600.0,
                height_mm=1200.0,
                d_mm=1080.0,
            ),
            e_bar="#4",
            g_bar="#3",
            g_count=0,
            spacing_mm=230,
            long_bar="#4",
            long_count=2,
            check_longitudinal=True,
        )

        self.assertEqual(candidate.status, "ok")
        self.assertEqual(candidate.controlling_limit, "SHEAR_TORSION_COMBINED_DEMAND")
        self.assertEqual(candidate.governing_demand_check, "SHEAR_TORSION_COMBINED_DEMAND")
        self.assertAlmostEqual(candidate.governing_demand_spacing_limit_mm or 0.0, 258000.0 / 1100.0)

    def test_150_by_750_geometry_uses_d_ratio_and_is_not_stopped_at_190(self) -> None:
        defaults = merge_optimization_defaults(None)
        variables = VariablesConfig.model_validate(defaults["variables"])
        region = _region(
            _scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0),
            detailing="DMO",
        )

        outcome = optimize_region_exhaustive(region, variables)

        self.assertEqual(region.height_mm, 750.0)
        self.assertEqual(region.d_mm, 675.0)
        self.assertEqual((region.d_mm or 0.0) / 2.0, 337.5)
        self.assertEqual(outcome.selected.spacing_mm, 330)
        self.assertGreater(outcome.selected.spacing_mm, 190)
        self.assertIsNone(outcome.selected.long_bar)
        self.assertEqual(outcome.selected.long_count, 0)
        self.assertEqual(outcome.selected.long_provided, 0.0)

        ga_outcome = optimize_region(
            region,
            OptimizationConfig.model_validate(defaults),
        )
        self.assertEqual(ga_outcome.selected.spacing_mm, 330)
        self.assertEqual(ga_outcome.selected.controlling_limit, outcome.selected.controlling_limit)

    def test_form_default_effective_depth_preserves_approximation_source(self) -> None:
        payload = build_validated_case_payload(
            case_name="d trace",
            sheet_name="Conc Bm Sum - ACI 318-08",
            units_rebar_per_length="mm2/m",
            beam_id="B389",
            detailing="DMO",
            cover_side_mm=40.0,
            cover_top_mm=40.0,
            cover_bottom_mm=40.0,
            fc_mpa=28.0,
            fy_mpa=420.0,
            width_mm=150.0,
            height_mm=750.0,
            d_mm=675.0,
            d_ratio_default=0.9,
            db_bar="#6",
            min_branches_c=4,
            min_branches_nc=2,
            region_c_ratio=0.2,
            span_pairs=[{"id": "389", "seismic": "389", "gravity": "389"}],
            span_layout=None,
            optimization_payload=merge_optimization_defaults(None),
        )

        regions = payload["beams"][0]["spans"][0]["regions"]
        self.assertTrue(all(region["d_mm"] == 675.0 for region in regions))
        self.assertTrue(all(region["d_source"] == "DEFAULT_RATIO" for region in regions))
        self.assertTrue(all(region["d_ratio"] == 0.9 for region in regions))

        demand = _region(
            _scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0),
            detailing="DMO",
            d_source="DEFAULT_RATIO",
            d_ratio=0.9,
        )
        outcome = optimize_region_exhaustive(
            demand,
            VariablesConfig.model_validate(merge_optimization_defaults(None)["variables"]),
        )
        result = candidate_to_region_result(
            demand,
            outcome.selected,
            method=outcome.method,
            evaluated_candidates=outcome.evaluated_candidates,
            feasible_candidates=outcome.feasible_candidates,
        )
        canonical = to_canonical_region_result(result)
        self.assertEqual((canonical.d_mm, canonical.d_source, canonical.d_ratio), (675.0, "DEFAULT_RATIO", 0.9))

    def test_default_spacing_domain_is_dynamic_and_has_no_200_mm_ceiling(self) -> None:
        defaults = merge_optimization_defaults(None)
        variables = VariablesConfig.model_validate(defaults["variables"])
        self.assertEqual(DEFAULT_STIRRUP_SPACING_MIN_MM, 70)
        self.assertEqual(DEFAULT_STIRRUP_SPACING_STEP_MM, 10)
        self.assertIsNone(variables.stirrup_spacing_mm)

        for d_mm, expected_max in ((420.0, 210), (500.0, 250), (600.0, 300)):
            region = _region(
                _scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0),
                d_mm=d_mm,
            )
            spacings = spacing_domain_for_region(region, variables, variables.G_counts)
            outcome = optimize_region_exhaustive(region, variables)
            self.assertEqual(spacings[-1], expected_max)
            self.assertEqual(outcome.selected.spacing_mm, expected_max)
            self.assertGreaterEqual(outcome.selected.spacing_mm, 210)
            self.assertTrue(outcome.selected.controlling_limit.startswith("ACI318_25_"))

    def test_dynamic_spacing_rounds_s_max_real_down_to_configured_step(self) -> None:
        variables = VariablesConfig.model_validate(merge_optimization_defaults(None)["variables"])
        region = _region(
            _scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0),
            d_mm=686.0,
        )

        spacings = spacing_domain_for_region(region, variables, variables.G_counts)

        self.assertEqual(spacings[-1], 340)
        self.assertEqual(optimize_region_exhaustive(region, variables).selected.spacing_mm, 340)

    def test_legacy_70_to_200_default_is_normalized_to_dynamic_domain(self) -> None:
        defaults = merge_optimization_defaults(None)
        defaults["variables"]["stirrup_spacing_mm"] = list(LEGACY_FIXED_STIRRUP_SPACING_MM)
        variables = VariablesConfig.model_validate(defaults["variables"])
        region = _region(
            _scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0),
            d_mm=600.0,
        )

        spacings = spacing_domain_for_region(region, variables, variables.G_counts)

        self.assertEqual(spacings[-1], 300)
        self.assertNotEqual(spacings[-1], 200)

    def test_explicit_project_limit_participates_in_s_max_real(self) -> None:
        defaults = merge_optimization_defaults(None)
        defaults["variables"]["stirrup_spacing_project_max_mm"] = 255.0
        variables = VariablesConfig.model_validate(defaults["variables"])
        region = _region(
            _scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0),
            d_mm=675.0,
        )

        spacings = spacing_domain_for_region(region, variables, variables.G_counts)
        selected = optimize_region_exhaustive(region, variables).selected

        self.assertEqual(spacings[-1], 250)
        self.assertEqual(selected.spacing_mm, 250)
        self.assertEqual(selected.controlling_limit, "PROJECT_SPACING_LIMIT")
        self.assertEqual(selected.governing_project_spacing_limit_mm, 255.0)

    def test_inactive_torsion_residuals_provide_no_longitudinal_steel(self) -> None:
        residual = torsion_zero_tolerance / 2.0
        region = _region(
            _scenario(v_rebar=0.0, t_transverse=residual, t_longitudinal=residual)
        )

        long_bar, long_count, provided, ok = select_longitudinal_independent(
            region,
            _variables(spacings=[100]),
        )

        self.assertEqual(region.scenarios[0].torsion_state, "INACTIVE")
        self.assertIsNone(long_bar)
        self.assertEqual(long_count, 0)
        self.assertEqual(provided, 0.0)
        self.assertTrue(ok)

    def test_inactive_torsion_with_shear_still_provides_transverse_reinforcement(self) -> None:
        region = _region(_scenario(v_rebar=1000.0, t_transverse=0.0, t_longitudinal=0.0))
        candidate = optimize_region_exhaustive(region, _variables(spacings=[100, 140])).selected

        self.assertEqual(candidate.status, "ok")
        self.assertGreater(candidate.av_over_s, 0.0)
        self.assertIsNone(candidate.long_bar)
        self.assertEqual(candidate.long_count, 0)
        self.assertEqual(candidate.long_provided, 0.0)

    def test_inactive_torsion_with_seismic_spacing_still_provides_stirrups(self) -> None:
        region = _region(
            _scenario(v_rebar=0.0, t_transverse=0.0, t_longitudinal=0.0),
            detailing="DMO",
            region_type="C",
            region_length_mm=1500.0,
        )
        candidate = evaluate_candidate(
            region,
            e_bar="#3",
            g_bar="#3",
            g_count=2,
            spacing_mm=100,
            long_bar="",
            long_count=0,
            check_longitudinal=True,
        )

        self.assertEqual(candidate.status, "ok")
        self.assertGreater(candidate.av_over_s, 0.0)
        self.assertEqual(candidate.long_count, 0)
        self.assertTrue(any(check.rule_id.startswith("ACI318_25_18_4_2_4") for check in candidate.rule_checks))

    def test_active_torsion_preserves_longitudinal_design(self) -> None:
        region = _region(_scenario(v_rebar=0.0, t_transverse=10.0, t_longitudinal=200.0))

        long_bar, long_count, provided, ok = select_longitudinal_independent(
            region,
            _variables(spacings=[100]),
        )

        self.assertEqual(region.scenarios[0].torsion_state, "ACTIVE")
        self.assertEqual((long_bar, long_count, provided, ok), ("#4", 2, 258.0, True))

    def test_span_coupled_does_not_carry_torsional_bars_into_inactive_region(self) -> None:
        active = _region(
            _scenario(v_rebar=0.0, t_transverse=10.0, t_longitudinal=200.0),
            region_type="C",
            region_length_mm=1500.0,
        )
        inactive = _region(
            _scenario(v_rebar=500.0, t_transverse=0.0, t_longitudinal=0.0),
            region_length_mm=1500.0,
        )
        inactive = RegionDemand(
            **{
                **inactive.__dict__,
                "region_id": "R3",
                "scenarios": tuple(
                    DemandScenario(**{**scenario.__dict__, "region_id": "R3"})
                    for scenario in inactive.scenarios
                ),
            }
        )
        optimization_payload = merge_optimization_defaults(
            {
                "enabled": False,
                "longitudinal_mode": "span_coupled",
                "variables": {
                    "E_bars": ["#3"],
                    "G_bars": ["#3"],
                    "G_counts": [0],
                    "longitudinal_bars": ["#4", "#5"],
                    "longitudinal_bar_counts": [2, 4],
                },
                "genetic_algorithm": {
                    "population_size": 8,
                    "generations": 2,
                    "elite_count": 2,
                },
            }
        )
        outcome = optimize_span_coupled(
            [active, inactive],
            OptimizationConfig.model_validate(optimization_payload),
            span_length_mm=3000.0,
            top_n=3,
        )
        by_region = {result.region_id: result for result in outcome.results}

        self.assertGreater(by_region["R2"].long_count, 0)
        self.assertEqual(by_region["R3"].long_count, 0)
        self.assertIsNone(by_region["R3"].long_bar)
        self.assertEqual(by_region["R3"].long_provided_mm2_override, 0.0)
        self.assertEqual(by_region["R3"].longitudinal_weight_kg_per_m, 0.0)

    def test_inconsistent_torsion_remains_a_traceable_error(self) -> None:
        region = _region(_scenario(v_rebar=0.0, t_transverse=10.0, t_longitudinal=0.0))
        candidate = evaluate_candidate(
            region,
            e_bar="#3",
            g_bar="#3",
            g_count=0,
            spacing_mm=100,
            long_bar="",
            long_count=0,
            check_longitudinal=True,
        )

        self.assertEqual(region.scenarios[0].torsion_state, "INCONSISTENT")
        self.assertEqual(candidate.failure_mode, "input_fail")
        self.assertIn("Inconsistent torsion demand", candidate.message)


if __name__ == "__main__":
    unittest.main()
