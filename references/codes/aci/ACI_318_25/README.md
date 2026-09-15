# ACI 318-25 reference

ACI 318-25 is the primary governing normative reference for ACI rules implemented by StructureLab.

The official document must be obtained and placed manually in the `private/` directory. The PDF is not distributed with this repository and must not be committed to version control.

Every implemented normative rule must identify the exact Code section and subsection used. Equations and applicability conditions must be verified from the local governing document before implementation; they must not be reconstructed from memory.

Commentary and secondary documents may help explain a provision, but they do not automatically replace or override the Code. Their use must be identified separately from the governing Code provision.

If the available reference does not resolve a rule or its applicability unambiguously, implementation of that rule must stop. Record and report the ambiguity instead of assuming an interpretation.

Use `SOURCE.yaml` for source metadata, `IMPLEMENTED_RULES.yaml` for the auditable implementation registry, and `ERRATA.md` for future official errata and interpretation changes.
