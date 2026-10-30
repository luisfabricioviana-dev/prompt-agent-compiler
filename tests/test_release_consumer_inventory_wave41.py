"""Wave 41: internal release surface inventory must not claim full coverage."""
import unittest
from contracts.release_consumer_inventory import INVENTORY, review_consumer_coverage


class ReleaseConsumerInventoryTests(unittest.TestCase):
    def test_known_release_paths_are_classified(self):
        names = {entry.consumer for entry in INVENTORY}
        self.assertIn("contracts.rea_release_node.ReleaseNode.execute", names)
        self.assertIn("contracts.rea_release_node.ReleaseNode.inspect_delivery", names)
        self.assertIn("compiler.run_optional_rea_release", names)
        self.assertIn("compiler.run_optional_rea_github_release", names)

    def test_read_only_and_dispatch_surfaces_are_distinct(self):
        for entry in INVENTORY:
            if entry.operation == "optional_dispatch":
                self.assertFalse(entry.governed)
            if entry.operation == "read_only_audit":
                self.assertTrue(entry.governed)

    def test_strict_adoption_gate_fails_closed(self):
        result = review_consumer_coverage(require_all_governed=True)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["reason"], "legacy_consumers_not_migrated")

    def test_default_does_not_claim_external_coverage(self):
        result = review_consumer_coverage()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["reason"], "external_consumers_unverified")


if __name__ == "__main__":
    unittest.main()
