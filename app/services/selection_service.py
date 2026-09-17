"""Resolve user selections against an existing preview without I/O."""

from __future__ import annotations

from app.core.errors import AppError
from app.schemas.jobs import JobSelectionSaveRequest, RegionOptionSelection, SpanOptionSelection


def _region_selection_data(preview: dict) -> dict[tuple[str, str], dict]:
    spans = preview.get("spans") if isinstance(preview.get("spans"), list) else []

    region_data: dict[tuple[str, str], dict] = {}
    for span in spans:
        span_id = str(span.get("span_id") or "").strip()
        if not span_id:
            continue
        regions = span.get("regions") if isinstance(span.get("regions"), list) else []
        for region in regions:
            region_id = str(region.get("region_id") or "").strip()
            options = region.get("options") if isinstance(region.get("options"), list) else []
            normalized_rows = sorted(
                [
                    {
                        "option": int(opt.get("option")),
                        "transverse_label": str(opt.get("transverse_label") or "").strip(),
                        "longitudinal_label": str(opt.get("longitudinal_label") or "").strip(),
                        "base_longitudinal_label": str(opt.get("base_longitudinal_label") or "").strip(),
                        "additional_longitudinal_label": str(opt.get("additional_longitudinal_label") or "").strip(),
                        "weight_total_kg": float(opt.get("weight_total_kg") or 0.0),
                        "weight_transverse_kg": float(opt.get("weight_transverse_kg") or 0.0),
                        "weight_longitudinal_kg": float(opt.get("weight_longitudinal_kg") or 0.0),
                    }
                    for opt in options
                    if opt.get("option") is not None
                ],
                key=lambda item: (
                    float(item.get("weight_total_kg") or 0.0),
                    int(item.get("option") or 0),
                ),
            )
            if not region_id or not normalized_rows:
                continue

            best_row = normalized_rows[0]
            trans_map: dict[str, dict] = {}
            long_map: dict[str, dict] = {}

            preview_transverse_options = (
                region.get("transverse_options") if isinstance(region.get("transverse_options"), list) else []
            )
            for option in preview_transverse_options:
                trans_label = str(option.get("label") or "").strip()
                if not trans_label:
                    continue
                item: dict[str, float | int | str] = {
                    "label": trans_label,
                    "weight_kg": float(option.get("weight_kg") or 0.0),
                }
                if option.get("stirrup_count") is not None:
                    try:
                        item["stirrup_count"] = int(option.get("stirrup_count"))
                    except (TypeError, ValueError):
                        pass
                if option.get("stirrup_unit_weight_kg") is not None:
                    try:
                        item["stirrup_unit_weight_kg"] = float(option.get("stirrup_unit_weight_kg"))
                    except (TypeError, ValueError):
                        pass
                trans_map[trans_label] = item

            preview_longitudinal_options = (
                region.get("longitudinal_options") if isinstance(region.get("longitudinal_options"), list) else []
            )
            for option in preview_longitudinal_options:
                long_label = str(option.get("label") or "").strip()
                if not long_label:
                    continue
                long_map[long_label] = {
                    "label": long_label,
                    "weight_kg": float(option.get("weight_kg") or 0.0),
                }

            for row in normalized_rows:
                trans_label = row["transverse_label"]
                long_label = row["longitudinal_label"]
                trans_weight = float(row.get("weight_transverse_kg") or 0.0)
                long_weight = float(row.get("weight_longitudinal_kg") or 0.0)

                if trans_label:
                    current = trans_map.get(trans_label)
                    if current is None or trans_weight < float(current.get("weight_kg") or 0.0):
                        updated: dict[str, float | int | str] = {
                            "label": trans_label,
                            "weight_kg": trans_weight,
                        }
                        if current is not None and current.get("stirrup_count") is not None:
                            updated["stirrup_count"] = int(current["stirrup_count"])
                        if current is not None and current.get("stirrup_unit_weight_kg") is not None:
                            updated["stirrup_unit_weight_kg"] = float(current["stirrup_unit_weight_kg"])
                        trans_map[trans_label] = updated

                if long_label:
                    current = long_map.get(long_label)
                    if current is None or long_weight < float(current.get("weight_kg") or 0.0):
                        long_map[long_label] = {
                            "label": long_label,
                            "weight_kg": long_weight,
                        }

            region_data[(span_id, region_id)] = {
                "best": best_row,
                "rows": normalized_rows,
                "transverse_options": sorted(trans_map.values(), key=lambda item: float(item["weight_kg"])),
                "longitudinal_options": sorted(long_map.values(), key=lambda item: float(item["weight_kg"])),
            }

    if not region_data:
        raise AppError(
            message="No hay alternativas por region disponibles para este job.",
            status_code=422,
            code="selection_unavailable",
        )

    return region_data


