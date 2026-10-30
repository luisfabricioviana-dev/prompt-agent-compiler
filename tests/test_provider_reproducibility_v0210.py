import unittest
from datetime import datetime, timezone

from contracts.semantic_provider_config import (
    SemanticProviderConfig,
    build_configured_provider,
)
from contracts.evaluation_run_manifest import EvaluationRunManifest


class FakeProvider:
    def __init__(self, client=None, model=None, prompt=None):
        self.client = client
        self.model = model
        self.prompt = prompt


class SemanticProviderConfigTests(unittest.TestCase):
    def test_model_id_is_required_and_has_no_implicit_default(self):
        with self.assertRaisesRegex(ValueError, "semantic_model_required"):
            SemanticProviderConfig.from_env({})

    def test_environment_model_is_preserved_exactly(self):
        cfg = SemanticProviderConfig.from_env(
            {
                "PAC_SEMANTIC_MODEL": "provider-model-snapshot-2026-10-30",
                "PAC_SEMANTIC_PROVIDER": "openai-responses",
            }
        )
        self.assertEqual(cfg.model_id, "provider-model-snapshot-2026-10-30")
        self.assertEqual(cfg.provider, "openai-responses")

    def test_builder_passes_explicit_model_to_provider(self):
        cfg = SemanticProviderConfig(
            provider="openai-responses",
            model_id="explicit-model",
        )

        provider = build_configured_provider(
            cfg,
            FakeProvider,
            client="client",
            prompt="prompt",
        )

        self.assertEqual(provider.model, "explicit-model")
        self.assertEqual(provider.client, "client")
        self.assertEqual(provider.prompt, "prompt")

    def test_config_rejects_empty_provider_or_model(self):
        with self.assertRaisesRegex(ValueError, "semantic_provider_required"):
            SemanticProviderConfig(provider="", model_id="x")
        with self.assertRaisesRegex(ValueError, "semantic_model_required"):
            SemanticProviderConfig(provider="openai-responses", model_id=" ")


class EvaluationRunManifestTests(unittest.TestCase):
    def test_manifest_records_reproducibility_identity(self):
        cfg = SemanticProviderConfig(
            provider="openai-responses",
            model_id="model-snapshot",
            request_parameters={"reasoning": "medium"},
        )
        started = datetime(2026, 10, 30, 15, 0, tzinfo=timezone.utc)

        manifest = EvaluationRunManifest.create(
            run_id="eval-001",
            config=cfg,
            prompt_bytes=b"prompt-v1",
            schema_bytes=b'{"type":"object"}',
            case_set_id="semantic-dev-v1",
            case_set_bytes=b'[{"id":"C1"}]',
            policy_version="0.2.10",
            started_at=started,
            sdk_version="9.9.9",
        )

        data = manifest.to_dict()
        self.assertEqual(data["provider"], "openai-responses")
        self.assertEqual(data["model_id"], "model-snapshot")
        self.assertEqual(data["policy_version"], "0.2.10")
        self.assertEqual(data["case_set_id"], "semantic-dev-v1")
        self.assertEqual(data["started_at"], "2026-10-30T15:00:00+00:00")
        self.assertEqual(data["sdk_version"], "9.9.9")
        self.assertEqual(data["request_parameters"], {"reasoning": "medium"})
        self.assertEqual(len(data["prompt_sha256"]), 64)
        self.assertEqual(len(data["schema_sha256"]), 64)
        self.assertEqual(len(data["case_set_sha256"]), 64)

    def test_manifest_requires_explicit_timezone_aware_start(self):
        cfg = SemanticProviderConfig(
            provider="openai-responses",
            model_id="model-snapshot",
        )
        with self.assertRaisesRegex(ValueError, "started_at_timezone_required"):
            EvaluationRunManifest.create(
                run_id="eval-002",
                config=cfg,
                prompt_bytes=b"x",
                schema_bytes=b"{}",
                case_set_id="dev",
                case_set_bytes=b"[]",
                policy_version="0.2.10",
                started_at=datetime(2026, 10, 30, 15, 0),
            )

    def test_finished_manifest_records_response_ids_usage_and_completion(self):
        cfg = SemanticProviderConfig(
            provider="openai-responses",
            model_id="model-snapshot",
        )
        started = datetime(2026, 10, 30, 15, 0, tzinfo=timezone.utc)
        manifest = EvaluationRunManifest.create(
            run_id="eval-003",
            config=cfg,
            prompt_bytes=b"x",
            schema_bytes=b"{}",
            case_set_id="dev",
            case_set_bytes=b"[]",
            policy_version="0.2.10",
            started_at=started,
        )

        finished = manifest.finish(
            completed_at=datetime(2026, 10, 30, 15, 5, tzinfo=timezone.utc),
            response_ids=("resp_1", "resp_2"),
            usage={"input_tokens": 100, "output_tokens": 40},
        )

        data = finished.to_dict()
        self.assertEqual(data["completed_at"], "2026-10-30T15:05:00+00:00")
        self.assertEqual(data["response_ids"], ["resp_1", "resp_2"])
        self.assertEqual(data["usage"]["input_tokens"], 100)

    def test_finish_rejects_completion_before_start(self):
        cfg = SemanticProviderConfig(
            provider="openai-responses",
            model_id="model-snapshot",
        )
        started = datetime(2026, 10, 30, 15, 0, tzinfo=timezone.utc)
        manifest = EvaluationRunManifest.create(
            run_id="eval-004",
            config=cfg,
            prompt_bytes=b"x",
            schema_bytes=b"{}",
            case_set_id="dev",
            case_set_bytes=b"[]",
            policy_version="0.2.10",
            started_at=started,
        )

        with self.assertRaisesRegex(ValueError, "completed_at_before_started_at"):
            manifest.finish(
                completed_at=datetime(2026, 10, 30, 14, 59, tzinfo=timezone.utc)
            )


if __name__ == "__main__":
    unittest.main()
