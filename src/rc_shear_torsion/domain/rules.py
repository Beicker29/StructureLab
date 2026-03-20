from __future__ import annotations

from rc_shear_torsion.models import ALLOWED_BAR_LABELS, CaseConfig

from .errors import DomainIssue


def _issue(code: str, field: str, message: str) -> DomainIssue:
    return DomainIssue(code=code, field=field, message=message)


def validate_case_rules(config: CaseConfig) -> list[DomainIssue]:
    issues: list[DomainIssue] = []
    variables = config.optimization.variables
    ga = config.optimization.genetic_algorithm

    if any(value <= 0 for value in variables.stirrup_spacing_mm):
        issues.append(
            _issue(
                "invalid_range",
                "optimization.variables.stirrup_spacing_mm",
                "All values must be > 0",
            )
        )
    if any(value < 0 for value in variables.G_counts):
        issues.append(
            _issue(
                "invalid_range",
                "optimization.variables.G_counts",
                "All values must be >= 0",
            )
        )
    if any(value <= 0 for value in variables.longitudinal_bar_counts):
        issues.append(
            _issue(
                "invalid_range",
                "optimization.variables.longitudinal_bar_counts",
                "All values must be > 0",
            )
        )

    invalid_e = sorted({bar for bar in variables.E_bars if bar not in ALLOWED_BAR_LABELS})
    if invalid_e:
        issues.append(
            _issue(
                "unsupported_bar",
                "optimization.variables.E_bars",
                f"Unsupported bars {invalid_e}; allowed={list(ALLOWED_BAR_LABELS)}",
            )
        )
    invalid_g = sorted({bar for bar in variables.G_bars if bar not in ALLOWED_BAR_LABELS})
    if invalid_g:
        issues.append(
            _issue(
                "unsupported_bar",
                "optimization.variables.G_bars",
                f"Unsupported bars {invalid_g}; allowed={list(ALLOWED_BAR_LABELS)}",
            )
        )
    invalid_long = sorted({bar for bar in variables.longitudinal_bars if bar not in ALLOWED_BAR_LABELS})
    if invalid_long:
        issues.append(
            _issue(
                "unsupported_bar",
                "optimization.variables.longitudinal_bars",
                f"Unsupported bars {invalid_long}; allowed={list(ALLOWED_BAR_LABELS)}",
            )
        )

    if ga.population_size < 4:
        issues.append(
            _issue(
                "invalid_range",
                "optimization.genetic_algorithm.population_size",
                "population_size must be >= 4",
            )
        )
    if ga.generations < 1:
        issues.append(
            _issue(
                "invalid_range",
                "optimization.genetic_algorithm.generations",
                "generations must be >= 1",
            )
        )
    if not (0.0 <= ga.crossover_rate <= 1.0):
        issues.append(
            _issue(
                "invalid_range",
                "optimization.genetic_algorithm.crossover_rate",
                "crossover_rate must be in [0, 1]",
            )
        )
    if not (0.0 <= ga.mutation_rate <= 1.0):
        issues.append(
            _issue(
                "invalid_range",
                "optimization.genetic_algorithm.mutation_rate",
                "mutation_rate must be in [0, 1]",
            )
        )
    if ga.elite_count < 1 or ga.elite_count >= ga.population_size:
        issues.append(
            _issue(
                "invalid_range",
                "optimization.genetic_algorithm.elite_count",
                "elite_count must be >= 1 and < population_size",
            )
        )

    if config.optimization.enabled:
        for beam in config.beams:
            if beam.cover_side_mm is None or beam.cover_top_mm is None or beam.cover_bottom_mm is None:
                issues.append(
                    _issue(
                        "missing_required",
                        f"beams[{beam.beam_id}].covers",
                        "Optimization enabled requires cover_side_mm, cover_top_mm, and cover_bottom_mm",
                    )
                )
                continue
            for span in beam.spans:
                for region in span.regions:
                    if region.width_mm is None or region.height_mm is None:
                        issues.append(
                            _issue(
                                "missing_required",
                                f"beams[{beam.beam_id}].spans[{span.id}].regions[{region.id}]",
                                "Optimization enabled requires width_mm and height_mm",
                            )
                        )
                        continue
                    if region.width_mm <= 2.0 * beam.cover_side_mm:
                        issues.append(
                            _issue(
                                "invalid_geometry",
                                f"beams[{beam.beam_id}].spans[{span.id}].regions[{region.id}].width_mm",
                                "width_mm must be > 2*beam.cover_side_mm",
                            )
                        )
                    if region.height_mm <= (beam.cover_top_mm + beam.cover_bottom_mm):
                        issues.append(
                            _issue(
                                "invalid_geometry",
                                f"beams[{beam.beam_id}].spans[{span.id}].regions[{region.id}].height_mm",
                                "height_mm must be > beam.cover_top_mm + beam.cover_bottom_mm",
                            )
                        )

    for beam in config.beams:
        if beam.detailing == "DES":
            for span in beam.spans:
                for region in span.regions:
                    if region.type != "C":
                        continue
                    if region.d_mm is None or region.db_bar is None:
                        issues.append(
                            _issue(
                                "missing_required",
                                f"beams[{beam.beam_id}].spans[{span.id}].regions[{region.id}]",
                                "DES with region type C requires d_mm and db_bar",
                            )
                        )

    for beam in config.beams:
        if beam.detailing != "DMO":
            continue
        for span in beam.spans:
            for region in span.regions:
                region_path = f"beams[{beam.beam_id}].spans[{span.id}].regions[{region.id}]"
                if region.type == "NC":
                    if beam.fc_mpa is None or beam.fy_mpa is None:
                        issues.append(
                            _issue(
                                "missing_required",
                                f"beams[{beam.beam_id}]",
                                "DMO with region type NC requires beam fc_mpa and fy_mpa",
                            )
                        )
                    if region.d_mm is None or region.db_bar is None:
                        issues.append(
                            _issue(
                                "missing_required",
                                region_path,
                                "DMO with region type NC requires d_mm and db_bar",
                            )
                        )
                if region.type != "C":
                    continue
                if region.d_mm is None or region.db_bar is None:
                    issues.append(
                        _issue(
                            "missing_required",
                            region_path,
                            "DMO with region type C requires d_mm and db_bar",
                        )
                    )
                    continue
                if region.min_branches is None:
                    issues.append(
                        _issue(
                            "missing_required",
                            region_path,
                            "DMO with region type C requires min_branches",
                        )
                    )
                    continue
                if region.min_branches < 4:
                    issues.append(
                        _issue(
                            "invalid_range",
                            f"{region_path}.min_branches",
                            "DMO with region type C requires min_branches >= 4",
                        )
                    )
                    continue
                min_required_g = region.min_branches - 2
                if max(variables.G_counts) < min_required_g:
                    issues.append(
                        _issue(
                            "incompatible_domain",
                            "optimization.variables.G_counts",
                            f"Region {beam.beam_id}/{span.id}/{region.id} requires G_count >= {min_required_g}",
                        )
                    )

    return issues