def _span_selection_data(
    region_data: dict[tuple[str, str], dict],
) -> tuple[dict[str, list[tuple[str, dict]]], dict[str, list[dict]], dict[str, dict[int, dict[str, dict]]]]:
    span_region_data: dict[str, list[tuple[str, dict]]] = {}
    for (span_id, region_id), data in region_data.items():
        span_region_data.setdefault(span_id, []).append((region_id, data))

    span_longitudinal_options: dict[str, list[dict]] = {}
    span_option_rows: dict[str, dict[int, dict[str, dict]]] = {}
    for span_id, items in span_region_data.items():
        common_labels: set[str] | None = None
        for _, data in items:
            labels = {
                str(option.get("label") or "").strip()
                for option in data["longitudinal_options"]
                if str(option.get("label") or "").strip()
            }
            common_labels = labels if common_labels is None else (common_labels & labels)

        options: list[dict] = []
        if common_labels:
            for label in common_labels:
                weight_sum = 0.0
                for _, data in items:
                    option = next(
                        (
                            entry
                            for entry in data["longitudinal_options"]
                            if str(entry.get("label") or "").strip() == label
                        ),
                        None,
                    )
                    weight_sum += float((option or {}).get("weight_kg") or 0.0)
                options.append({"label": label, "weight_kg": weight_sum, "coverage": len(items)})
            options.sort(key=lambda item: (float(item["weight_kg"]), str(item["label"])))
        else:
            union: dict[str, dict] = {}
            for _, data in items:
                for option in data["longitudinal_options"]:
                    label = str(option.get("label") or "").strip()
                    if not label:
                        continue
                    entry = union.setdefault(label, {"label": label, "weight_kg": 0.0, "coverage": 0})
                    entry["weight_kg"] = float(entry["weight_kg"]) + float(option.get("weight_kg") or 0.0)
                    entry["coverage"] = int(entry["coverage"]) + 1
            options = sorted(
                union.values(),
                key=lambda item: (-int(item["coverage"]), float(item["weight_kg"]), str(item["label"])),
            )

        span_longitudinal_options[span_id] = options[:10]

        common_option_numbers: set[int] | None = None
        for _, data in items:
            numbers = {
                int(row["option"])
                for row in data["rows"]
                if row.get("option") is not None
            }
            common_option_numbers = numbers if common_option_numbers is None else (common_option_numbers & numbers)

        option_map: dict[int, dict[str, dict]] = {}
        for option_number in sorted(common_option_numbers or []):
            per_region: dict[str, dict] = {}
            for region_id, data in items:
                row = next((row for row in data["rows"] if int(row["option"]) == option_number), None)
                if row is None:
                    per_region = {}
                    break
                per_region[region_id] = row
            if per_region:
                option_map[option_number] = per_region
        span_option_rows[span_id] = option_map

    return span_region_data, span_longitudinal_options, span_option_rows


