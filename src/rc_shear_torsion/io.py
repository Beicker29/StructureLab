from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook

from .models import CaseConfig, resolve_path

REQUIRED_COLUMNS = [
    "Story",
    "Label",
    "UniqueName",
    "DesignSect",
    "Station",
    "AsTop",
    "AsBot",
    "VRebar",
    "TLngRebar",
    "TTrnRebar",
]


@dataclass(frozen=True)
class EtabsStationRow:
    story: str
    label: str
    unique_name: str
    design_sect: str
    station: float
    as_top: float
    as_bot: float
    v_rebar_req: float
    t_lng_req: float
    t_trn_req: float


@dataclass(frozen=True)
class EtabsFrameData:
    unique_name: str
    stations: tuple[EtabsStationRow, ...]


@dataclass(frozen=True)
class EtabsSourceData:
    source_name: str
    by_unique_name: dict[str, EtabsFrameData]
    row_count: int
    skipped_rows: int
    warnings: tuple[str, ...]


def load_etabs_sources(config: CaseConfig, case_file_dir: Path) -> dict[str, EtabsSourceData]:
    seismic_path = resolve_path(config.inputs.seismic_excel, case_file_dir)
    gravity_path = resolve_path(config.inputs.gravity_excel, case_file_dir)
    unit_factor = 100.0 if config.units.rebar_per_length == "cm2/m" else 1.0

    seismic = read_etabs_excel(
        source_name="seismic",
        excel_path=seismic_path,
        sheet_name=config.inputs.sheet_name,
        rebar_per_length_factor=unit_factor,
    )
    gravity = read_etabs_excel(
        source_name="gravity",
        excel_path=gravity_path,
        sheet_name=config.inputs.sheet_name,
        rebar_per_length_factor=unit_factor,
    )
    return {"seismic": seismic, "gravity": gravity}


def read_etabs_excel(
    *,
    source_name: str,
    excel_path: Path,
    sheet_name: str,
    rebar_per_length_factor: float,
) -> EtabsSourceData:
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found for {source_name}: {excel_path}")

    wb = load_workbook(excel_path, read_only=True, data_only=True)
    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' not found in {excel_path}")
    ws = wb[sheet_name]

    header_row_idx, header_map = find_header(ws.iter_rows(min_row=1, max_row=30, values_only=True))
    missing = [column for column in REQUIRED_COLUMNS if column not in header_map]
    if missing:
        raise ValueError(
            f"Missing required columns in {excel_path.name}: {', '.join(missing)}"
        )

    raw_by_unique: dict[str, dict[float, EtabsStationRow]] = {}
    row_count = 0
    skipped_rows = 0
    warnings: list[str] = []
    for row_index, row in enumerate(ws.iter_rows(min_row=header_row_idx + 1, values_only=True), start=header_row_idx + 1):
        if row is None:
            continue
        unique_name = as_text(row[header_map["UniqueName"]])
        station_value = row[header_map["Station"]]
        if not unique_name or station_value in (None, ""):
            skipped_rows += 1
            continue
        try:
            station = float(station_value)
        except (TypeError, ValueError):
            skipped_rows += 1
            continue

        row_count += 1
        record = EtabsStationRow(
            story=as_text(row[header_map["Story"]]),
            label=as_text(row[header_map["Label"]]),
            unique_name=unique_name,
            design_sect=as_text(row[header_map["DesignSect"]]),
            station=station,
            as_top=as_float(row[header_map["AsTop"]]),
            as_bot=as_float(row[header_map["AsBot"]]),
            v_rebar_req=as_float(row[header_map["VRebar"]]) * rebar_per_length_factor,
            t_lng_req=as_float(row[header_map["TLngRebar"]]),
            t_trn_req=as_float(row[header_map["TTrnRebar"]]) * rebar_per_length_factor,
        )

        by_station = raw_by_unique.setdefault(unique_name, {})
        if station in by_station:
            prev = by_station[station]
            by_station[station] = EtabsStationRow(
                story=record.story or prev.story,
                label=record.label or prev.label,
                unique_name=unique_name,
                design_sect=record.design_sect or prev.design_sect,
                station=station,
                as_top=max(prev.as_top, record.as_top),
                as_bot=max(prev.as_bot, record.as_bot),
                v_rebar_req=max(prev.v_rebar_req, record.v_rebar_req),
                t_lng_req=max(prev.t_lng_req, record.t_lng_req),
                t_trn_req=max(prev.t_trn_req, record.t_trn_req),
            )
        else:
            by_station[station] = record

    by_unique_name = {
        unique_name: EtabsFrameData(
            unique_name=unique_name,
            stations=tuple(by_station[key] for key in sorted(by_station.keys())),
        )
        for unique_name, by_station in raw_by_unique.items()
    }

    if skipped_rows > 0:
        warnings.append(
            f"{source_name}: skipped {skipped_rows} rows with missing/invalid UniqueName or Station"
        )

    return EtabsSourceData(
        source_name=source_name,
        by_unique_name=by_unique_name,
        row_count=row_count,
        skipped_rows=skipped_rows,
        warnings=tuple(warnings),
    )


def find_header(rows: Iterable[tuple[object, ...]]) -> tuple[int, dict[str, int]]:
    for idx, row in enumerate(rows, start=1):
        row_map = {as_text(value): i for i, value in enumerate(row) if as_text(value)}
        if "UniqueName" in row_map and "Station" in row_map and "VRebar" in row_map:
            return idx, row_map
    raise ValueError("Unable to locate ETABS header row")


def as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def as_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
