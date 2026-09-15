# AGENTS.md — StructureLab

## 1. Purpose

This file defines the permanent working rules for AI coding agents operating in the StructureLab repository.

These instructions apply to all modifications unless a more specific `AGENTS.md` exists inside a subdirectory.

The primary goals are:

- engineering correctness;
- traceability;
- reproducibility;
- maintainable architecture;
- explicit assumptions;
- preservation of validated behavior;
- safe incremental development.

StructureLab is engineering software. Numerical results and code changes must therefore be auditable.

---

# 2. Sources of truth

Before making changes, determine which project documents govern the task.

Priority:

1. explicit user instruction for the current task;
2. `AGENTS.md`;
3. task-specific technical plans or specifications;
4. `ARCHITECTURE.md`;
5. tests and documented API contracts;
6. `README.md`;
7. existing implementation.

For the current shear/torsion refactor:

`STRUCTURELAB_REFACTOR_PLAN.md`

is the technical source of truth.

Do not silently override decisions established in that document.

---

# 3. Before editing

Before modifying code:

1. read this `AGENTS.md`;
2. read the relevant technical specification;
3. inspect the relevant modules;
4. run `git status`;
5. identify the current branch;
6. detect existing local changes;
7. identify applicable tests;
8. search for all consumers of code that may be modified.

Do not overwrite, revert, or discard work that existed before the task.

If existing modifications overlap with the requested work, preserve them unless explicitly instructed otherwise.

---

# 4. Work incrementally

Prefer small, verifiable changes.

When a task is divided into phases:

- implement one phase at a time;
- do not anticipate later phases unless necessary for compatibility;
- complete the tests and verification of the current phase before proceeding.

Do not combine:

- architectural refactors;
- engineering formula changes;
- API migrations;
- unrelated cleanup;

in the same change unless the specification explicitly requires it.

---

# 5. Engineering rules

## 5.1 No silent engineering assumptions

Never invent:

- ACI interpretations;
- constitutive assumptions;
- units;
- tolerances;
- default values;
- applicability conditions;
- extrapolation rules.

If a normative or engineering decision is ambiguous and cannot be resolved from the project sources, stop that specific rule and report the ambiguity.

Continue with independent work that is not blocked.

---

## 5.2 Missing information

Missing engineering information must never silently become compliance.

When a rule could apply but required data are unavailable, use the appropriate explicit state such as:

`NOT_EVALUATED`

rather than:

`PASS`

when the domain model supports those states.

---

## 5.3 Units

Units must be explicit at domain boundaries.

Avoid formulas whose expected units cannot be determined from:

- variable names;
- type/model definition;
- documentation;
- surrounding code.

Do not introduce implicit conversions.

Centralize unit conversions whenever practical.

---

## 5.4 Numerical tolerances

Do not scatter arbitrary tolerances through the code.

Use centralized, named tolerances.

Numerical comparisons must be reproducible.

If a new tolerance is needed, document:

- purpose;
- units;
- default value;
- reason for the selected magnitude.

---

# 6. Architecture principles

## 6.1 Separate engineering domains

Keep separate:

- input/import normalization;
- engineering domain models;
- code provisions;
- candidate generation;
- candidate evaluation;
- optimization;
- reporting;
- user interface.

The UI must capture inputs and display results.

It must not decide engineering applicability.

---

## 6.2 Pure engineering rules

Whenever practical, engineering rules should be pure functions.

A rule should receive explicit input data and return a structured result.

It should not depend directly on:

- UI state;
- files;
- global mutable state;
- optimization algorithms;
- HTML;
- Excel;
- FastAPI.

---

## 6.3 Single source for formulas

Each engineering formula should have one authoritative implementation.

Do not duplicate formulas between:

- exhaustive search;
- genetic optimization;
- reporting;
- API;
- UI;
- validation utilities.

Shared behavior must consume the same domain evaluator.

---

## 6.4 DRY without hiding engineering

Apply DRY to:

- constants;
- units;
- catalogs;
- formulas;
- applicability decisions;
- common validation.

Do not create abstractions that obscure the governing engineering equation or make auditing difficult.

Readable engineering code is preferred over overly generic abstractions.

---

# 7. Optimization

Optimization algorithms must search the design space.

They must not contain independent implementations of engineering rules.

