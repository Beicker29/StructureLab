"""Central numerical tolerances used by the engineering domain."""

# Demands are expressed in the units already normalized by the ETABS reader.
# This is a numerical zero tolerance, not a normative design threshold.
torsion_zero_tolerance: float = 1.0e-9

# Used only to absorb floating-point roundoff in dimensional comparisons.
# This is not a construction tolerance or a permitted ACI deviation. Units: mm.
dimensional_comparison_tolerance_mm: float = 1.0e-9

# Backward-compatible name used by the spacing rules.
spacing_comparison_tolerance_mm: float = dimensional_comparison_tolerance_mm

# Nominal reinforcement grades are discrete ACI inputs. This tolerance only
# absorbs serialization roundoff; it is not a permitted material deviation.
# Units: MPa.
reinforcement_grade_tolerance_mpa: float = 1.0e-9
