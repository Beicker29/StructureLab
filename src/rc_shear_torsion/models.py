from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from .reinforcement import ALLOWED_BAR_LABELS as ALLOWED_BAR_LABELS, BAR_DIAMETERS_MM

DEFAULT_STIRRUP_SPACING_MIN_MM = 70
DEFAULT_STIRRUP_SPACING_STEP_MM = 10
LEGACY_FIXED_STIRRUP_SPACING_MM = tuple(range(70, 201, 10))


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
    # Effective-depth provenance is optional for legacy JSON cases.  New form
    # payloads identify ratio-derived values explicitly so d_mm is not mistaken
    # for a measured or fully detailed geometry.
    d_source: Literal["EXPLICIT", "DEFAULT_RATIO", "SPAN_RATIO"] | None = None
    d_ratio: float | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @model_validator(mode="after")
    def validate_limits(self) -> "RegionConfig":
        if not (0.0 <= self.from_ <= 1.0 and 0.0 <= self.to <= 1.0):
            raise ValueError(f"Region '{self.id}' must be inside [0.0, 1.0]")
        if self.from_ >= self.to:
            raise ValueError(f"Region '{self.id}' must satisfy from < to")
        if self.d_mm is not None and self.d_mm <= 0.0:
            raise ValueError(f"Region '{self.id}' d_mm must be > 0")
        if self.min_branches is not None and self.min_branches < 1:
            raise ValueError(f"Region '{self.id}' min_branches must be >= 1")
        if self.width_mm is not None and self.width_mm <= 0.0:
            raise ValueError(f"Region '{self.id}' width_mm must be > 0")
        if self.height_mm is not None and self.height_mm <= 0.0:
            raise ValueError(f"Region '{self.id}' height_mm must be > 0")
        if self.d_ratio is not None and not (0.0 < self.d_ratio <= 1.0):
            raise ValueError(f"Region '{self.id}' d_ratio must be inside (0, 1]")
        if self.d_source in {"DEFAULT_RATIO", "SPAN_RATIO"} and self.d_ratio is None:
            raise ValueError(f"Region '{self.id}' {self.d_source} requires d_ratio")
        return self


class SpanConfig(BaseModel):
    id: str
    seismic: str
    gravity: str
    support_left_mm: float | None = None
    support_right_mm: float | None = None
    clear_length_mm: float | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "clear_length_mm",
            "L_libre_real_mm",
            "longitud_libre_real_mm",
        ),
    )
    regions: list[RegionConfig]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_regions(self) -> "SpanConfig":
        if not self.regions:
            raise ValueError(f"Span '{self.id}' must include at least one region")
        if self.support_left_mm is not None and self.support_left_mm < 0.0:
            raise ValueError(f"Span '{self.id}' support_left_mm must be >= 0")
        if self.support_right_mm is not None and self.support_right_mm < 0.0:
            raise ValueError(f"Span '{self.id}' support_right_mm must be >= 0")
        if self.clear_length_mm is not None and self.clear_length_mm <= 0.0:
            raise ValueError(f"Span '{self.id}' clear_length_mm must be > 0")
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
    detailing: Literal["DES", "DMO", "DMI"] = "DES"
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
    # A supplied list is an explicit legacy/custom catalog.  When omitted (or
    # when it is the former implicit 70..200 default), the engine builds the
    # catalog dynamically from the real code, demand, and project limits.
    stirrup_spacing_mm: list[int] | None = None
    stirrup_spacing_min_mm: int = DEFAULT_STIRRUP_SPACING_MIN_MM
    stirrup_spacing_step_mm: int = DEFAULT_STIRRUP_SPACING_STEP_MM
    stirrup_spacing_project_max_mm: float | None = None
    longitudinal_bars: list[str]
    longitudinal_bar_counts: list[int]

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_non_empty(self) -> "VariablesConfig":
        fields = (
            ("E_bars", self.E_bars),
            ("G_bars", self.G_bars),
            ("G_counts", self.G_counts),
            ("longitudinal_bars", self.longitudinal_bars),
            ("longitudinal_bar_counts", self.longitudinal_bar_counts),
        )
        for field_name, values in fields:
            if not values:
                raise ValueError(f"optimization.variables.{field_name} cannot be empty")
        if self.stirrup_spacing_mm is not None and not self.stirrup_spacing_mm:
            raise ValueError("optimization.variables.stirrup_spacing_mm cannot be empty when supplied")
        return self


class GAConfig(BaseModel):
    population_size: int
    generations: int
    crossover_rate: float
    mutation_rate: float
    elite_count: int

    model_config = ConfigDict(extra="forbid")


class OptimizationConfig(BaseModel):
    enabled: bool
    objective: Literal["min_weight"]
    longitudinal_mode: Literal["legacy_region_independent", "span_coupled"] = "legacy_region_independent"
    variables: VariablesConfig
    genetic_algorithm: GAConfig

    model_config = ConfigDict(extra="forbid")


