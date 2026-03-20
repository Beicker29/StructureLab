from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ALLOWED_BAR_LABELS = ("#2", "#3", "#4", "#5", "#6", "#7", "#8", "#9", "#10", "#11")


class RegionConfig(BaseModel):
    id: str
    from_: float = Field(alias="from")
    to: float
    type: Literal["C", "NC"]
    d_mm: float | None = None
    db_bar: Literal["#2", "#3", "#4", "#5", "#6", "#7", "#8", "#9", "#10", "#11"] | None = None
    min_branches: int | None = None
    width_mm: float | None = None
    height_mm: float | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validate_limits(self) -> "RegionConfig":
        if not (0.0 <= self.from_ <= 1.0 and 0.0 <= self.to <= 1.0):
            raise ValueError(f"Region '{self.id}' must be inside [0.0, 1.0]")
        if self.from_ >= self.to:
            raise ValueError(f"Region '{self.id}' must satisfy from < to")
        if self.d_mm is not None and self.d_mm <= 0.0:
            raise ValueError(f"Region '{self.id}' d_mm must be > 0")
        if self.min_branches is not None and self.min_branches < 2:
            raise ValueError(f"Region '{self.id}' min_branches must be >= 2")
        if self.width_mm is not None and self.width_mm <= 0.0:
            raise ValueError(f"Region '{self.id}' width_mm must be > 0")
        if self.height_mm is not None and self.height_mm <= 0.0:
            raise ValueError(f"Region '{self.id}' height_mm must be > 0")
        return self


class SpanConfig(BaseModel):
    id: str
    seismic: str
    gravity: str
    regions: list[RegionConfig]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_regions(self) -> "SpanConfig":
        if not self.regions:
            raise ValueError(f"Span '{self.id}' must include at least one region")
        sorted_regions = sorted(self.regions, key=lambda region: region.from_)
        tol = 1.0e-9
        if abs(sorted_regions[0].from_ - 0.0) > tol:
            raise ValueError(f"Span '{self.id}' regions must start at 0.0")
        if abs(sorted_regions[-1].to - 1.0) > tol:
            raise ValueError(f"Span '{self.id}' regions must end at 1.0")
        current = 0.0
        for region in sorted_regions:
            if abs(region.from_ - current) > tol:
                raise ValueError(
                    f"Span '{self.id}' regions contain gaps/overlap around {region.id}: "
                    f"expected from={current}, got {region.from_}"
                )
            current = region.to
        return self


class BeamConfig(BaseModel):
    beam_id: str
    detailing: Literal["DES", "DMO"] = "DES"
    cover_side_mm: float | None = None
    cover_top_mm: float | None = None
    cover_bottom_mm: float | None = None
    fc_mpa: float | None = None
    fy_mpa: float | None = None
    spans: list[SpanConfig]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_covers(self) -> "BeamConfig":
        if self.cover_side_mm is not None and self.cover_side_mm < 0.0:
            raise ValueError(f"Beam '{self.beam_id}' cover_side_mm must be >= 0")
        if self.cover_top_mm is not None and self.cover_top_mm < 0.0:
            raise ValueError(f"Beam '{self.beam_id}' cover_top_mm must be >= 0")
        if self.cover_bottom_mm is not None and self.cover_bottom_mm < 0.0:
            raise ValueError(f"Beam '{self.beam_id}' cover_bottom_mm must be >= 0")
        if self.fc_mpa is not None and self.fc_mpa <= 0.0:
            raise ValueError(f"Beam '{self.beam_id}' fc_mpa must be > 0")
        if self.fy_mpa is not None and self.fy_mpa <= 0.0:
            raise ValueError(f"Beam '{self.beam_id}' fy_mpa must be > 0")
        return self


class InputsConfig(BaseModel):
    seismic_excel: str
    gravity_excel: str
    sheet_name: str

    model_config = ConfigDict(extra="forbid")


class UnitsConfig(BaseModel):
    rebar_per_length: Literal["cm2/m", "mm2/m"]

    model_config = ConfigDict(extra="forbid")