def _validate_requested_selections(
    payload: JobSelectionSaveRequest,
    region_data: dict[tuple[str, str], dict],
    span_region_data: dict[str, list[tuple[str, dict]]],
) -> tuple[dict[tuple[str, str], RegionOptionSelection], dict[str, SpanOptionSelection]]:
    requested_map: dict[tuple[str, str], RegionOptionSelection] = {}
    for item in payload.selections:
        key = (item.span_id.strip(), item.region_id.strip())
        if not key[0] or not key[1]:
            raise AppError(
                message="Cada seleccion debe incluir span_id y region_id validos.",
                status_code=422,
                code="invalid_selection",
            )
        if key in requested_map:
            raise AppError(
                message=f"La region {key[0]}/{key[1]} esta repetida en la seleccion.",
                status_code=422,
                code="invalid_selection",
            )
        requested_map[key] = item

    requested_span_map: dict[str, SpanOptionSelection] = {}
    for item in payload.span_selections:
        span_id = item.span_id.strip()
        if not span_id:
            raise AppError(
                message="Cada seleccion por vano debe incluir span_id valido.",
                status_code=422,
                code="invalid_selection",
            )
        if span_id in requested_span_map:
            raise AppError(
                message=f"El vano {span_id} esta repetido en span_selections.",
                status_code=422,
                code="invalid_selection",
            )
        if span_id not in span_region_data:
            raise AppError(
                message=f"El vano {span_id} no existe en el preview del job.",
                status_code=422,
                code="invalid_selection",
            )
        requested_span_map[span_id] = item

    invalid_regions = sorted(
        [f"{span_id}/{region_id}" for (span_id, region_id) in requested_map if (span_id, region_id) not in region_data]
    )
    if invalid_regions:
        raise AppError(
            message=f"Estas regiones no existen en el preview del job: {', '.join(invalid_regions)}",
            status_code=422,
            code="invalid_selection",
        )

    return requested_map, requested_span_map


def _filter_longitudinal_labels(
    rows: list[dict], base_label: str | None, additional_label: str | None,
) -> list[dict]:
    for field, label in (
        ("base_longitudinal_label", base_label),
        ("additional_longitudinal_label", additional_label),
    ):
        if label:
            rows = [row for row in rows if str(row.get(field) or "").strip() == label]
    return rows


