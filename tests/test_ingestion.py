from __future__ import annotations

import unittest

from app.core.errors import InvalidUploadError
from app.domain.ingestion import (
    parse_optimization_overrides,
    parse_pairs_json,
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


if __name__ == "__main__":
    unittest.main()