class VariablesConfig(BaseModel):
    E_bars: list[str]
    G_bars: list[str]
    G_counts: list[int]
    stirrup_spacing_mm: list[int]
    longitudinal_bars: list[str]
    longitudinal_bar_counts: list[int]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_non_empty(self) -> "VariablesConfig":
        fields = (
            ("E_bars", self.E_bars),
            ("G_bars", self.G_bars),
            ("G_counts", self.G_counts),
            ("stirrup_spacing_mm", self.stirrup_spacing_mm),
            ("longitudinal_bars", self.longitudinal_bars),
            ("longitudinal_bar_counts", self.longitudinal_bar_counts),
        )
        for field_name, values in fields:
            if not values:
                raise ValueError(f"optimization.variables.{field_name} cannot be empty")
        if any(value <= 0 for value in self.stirrup_spacing_mm):
            raise ValueError("optimization.variables.stirrup_spacing_mm must be > 0")
        if any(value < 0 for value in self.G_counts):
            raise ValueError("optimization.variables.G_counts must be >= 0")
        if any(value <= 0 for value in self.longitudinal_bar_counts):
            raise ValueError("optimization.variables.longitudinal_bar_counts must be > 0")
        invalid_e = sorted({bar for bar in self.E_bars if bar not in ALLOWED_BAR_LABELS})
        if invalid_e:
            raise ValueError(
                f"optimization.variables.E_bars contains unsupported bars {invalid_e}; allowed={list(ALLOWED_BAR_LABELS)}"
            )
        invalid_g = sorted({bar for bar in self.G_bars if bar not in ALLOWED_BAR_LABELS})
        if invalid_g:
            raise ValueError(
                f"optimization.variables.G_bars contains unsupported bars {invalid_g}; allowed={list(ALLOWED_BAR_LABELS)}"
            )
        invalid_long = sorted({bar for bar in self.longitudinal_bars if bar not in ALLOWED_BAR_LABELS})
        if invalid_long:
            raise ValueError(
                "optimization.variables.longitudinal_bars contains unsupported bars "
                f"{invalid_long}; allowed={list(ALLOWED_BAR_LABELS)}"
            )
        return self


class GAConfig(BaseModel):
    population_size: int
    generations: int
    crossover_rate: float
    mutation_rate: float
    elite_count: int

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_values(self) -> "GAConfig":
        if self.population_size < 4:
            raise ValueError("population_size must be >= 4")
        if self.generations < 1:
            raise ValueError("generations must be >= 1")
        if not (0.0 <= self.crossover_rate <= 1.0):
            raise ValueError("crossover_rate must be in [0, 1]")
        if not (0.0 <= self.mutation_rate <= 1.0):
            raise ValueError("mutation_rate must be in [0, 1]")
        if self.elite_count < 1 or self.elite_count >= self.population_size:
            raise ValueError("elite_count must be >=1 and < population_size")
        return self


class OptimizationConfig(BaseModel):
    enabled: bool
    objective: Literal["min_weight"]
    variables: VariablesConfig
    genetic_algorithm: GAConfig

    model_config = ConfigDict(extra="forbid")


