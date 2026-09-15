# Architecture

This repository follows a layered engineering-service architecture focused on traceability and backward compatibility.

## Layer map

1. `app/routers`
- HTTP transport only.
- No engineering formulas.
- Maps domain/application errors to HTTP responses.

2. `app/services`
- Application orchestration and job flow.
- Coordinates ingestion, case build, execution and artifact exposure.
- Does not implement structural formulas.

3. `app/domain`
- Form ingestion and domain-level payload assembly for API entrypoints.
- Reusable business/domain guards used by API services.

4. `src/rc_shear_torsion/domain`
- Core engineering domain validation (rules and normalized errors).
- Single source of truth for engineering/business constraints.

5. `src/rc_shear_torsion`
- Engineering engine and optimization.
- Deterministic calculation and report generation.
- CLI wrapper calls engine without duplicating API logic.

6. `tests`
- Contract tests (API), domain tests, and end-to-end smoke tests.
- Regression tests for previous bugs and compatibility boundaries.

## Runtime flow

1. Request enters router (`/v1/jobs` or `/v1/jobs/from-form`).
2. Service validates transport payload and reads uploads.
3. Domain layer builds/validates canonical `case_payload`.
4. Engine runs calculations and optimization.
5. Reports/artifacts are generated in job output directory.
6. API exposes status, preview, case, zip and per-artifact downloads.

## Compatibility contract

1. Preserve endpoint signatures and response fields unless a breaking change is explicitly approved.
2. Preserve report file names and worksheet headers used by tests/integrations.
3. Preserve CLI contract (`python -m rc_shear_torsion.run ...`) and exit semantics.

## Separation rules

1. Schemas/Pydantic:
- Type coercion, required fields, shape validation.

2. Domain validation:
- Engineering/business ranges, dependencies and consistency rules.

3. Engine:
- Calculation and optimization only.
- Minimal unavoidable guard rails are acceptable.

4. UI:
- Presentation and payload assembly only.
- Never duplicate engineering formulas.


## Span-Coupled Longitudinal Mode

1. Activation:
- `optimization.longitudinal_mode` supports:
  - `legacy_region_independent` (default),
  - `span_coupled`.

2. Domain inputs:
- `optimization.variables.longitudinal_bar_counts` must be even in `span_coupled`.

3. Engine behavior:
- `engine` routes to `optimize_span_coupled` only when mode is `span_coupled`.
- Legacy mode remains unchanged.

4. Selection contract:
- Region-level `selections` remains valid.
- Span-level `span_selections` is optional for coupled mode.

5. Preview contract:
- Region options remain available.
- Optional span block `span_option_choices` is exposed for coupled spans.


