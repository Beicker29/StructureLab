# ENGINEERING_REPO_STANDARD

This document defines the coding standard used in this repository and expected in future internal engineering repos.

## 1. Architecture baseline

1. Keep calculation engine independent from web framework.
2. Keep domain validation reusable across API, CLI and batch flows.
3. Keep transport concerns (HTTP/UI) outside calculation modules.
4. Keep reports/exporters downstream of canonical results.

## 2. Layer responsibilities

1. `schemas`
- Validate shape, primitive types, required fields.

2. `domain`
- Validate engineering/business rules.
- Produce normalized errors (`code`, `field`, `message`, `severity`).

3. `engine`
- Compute outputs from validated inputs.
- No HTTP concerns.

4. `services`
- Orchestrate workflow and side effects.
- Call domain + engine; do not duplicate formulas/rules.

5. `routers` and `ui`
- Handle UX/transport mapping.
- Never host structural formulas.

## 3. Error model

1. Domain errors must be structured and mappable to API and CLI.
2. API returns readable contracts (`error`, `message`, `details`).
3. CLI prints actionable domain errors and exits with deterministic codes.

## 4. Testing baseline

1. Domain tests for rules and edge cases.
2. API contract tests for status/error/download endpoints.
3. End-to-end smoke tests with real fixture inputs.
4. Regression test required for every production bug fix.

## 5. Change policy

1. Prefer incremental refactors.
2. Preserve public contracts by default.
3. If numerical behavior changes, document before/after evidence.
4. Avoid broad rewrites in production branches.

## 6. Observability and traceability

1. Job lifecycle states must remain explicit (`queued`, `running`, `completed`, `failed`).
2. Persist case input, artifacts and execution logs per job.
3. Keep outputs reproducible from stored case + inputs.

## 7. Frontend policy for engineering tools

1. UI assembles payloads and displays results; backend keeps engineering authority.
2. Prefer guided forms over raw JSON editing when possible.
3. Show explicit loading/error/success states and actionable messages.
4. Keep technical labels and units visible.