Whenever multiple optimization strategies exist, such as:

- exhaustive search;
- genetic algorithm;

they must use the same candidate evaluation function.

For stochastic methods:

- use configurable seeds;
- preserve reproducibility;
- report the seed when relevant.

For sufficiently small cases, stochastic results should be benchmarked against exhaustive search.

---

# 8. Compatibility

Maintain backward compatibility when technically reasonable.

Compatibility should normally be handled at input boundaries through:

- normalization;
- migration;
- aliases;
- explicit defaults.

Do not preserve obsolete duplicate calculation engines merely to maintain compatibility.

New optional fields require explicit and safe defaults.

---

# 9. Testing

Before changing behavior:

- identify existing tests;
- add characterization tests when necessary.

After changes:

- run focused tests;
- run the relevant module test suite;
- run the complete suite when practical.

Tests should favor:

- deterministic inputs;
- explicit expected results;
- one behavior per test;
- engineering edge cases;
- regression cases.

Do not write tests that permanently encode a known engineering bug as correct behavior.

Legacy behavior that is temporarily characterized must be clearly identified as legacy.

---

# 10. Traceability

Engineering results should be explainable.

Where applicable, results should expose:

- input source;
- station or location;
- governing demand;
- capacity;
- governing rule;
- applicable code section;
- required value;
- provided value;
- units;
- status;
- reason for applicability;
- missing data;
- optimization method.

Avoid returning only a final boolean when richer traceability is required.

---

# 11. Refactoring

Before deleting or moving code:

1. search for every reference;
2. identify all consumers;
3. migrate consumers;
4. run relevant tests;
5. only then remove obsolete code.

Do not keep:

- dead code;
- duplicate implementations;
- unused adapters;
- stale compatibility layers;

without a documented need.

Temporary adapters must be clearly identified and eventually removed.

---

# 12. Git safety

Unless explicitly requested:

- do not commit;
- do not push;
- do not reset;
- do not rebase;
- do not force checkout;
- do not discard uncommitted changes.

At the beginning and end of meaningful tasks, inspect:

`git status`

Use `git diff` before reporting completion.

---

# 13. Documentation

Update documentation when behavior, architecture, API contracts, or limitations change.

Documentation must describe the actual implementation.

Known limitations should be explicit.

Do not document unimplemented functionality as available.

---

# 14. Completion report

For substantial changes, finish with:

## Files changed
List files and purpose.

## Engineering decisions
List relevant assumptions and decisions.

## Tests added or modified
Explain what each protects.

## Verification
List commands executed and results.

## Compatibility
State any impact on previous files or APIs.

## Risks / unresolved items
Identify remaining engineering or software concerns.

Do not claim completion if tests required by the task are failing.

---

# 15. Current StructureLab refactor

For the shear/torsion refactor, always read:

`STRUCTURELAB_REFACTOR_PLAN.md`

before making changes.

That document defines, among other things:

- physical demand scenarios by source and station;
- prohibition of independent artificial demand envelopes;
- torsion states;
- DMI / DMO / DES behavior;
- ACI rule modularization;
- ties applicability;
- optimization integration;
- result traceability;
- test requirements;
- temporary exclusion of `bt+d`.

Do not alter those decisions without explicit approval.

---

# 16. Core principle

StructureLab should not merely produce a result.

It should make it possible for another engineer to determine:

**what was calculated, from which data, using which equation or rule, under which assumptions, and why that result governed.**

---

## Governing technical references

1. For ACI rules, consult the local ACI 318-25 reference first.
2. Do not implement an ACI equation from memory.
3. Identify the exact section and subsection before programming a rule.
4. Verify applicability conditions before evaluating a rule.
5. Distinguish Code provisions from Commentary material.
6. Each normative rule must have exactly one implementation in the codebase.
7. Each normative rule must have a unit test.
8. Results must preserve traceability to the section used.
9. If the governing reference does not confirm a rule, do not assume it.
10. Report the ambiguity and leave the rule unimplemented.

The governing local metadata and audit registry for ACI 318-25 are located in:

`references/codes/aci/ACI_318_25/`

For the current StructureLab refactor, `STRUCTURELAB_REFACTOR_PLAN.md` is the governing technical plan. Work only within the phase explicitly authorized by the user.