class CaseConfig(BaseModel):
    case_name: str
    inputs: InputsConfig
    units: UnitsConfig
    longitudinal_bar_diameter_mm: float | None = None
    compression_rebar_required: bool = False
    longitudinal_bars_bundled: Literal[False] = False
    beams: list[BeamConfig]
    optimization: OptimizationConfig

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def normalize_global_longitudinal_detailing(cls, data: object) -> object:
        """Consolidate legacy beam/span detailing values into one case value.

        Phase 3 initially allowed span overrides.  They remain readable only
        when every explicit legacy value agrees; conflicting values are never
        resolved by order or by selecting an arbitrary span.
        """
        if not isinstance(data, dict) or not isinstance(data.get("beams"), list):
            return data
        migrated = dict(data)
        diameter_values: list[tuple[str, float]] = []
        compression_values: list[tuple[str, bool]] = []

        def add_diameter(path: str, value: object) -> None:
            if value is None:
                return
            try:
                diameter = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path} must be a numeric diameter in mm") from exc
            diameter_values.append((path, diameter))

        def add_compression(path: str, value: object) -> None:
            if not isinstance(value, bool):
                raise ValueError(f"{path} must be boolean")
            compression_values.append((path, value))

        if migrated.get("longitudinal_bar_diameter_mm") is not None:
            add_diameter(
                "longitudinal_bar_diameter_mm",
                migrated["longitudinal_bar_diameter_mm"],
            )
        if "compression_rebar_required" in migrated:
            add_compression(
                "compression_rebar_required",
                migrated["compression_rebar_required"],
            )

        migrated_beams: list[object] = []
        for beam_index, beam_value in enumerate(data["beams"]):
            if not isinstance(beam_value, dict):
                migrated_beams.append(beam_value)
                continue
            beam = dict(beam_value)
            beam_path = f"beams[{beam_index}]"
            if beam.get("longitudinal_bar_diameter_mm") is not None:
                add_diameter(
                    f"{beam_path}.longitudinal_bar_diameter_mm",
                    beam.pop("longitudinal_bar_diameter_mm"),
                )
            if "compression_rebar_required" in beam:
                add_compression(
                    f"{beam_path}.compression_rebar_required",
                    beam.pop("compression_rebar_required"),
                )
            if "longitudinal_bars_bundled" in beam:
                bundled = beam.pop("longitudinal_bars_bundled")
                if bundled is not False:
                    raise ValueError(
                        f"{beam_path}.longitudinal_bars_bundled conflicts with global false"
                    )
            spans_value = beam.get("spans")
            if isinstance(spans_value, list):
                spans: list[object] = []
                for span_index, span_value in enumerate(spans_value):
                    if not isinstance(span_value, dict):
                        spans.append(span_value)
                        continue
                    span = dict(span_value)
                    span_path = f"{beam_path}.spans[{span_index}]"
                    if span.get("longitudinal_bar_diameter_mm") is not None:
                        add_diameter(
                            f"{span_path}.longitudinal_bar_diameter_mm",
                            span.pop("longitudinal_bar_diameter_mm"),
                        )
                    if "compression_rebar_required" in span:
                        add_compression(
                            f"{span_path}.compression_rebar_required",
                            span.pop("compression_rebar_required"),
                        )
                    if "longitudinal_bars_bundled" in span:
                        bundled = span.pop("longitudinal_bars_bundled")
                        if bundled is not False:
                            raise ValueError(
                                f"{span_path}.longitudinal_bars_bundled conflicts with global false"
                            )
                    regions_value = span.get("regions")
                    if isinstance(regions_value, list):
                        for region_index, region_value in enumerate(regions_value):
                            if not isinstance(region_value, dict):
                                continue
                            db_bar = region_value.get("db_bar")
                            if db_bar in BAR_DIAMETERS_MM:
                                add_diameter(
                                    f"{span_path}.regions[{region_index}].db_bar",
                                    BAR_DIAMETERS_MM[db_bar],
                                )
                    spans.append(span)
                beam["spans"] = spans
            migrated_beams.append(beam)
        migrated["beams"] = migrated_beams

        if diameter_values:
            expected_path, expected = diameter_values[0]
            conflicts = [
                (path, value)
                for path, value in diameter_values[1:]
                if abs(value - expected) > 1.0e-9
            ]
            if conflicts:
                details = ", ".join(
                    [f"{expected_path}={expected:g}"]
                    + [f"{path}={value:g}" for path, value in conflicts]
                )
                raise ValueError(
                    "Conflicting legacy longitudinal_bar_diameter_mm values; "
                    f"global case configuration is required: {details}"
                )
            migrated["longitudinal_bar_diameter_mm"] = expected

        if compression_values:
            expected_path, expected = compression_values[0]
            conflicts = [
                (path, value)
                for path, value in compression_values[1:]
                if value != expected
            ]
            if conflicts:
                details = ", ".join(
                    [f"{expected_path}={str(expected).lower()}"]
                    + [f"{path}={str(value).lower()}" for path, value in conflicts]
                )
                raise ValueError(
                    "Conflicting legacy compression_rebar_required values; "
                    f"global case configuration is required: {details}"
                )
            migrated["compression_rebar_required"] = expected
        return migrated

    @model_validator(mode="after")
    def validate_beams(self) -> "CaseConfig":
        if not self.beams:
            raise ValueError("At least one beam must be provided")
        if (
            self.longitudinal_bar_diameter_mm is not None
            and self.longitudinal_bar_diameter_mm <= 0.0
        ):
            raise ValueError("longitudinal_bar_diameter_mm must be > 0")
        beam_ids = [beam.beam_id for beam in self.beams]
        if len(beam_ids) != len(set(beam_ids)):
            raise ValueError("beam_id values must be unique")
        return self


def load_case_config(case_json_path: str | Path) -> CaseConfig:
    case_path = Path(case_json_path)
    if not case_path.exists():
        raise FileNotFoundError(f"Case file not found: {case_path}")
    payload = json.loads(case_path.read_text(encoding="utf-8"))
    from .domain.validation import validate_case_payload

    config = validate_case_payload(payload)
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
    base_candidate = (base_dir / path).resolve()
    if base_candidate.exists():
        return base_candidate

    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    # Keep deterministic error paths anchored to the case directory.
    return base_candidate


