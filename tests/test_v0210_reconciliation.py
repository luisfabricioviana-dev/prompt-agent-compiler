import base64
import codecs
import hashlib
import unittest

import reconciliation_v0_2_10 as reconciliation


class ReconciliationContractTests(unittest.TestCase):
    def test_recovered_v029_bundle_source_and_digest_are_pinned(self):
        self.assertEqual(
            reconciliation.RECOVERED_V029_SOURCE_KIND,
            "google_drive_recovered_bundle",
        )
        self.assertEqual(
            reconciliation.RECOVERED_V029_DRIVE_FILE_ID,
            "1a6h9u7JtEYGkbK8nzVE3scClYUvO9E4T",
        )
        self.assertEqual(
            reconciliation.RECOVERED_V029_ARCHIVE_SHA256,
            "a0986c482309b6de7bf1bf90be3db9cba546f4cd0703813fe8b2161508fede7a",
        )

    def test_promotable_tree_excludes_blind_holdout_material(self):
        from pathlib import Path

        self.assertFalse(
            Path("recovery/prompt_agent_compiler_v0_2_9_recovered.zip").exists()
        )
        self.assertTrue(Path("recovered_v0_2_9").is_dir())
        self.assertFalse(
            Path("recovered_v0_2_9/blind_holdout_v0_2_9.json").exists()
        )

    def test_transport_reconstruction_is_digest_bound(self):
        payload = b"prompt-agent-compiler-v0.2.9"
        encoded = base64.b64encode(payload).decode("ascii")
        chunks = [encoded[:7], encoded[7:19], encoded[19:]]
        expected = hashlib.sha256(payload).hexdigest()

        restored = reconciliation.reconstruct_archive(
            chunks,
            expected_sha256=expected,
        )

        self.assertEqual(restored, payload)

        with self.assertRaisesRegex(ValueError, "archive_digest_mismatch"):
            reconciliation.reconstruct_archive(
                chunks,
                expected_sha256="0" * 64,
            )

    def test_rot13_transport_decoder_is_retained_for_archaeological_replay(self):
        payload = b"rot13 transport fixture"
        encoded = base64.b64encode(payload).decode("ascii")
        transported = codecs.encode(encoded, "rot_13")
        chunks = [transported[:5], transported[5:13], transported[13:]]
        expected = hashlib.sha256(payload).hexdigest()

        restored = reconciliation.reconstruct_rot13_archive(
            chunks,
            expected_sha256=expected,
        )

        self.assertEqual(restored, payload)


    def test_public_safe_recovered_tree_contract_passes(self):
        from pathlib import Path

        result = reconciliation.verify_public_safe_recovered_tree(
            Path("recovered_v0_2_9")
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["json_artifacts"], 26)
        self.assertEqual(result["freeze_files_checked"], 11)
        self.assertFalse(result["holdout_present"])

    def test_public_safe_contract_rejects_holdout_material(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "blind_holdout_v0_2_9.json").write_text("{}", encoding="utf-8")
            result = reconciliation.verify_public_safe_recovered_tree(root)

        self.assertFalse(result["valid"])
        self.assertTrue(result["holdout_present"])
        self.assertIn("blind_holdout_present", result["reasons"])


if __name__ == "__main__":
    unittest.main()
