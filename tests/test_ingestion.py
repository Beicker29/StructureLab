from __future__ import annotations

import unittest

from app.core.errors import InvalidUploadError
from app.domain.ingestion import (
    parse_optimization_overrides,
    parse_pairs_json,
    parse_span_layout_json,
    resolve_span_pairs,
)


class IngestionDomainTests(unittest.TestCase):
    def test_parse_pairs_json_rejects_invalid_payload(self) -> None:
        with self.assertRaises(InvalidUploadError):
            parse_pairs_json('{"seismic":"1"}')

    def test_resolve_span_pairs_uses_numeric_natural_order_on_shared_names(self) -> None:
        pairs = resolve_span_pairs(
            seismic_names={"10", "2", "A"},
            gravity_names={"A", "2", "10"},
            frame_names_csv=None,
            frame_pairs_json=None,
        )
        self.assertEqual([pair["seismic"] for pair in pairs], ["2", "10", "A"])
        self.assertEqual([pair["gravity"] for pair in pairs], ["2", "10", "A"])

    def test_resolve_span_pairs_validates_pair_membership(self) -> None:
        with self.assertRaises(InvalidUploadError):
            resolve_span_pairs(
                seismic_names={"1", "2"},
                gravity_names={"1", "2"},
                frame_names_csv=None,
                frame_pairs_json='[{"id":"S1","seismic":"9","gravity":"1"}]',
            )

    def test_parse_optimization_overrides_requires_object(self) -> None:
        with self.assertRaises(InvalidUploadError):
            parse_optimization_overrides('["bad"]')

        payload = parse_optimization_overrides('{"enabled": false, "objective": "min_weight"}')
        self.assertEqual(payload["enabled"], False)
        self.assertEqual(payload["objective"], "min_weight")

    def test_parse_span_layout_json_accepts_regions_with_confinado_flag(self) -> None:
        raw = """
        [
          {
            "id": "S1",
            "seismic": "190",
            "gravity": "190",
            "c_ratio_extremos": 0.2,
            "support_left_mm": 200,
            "support_right_mm": 250,
            "regions": [
              {"id": "R1", "from": 0.0, "to": 0.2, "confinado": true},
              {"id": "R2", "from": 0.2, "to": 0.8, "confinado": false},
              {"id": "R3", "from": 0.8, "to": 1.0, "confinado": true}
            ]
          }
        ]
        """
        parsed = parse_span_layout_json(raw)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["id"], "S1")
        self.assertEqual(parsed[0]["support_right_mm"], 250.0)
        self.assertEqual(parsed[0]["regions"][0]["type"], "C")
        self.assertEqual(parsed[0]["regions"][1]["type"], "NC")

    def test_parse_span_layout_json_accepts_clear_length_override_aliases(self) -> None:
        raw = """
        [
          {
            "id": "S1",
            "seismic": "190",
            "gravity": "190",
            "support_left_mm": 200,
            "support_right_mm": 250,
            "L_libre_real_mm": 5370,
            "regions": [
              {"id": "R1", "from": 0.0, "to": 1.0, "type": "C"}
            ]
          }
        ]
        """
        parsed = parse_span_layout_json(raw)
        self.assertEqual(parsed[0]["clear_length_mm"], 5370.0)

    def test_parse_span_layout_json_rejects_non_contiguous_regions(self) -> None:
        raw = """
        [
          {
            "id": "S1",
            "seismic": "190",
            "gravity": "190",
            "support_left_mm": 200,
            "support_right_mm": 250,
            "regions": [
              {"id": "R1", "from": 0.0, "to": 0.3, "type": "C"},
              {"id": "R2", "from": 0.4, "to": 1.0, "type": "NC"}
            ]
          }
        ]
        """
        with self.assertRaises(InvalidUploadError):
            parse_span_layout_json(raw)


if __name__ == "__main__":
    unittest.main()

