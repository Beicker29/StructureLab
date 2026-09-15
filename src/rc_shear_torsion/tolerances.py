"""Central numerical tolerances used by the engineering domain."""

# Demands are expressed in the units already normalized by the ETABS reader.
# This is a numerical zero tolerance, not a normative design threshold.
torsion_zero_tolerance: float = 1.0e-9

# Used only to absorb floating-point roundoff when comparing a selected
# spacing against an ACI maximum spacing. Units: mm.
spacing_comparison_tolerance_mm: float = 1.0e-9

# Nominal reinforcement grades are discrete ACI inputs. This tolerance only
# absorbs serialization roundoff; it is not a permitted material deviation.
# Units: MPa.
reinforcement_grade_tolerance_mpa: float = 1.0e-9
