# Engineering Repo Template

This file is a reusable starting point for internal engineering repositories.

## Purpose

Use this template when the project needs:

1. A calculation engine independent from web/UI frameworks.
2. A reusable domain validation layer.
3. API, CLI, and optional UI over the same engineering core.
4. Traceable outputs, reproducible runs, and regression-safe changes.

## Recommended structure

```text
repo/
  app/
    core/
      config.py
      errors.py
    domain/
      __init__.py
      ingestion.py
      case_payload.py
    routers/
      __init__.py
      health.py
      jobs.py
      ui.py
    schemas/
      __init__.py
      common.py
      jobs.py
    services/
      __init__.py
      case_builder_service.py
      job_service.py
      preview_service.py
    ui/
      templates/
        ui.html
      static/
        ui.css
        ui.js
    main.py
  src/
    project_name/
      domain/
        __init__.py
        errors.py
        rules.py
        validation.py
      __init__.py
      models.py
      engine.py
      optimization.py
      results_model.py
      report.py
      io.py
      run.py
  tests/
    test_api.py
    test_core.py
    test_ingestion.py
  examples/
    case_0001/
      case.json
  scripts/
    smoke_api.py
  storage/
  .github/
    workflows/
  README.md
  ARCHITECTURE.md
  ENGINEERING_REPO_STANDARD.md
  pyproject.toml
  requirements.txt
  render.yaml
```

## Layer rules

### `src/project_name`

- Owns engineering logic.
- No FastAPI, no HTML, no transport concerns.
- Must run from CLI and from services without behavioral differences.

### `src/project_name/domain`

- Owns engineering and business rules.
- Exposes normalized domain errors.
- Must be the single source of truth for constraints.

### `app/services`

- Orchestrates workflows, files, jobs, and side effects.
- Calls domain + engine.
- Must not contain structural formulas.

### `app/routers`

- Handles HTTP request/response mapping only.
- Converts app/domain errors to stable API contracts.

### `app/ui`

- Presentation layer only.
- Builds compatible payloads for backend.
- Never hosts engineering formulas.

### `tests`

- Protects public contracts and numerical behavior.
- Every production bug fix should add a regression test.

## Minimal file responsibilities

### `src/project_name/models.py`

- Canonical typed models for engine input/output.
- Path resolution and typed configuration helpers when needed.

### `src/project_name/engine.py`

- High-level calculation pipeline.
- Reads validated models, executes computation, emits canonical results.

### `src/project_name/optimization.py`

- Search strategies only.
- Exhaustive, GA, or hybrid strategies should be swappable here.

### `src/project_name/results_model.py`

- Canonical result model before export.
- Derived checks, weights, summaries, and reusable computed values.

### `src/project_name/report.py`

- Exporters only.
- Excel/CSV/ZIP generation from canonical results.

### `app/domain/case_payload.py`

- Assembles normalized payloads from transport-layer inputs.
- Validates them through the engineering domain before execution.

### `app/services/job_service.py`

- Job state management.
- Artifact registration.
- Execution logging and failure observability.

## Required API contract pattern

For errors, keep a stable shape:

```json
{
  "error": "domain_validation_error",
  "message": "Validation failed",
  "details": [
    {
      "code": "invalid_range",
      "field": "optimization.genetic_algorithm.population_size",
      "message": "population_size must be >= 4",
      "severity": "error"
    }
  ]
}
```

For long-running work, keep explicit job states:

- `queued`
- `running`
- `completed`
- `failed`

## Required development rules

1. No engineering formulas in endpoints.
2. No duplicated validation between API, CLI, and engine.
3. No report generation logic mixed with domain rules.
4. No giant files when a concern can be extracted safely.
5. No breaking changes without explicit approval and regression coverage.

## Required testing baseline

1. Domain validation tests.
2. Core calculation tests.
3. API contract tests.
4. End-to-end smoke test using a real fixture.
5. Regression tests for previous bugs.

## Bootstrap checklist

1. Create typed domain models.
2. Define normalized domain errors.
3. Implement validation rules before adding UI complexity.
4. Build engine against validated input only.
5. Add canonical result model before exporters multiply.
6. Add CLI for local reproducibility.
7. Add API only after core and validation are stable.
8. Add UI only as a thin client over stable API contracts.
9. Add smoke tests for deploy path.
10. Add architecture docs before the repo grows.

## README skeleton

Every new repo should document:

1. What the engine computes.
2. Quick start.
3. CLI usage.
4. API usage.
5. Example fixture.
6. Output artifacts.
7. Environment variables.
8. Deploy instructions.
9. Architecture links.

## Naming conventions

Use direct technical names:

- `build_case_payload_from_form`
- `validate_case_payload`
- `run_case`
- `write_summary`
- `render_preview`

Avoid vague names:

- `process_data`
- `handle_all`
- `do_work`
- `manager`

## Decision rule for future repos

If a new feature answers one of these questions, it belongs here:

- "How is the input shaped?" -> `schemas`
- "Is the engineering rule valid?" -> `domain`
- "How is it calculated?" -> `engine`
- "How is the workflow executed?" -> `services`
- "How is it exposed?" -> `routers` or `ui`
