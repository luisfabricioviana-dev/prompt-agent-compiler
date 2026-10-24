import hashlib
import unittest
from rea_admission_canary import inspect_candidate

class AdmissionCanaryTests(unittest.TestCase):
    def test_candidate_is_blocked_without_independent_provenance(self):
        payload = b"test fixture"
        result = inspect_candidate(payload)
        self.assertEqual(result["state"], "BLOCKED")
        self.assertIn("provenance_unverified", result["reasons"])
        self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertFalse(result["dispatch_performed"])
        self.assertFalse(result["publication_performed"])

    def test_secret_claim_does_not_bypass_provenance(self):
        result = inspect_candidate(b"candidate")
        self.assertNotEqual(result["state"], "ADMISSIBLE_CANDIDATE")

if __name__ == "__main__":
    unittest.main()
