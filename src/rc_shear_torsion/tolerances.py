"""Central numerical tolerances used while importing demand data."""

# Demands are expressed in the units already normalized by the ETABS reader.
# This is a numerical zero tolerance, not a normative design threshold.
torsion_zero_tolerance: float = 1.0e-9