class CaseConfig(BaseModel):
    case_name: str
    inputs: InputsConfig
    units: UnitsConfig
    beams: list[BeamConfig]
    optimization: OptimizationConfig

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_beams(self) -> "CaseConfig":
        if not self.beams:
            raise ValueError("At least one beam must be provided")
        beam_ids = [beam.beam_id for beam in self.beams]
        if len(beam_ids) != len(set(beam_ids)):
            raise ValueError("beam_id values must be unique")

        if self.optimization.enabled:
            for beam in self.beams:
                if beam.cover_side_mm is None or beam.cover_top_mm is None or beam.cover_bottom_mm is None:
                    raise ValueError(
                        f"Optimization enabled: beam '{beam.beam_id}' must define "
                        "cover_side_mm, cover_top_mm, and cover_bottom_mm"
                    )
                for span in beam.spans:
                    for region in span.regions:
                        required_geometry = (
                            region.width_mm,
                            region.height_mm,
                        )
                        if any(value is None for value in required_geometry):
                            raise ValueError(
                                f"Optimization enabled: region '{beam.beam_id}/{span.id}/{region.id}' "
                                "must define width_mm and height_mm"
                            )
                        if region.width_mm <= 2.0 * beam.cover_side_mm:
                            raise ValueError(
                                f"Region '{beam.beam_id}/{span.id}/{region.id}' width_mm must be > 2*beam.cover_side_mm"
                            )
                        if region.height_mm <= (beam.cover_top_mm + beam.cover_bottom_mm):
                            raise ValueError(
                                f"Region '{beam.beam_id}/{span.id}/{region.id}' height_mm must be > "
                                "beam.cover_top_mm + beam.cover_bottom_mm"
                            )

        for beam in self.beams:
            if beam.detailing == "DES":
                for span in beam.spans:
                    for region in span.regions:
                        if region.type != "C":
                            continue
                        if region.d_mm is None or region.db_bar is None:
                            raise ValueError(
                                f"Beam '{beam.beam_id}' is DES: region '{span.id}/{region.id}' "
                                "with type='C' must define d_mm and db_bar"
                            )

        for beam in self.beams:
            if beam.detailing != "DMO":
                continue
            for span in beam.spans:
                for region in span.regions:
                    if region.type == "NC":
                        if beam.fc_mpa is None or beam.fy_mpa is None:
                            raise ValueError(
                                f"Beam '{beam.beam_id}' is DMO with region '{span.id}/{region.id}' type='NC': "
                                "beam must define fc_mpa and fy_mpa"
                            )
                        if region.d_mm is None or region.db_bar is None:
                            raise ValueError(
                                f"Beam '{beam.beam_id}' is DMO: region '{span.id}/{region.id}' "
                                "with type='NC' must define d_mm and db_bar"
                            )
                    if region.type != "C":
                        continue
                    if region.d_mm is None or region.db_bar is None:
                        raise ValueError(
                            f"Beam '{beam.beam_id}' is DMO: region '{span.id}/{region.id}' "
                            "with type='C' must define d_mm and db_bar"
                        )
                    if region.min_branches is None:
                        raise ValueError(
                            f"Beam '{beam.beam_id}' is DMO: region '{span.id}/{region.id}' "
                            "with type='C' must define min_branches"
                        )
                    if region.min_branches < 4:
                        raise ValueError(
                            f"Beam '{beam.beam_id}' is DMO: region '{span.id}/{region.id}' "
                            "with type='C' requires min_branches >= 4"
                        )
                    min_required_g = region.min_branches - 2
                    if max(self.optimization.variables.G_counts) < min_required_g:
                        raise ValueError(
                            f"Beam '{beam.beam_id}' region '{span.id}/{region.id}': "
                            f"min_branches={region.min_branches} requires G_count >= {min_required_g}, "
                            f"but optimization.variables.G_counts={self.optimization.variables.G_counts}"
                        )
        return self


def load_case_config(case_json_path: str | Path) -> CaseConfig:
    case_path = Path(case_json_path)
    if not case_path.exists():
        raise FileNotFoundError(f"Case file not found: {case_path}")
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    config = CaseConfig.model_validate(payload)
    validate_input_files(config, case_path.parent)
    return config


def validate_input_files(config: CaseConfig, base_dir: Path) -> None:
    seismic = resolve_path(config.inputs.seismic_excel, base_dir)
    gravity = resolve_path(config.inputs.gravity_excel, base_dir)
    if not seismic.exists():
        raise FileNotFoundError(f"Seismic excel does not exist: {seismic}")
    if not gravity.exists():
        raise FileNotFoundError(f"Gravity excel does not exist: {gravity}")


def resolve_path(path_value: str, base_dir: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    cwd_candidate = path.resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return (base_dir / path).resolve()