def resolve_selected_options(preview: dict, payload: JobSelectionSaveRequest) -> list[dict]:
    """Preserve region/span precedence, exact combinations and report fields."""
    region_data = _region_selection_data(preview)
    span_region_data, span_longitudinal_options, span_option_rows = _span_selection_data(region_data)
    requested_map, requested_span_map = _validate_requested_selections(payload, region_data, span_region_data)
    resolved_rows: list[dict] = []
    for key in sorted(region_data.keys()):
        span_id, region_id = key
        data = region_data[key]
        best = data["best"]

        trans_lookup = {item["label"]: item for item in data["transverse_options"] if item.get("label")}
        long_lookup = {item["label"]: item for item in data["longitudinal_options"] if item.get("label")}

        req = requested_map.get(key)
        span_req = requested_span_map.get(span_id)
        selected_transverse_label: str | None = None
        selected_longitudinal_label: str | None = None
        selected_base_longitudinal_label: str | None = None
        selected_additional_longitudinal_label: str | None = None

        if req is not None:
            if req.transverse_label:
                selected_transverse_label = req.transverse_label.strip()
            if req.longitudinal_label:
                selected_longitudinal_label = req.longitudinal_label.strip()
            if req.base_longitudinal_label:
                selected_base_longitudinal_label = req.base_longitudinal_label.strip()
            if req.additional_longitudinal_label:
                selected_additional_longitudinal_label = req.additional_longitudinal_label.strip()
            if req.option is not None and (not selected_transverse_label or not selected_longitudinal_label):
                option_row = next((row for row in data["rows"] if int(row["option"]) == int(req.option)), None)
                if option_row is None:
                    raise AppError(
                        message=f"La opcion {req.option} no existe para la region {span_id}/{region_id}.",
                        status_code=422,
                        code="invalid_selection",
                    )
                selected_transverse_label = selected_transverse_label or option_row["transverse_label"]
                selected_longitudinal_label = selected_longitudinal_label or option_row["longitudinal_label"]
                selected_base_longitudinal_label = selected_base_longitudinal_label or str(
                    option_row.get("base_longitudinal_label") or ""
                ).strip()
                selected_additional_longitudinal_label = selected_additional_longitudinal_label or str(
                    option_row.get("additional_longitudinal_label") or ""
                ).strip()

        if not selected_longitudinal_label and span_req is not None:
            span_options = span_longitudinal_options.get(span_id, [])
            option_rows = span_option_rows.get(span_id, {})
            if span_req.longitudinal_label:
                selected_longitudinal_label = span_req.longitudinal_label.strip()
            elif span_req.option is not None:
                span_option_number = int(span_req.option)
                option_row = (option_rows.get(span_option_number) or {}).get(region_id)
                if option_row is not None:
                    selected_longitudinal_label = str(option_row.get("longitudinal_label") or "").strip()
                    selected_base_longitudinal_label = selected_base_longitudinal_label or str(
                        option_row.get("base_longitudinal_label") or ""
                    ).strip()
                    selected_additional_longitudinal_label = selected_additional_longitudinal_label or str(
                        option_row.get("additional_longitudinal_label") or ""
                    ).strip()
                else:
                    option_index = span_option_number - 1
                    if option_index < 0 or option_index >= len(span_options):
                        raise AppError(
                            message=f"La opcion {span_req.option} no existe para el vano {span_id}.",
                            status_code=422,
                            code="invalid_selection",
                        )
                    selected_longitudinal_label = str(span_options[option_index]["label"])

        selected_longitudinal_label = selected_longitudinal_label or str(best.get("longitudinal_label") or "").strip()
        if not selected_transverse_label:
            compatible_rows = [
                row
                for row in data["rows"]
                if row["longitudinal_label"] == selected_longitudinal_label
            ]
            compatible_rows = _filter_longitudinal_labels(
                compatible_rows, selected_base_longitudinal_label, selected_additional_longitudinal_label,
            )
            if compatible_rows:
                compatible_rows = sorted(
                    compatible_rows,
                    key=lambda row: (
                        float(row.get("weight_total_kg") or 0.0),
                        int(row.get("option") or 0),
                    ),
                )
                selected_transverse_label = str(compatible_rows[0].get("transverse_label") or "").strip()
            else:
                selected_transverse_label = str(best.get("transverse_label") or "").strip()

        if selected_transverse_label not in trans_lookup:
            raise AppError(
                message=f"El estribo '{selected_transverse_label}' no existe para la region {span_id}/{region_id}.",
                status_code=422,
                code="invalid_selection",
            )
        if selected_longitudinal_label not in long_lookup:
            raise AppError(
                message=f"El refuerzo longitudinal '{selected_longitudinal_label}' no existe para la region {span_id}/{region_id}.",
                status_code=422,
                code="invalid_selection",
            )

        selected_combo_candidates = [
            row
            for row in data["rows"]
            if row["transverse_label"] == selected_transverse_label
            and row["longitudinal_label"] == selected_longitudinal_label
        ]
        selected_combo_candidates = _filter_longitudinal_labels(
            selected_combo_candidates, selected_base_longitudinal_label, selected_additional_longitudinal_label,
        )
        selected_combo = (
            sorted(
                selected_combo_candidates,
                key=lambda row: (
                    float(row.get("weight_total_kg") or 0.0),
                    int(row.get("option") or 0),
                ),
            )[0]
            if selected_combo_candidates
            else None
        )
        if selected_combo is None:
            raise AppError(
                message=(
                    f"La combinacion seleccionada no existe para la region {span_id}/{region_id} "
                    f"(transversal='{selected_transverse_label}', longitudinal='{selected_longitudinal_label}')."
                ),
                status_code=422,
                code="invalid_selection",
            )

        best_weight = float(best.get("weight_total_kg") or 0.0)
        selected_transverse_weight = selected_combo["weight_transverse_kg"]
        selected_longitudinal_weight = selected_combo["weight_longitudinal_kg"]
        selected_weight = selected_combo["weight_total_kg"]
        diff_pct = ((selected_weight - best_weight) / best_weight * 100.0) if best_weight > 0 else None

        resolved_rows.append(
            {
                "span_id": span_id,
                "region_id": region_id,
                "best_option": best["option"],
                "selected_option": int(selected_combo["option"]),
                "best_transverse_label": best.get("transverse_label") or "",
                "best_longitudinal_label": best.get("longitudinal_label") or "",
                "selected_transverse_label": selected_transverse_label,
                "selected_longitudinal_label": selected_longitudinal_label,
                "selected_base_longitudinal_label": str(selected_combo.get("base_longitudinal_label") or "").strip(),
                "selected_additional_longitudinal_label": str(
                    selected_combo.get("additional_longitudinal_label") or ""
                ).strip(),
                "best_weight_kg": best_weight,
                "selected_weight_kg": selected_weight,
                "selected_transverse_weight_kg": selected_transverse_weight,
                "selected_longitudinal_weight_kg": selected_longitudinal_weight,
                "difference_kg": selected_weight - best_weight,
                "difference_pct": diff_pct,
            }
        )

    return resolved_rows
