"""Wave38: legacy objects cannot become delivery or dispatch authority."""
import unittest
from contracts.legacy_release_result_quarantine import classify_legacy_release_result
from contracts.rea_pipeline import PipelineResult


class LegacyQuarantineTests(unittest.TestCase):
    def test_pipeline_observer_confirmation_is_not_governed(self):
        result = classify_legacy_release_result(
            PipelineResult("CONFIRMED_BY_OBSERVER", "DELIVERY_CONFIRMED", "a"*64))
        self.assertEqual(result.status, "BLOCK")
        self.assertEqual(result.reason, "governed_audit_required")
        self.assertIs(result.dispatch_authorized, False)

    def test_dictionary_consistent_is_not_evidence(self):
        for value in ({"state": "CONSISTENT"}, {"state": "CONFIRMED"},
                      {"state": "SUCCESS"}, {"state": True}):
            with self.subTest(value=value):
                decision = classify_legacy_release_result(value)
                self.assertEqual(decision.status, "BLOCK")
                self.assertFalse(decision.dispatch_authorized)

    def test_tuple_confirmation_is_not_evidence(self):
        result = classify_legacy_release_result(("DELIVERY_CONFIRMED", "ok"))
        self.assertEqual(result.status, "BLOCK")

    def test_uncertain_legacy_states_preserve_no_retry(self):
        for value in ({"state": "IN_DOUBT"}, ("UNCERTAIN", "timeout"),
                      PipelineResult("DISPATCHED", "pending", "a"*64)):
            self.assertEqual(classify_legacy_release_result(value).status, "IN_DOUBT")

    def test_unrecognized_structures_block(self):
        for value in (None, object(), [], ("CONFIRMED",), {"status": "CONFIRMED"}):
            self.assertEqual(classify_legacy_release_result(value).status, "BLOCK")


if __name__ == "__main__":
    unittest.main()
