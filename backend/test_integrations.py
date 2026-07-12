import json
from pathlib import Path
import tempfile
import unittest

import httpx

from artifact_storage import FallbackArtifactStorage, LocalFilesystemStorage, S3ArtifactStorage, StorageConfig, configured_artifact_storage
from reasoning import DeterministicReasoningProvider, NVIDIAConfig, NVIDIAReasoningProvider


class FakeResponse:
    def __init__(self, content): self.content = content
    def raise_for_status(self): return None
    def json(self): return {"choices": [{"message": {"content": self.content}}]}


class SequenceClient:
    def __init__(self, values): self.values = list(values); self.calls = 0
    def post(self, *args, **kwargs):
        value = self.values[min(self.calls, len(self.values)-1)]; self.calls += 1
        if isinstance(value, Exception): raise value
        return FakeResponse(value)


class FailingS3Client:
    def put_object(self, **kwargs): raise RuntimeError("simulated S3 outage")


REPORT = {"customerAtRisk": "Acme Health", "contractValue": "$640,000", "riskExplanation": "Product defects threaten renewal.", "relatedEngineeringIssues": ["Payment timeout"], "recommendedActions": ["Validate hotfix"], "draftCustomerResponse": "We are addressing the incident.", "proposedMeetingAgenda": ["Status review"], "verificationScore": 96}


class IntegrationProviderTest(unittest.TestCase):
    def test_nvidia_mock_output(self):
        provider = DeterministicReasoningProvider()
        risk = provider.analyze_customer_risk({}, [])
        actions = provider.generate_action_plan({})
        verification = provider.verify_workflow_result({})
        self.assertEqual(risk["riskScore"], 92)
        self.assertTrue(all(set(("priority", "action", "owner", "deadline", "expectedOutcome")) <= set(item) for item in actions))
        self.assertTrue(verification["verified"])

    def test_nvidia_malformed_response_repairs_once_then_falls_back(self):
        client = SequenceClient(["not-json", '{"still":"invalid"}'])
        provider = NVIDIAReasoningProvider(NVIDIAConfig(api_key="test", mock_mode=False), client)
        result = provider.analyze_customer_risk({}, [])
        self.assertEqual(client.calls, 2)
        self.assertEqual(result["customerName"], "Acme Health")
        self.assertIn("repair", provider.last_fallback_reason)

    def test_nvidia_timeout_falls_back(self):
        request = httpx.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions")
        provider = NVIDIAReasoningProvider(NVIDIAConfig(api_key="test", mock_mode=False), SequenceClient([httpx.ReadTimeout("timeout", request=request)]))
        result = provider.verify_workflow_result({})
        self.assertTrue(result["verified"])
        self.assertIn("timed out", provider.last_fallback_reason)

    def test_local_artifact_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalFilesystemStorage(StorageConfig(local_directory=Path(directory)))
            result = storage.store_report(REPORT, "review")
            self.assertEqual(result["mode"], "Local")
            self.assertEqual(json.loads(Path(result["locations"]["json"]).read_text())["customerAtRisk"], "Acme Health")
            self.assertIn("# Executive Customer Review", Path(result["locations"]["markdown"]).read_text())

    def test_s3_configuration_absence_uses_local(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = configured_artifact_storage(StorageConfig(bucket="", use_local_mode=False, local_directory=Path(directory)))
            self.assertEqual(storage.health_check()["mode"], "Local")

    def test_s3_failure_falls_back_local(self):
        with tempfile.TemporaryDirectory() as directory:
            config = StorageConfig(bucket="enterpriseos-demo", use_local_mode=False, local_directory=Path(directory))
            storage = FallbackArtifactStorage(S3ArtifactStorage(config, FailingS3Client()), LocalFilesystemStorage(config))
            result = storage.store_report(REPORT, "review")
            self.assertEqual(result["mode"], "Local")
            self.assertIn("S3 unavailable", result["fallbackReason"])
            self.assertTrue(Path(result["locations"]["json"]).exists())

    def test_final_report_generation_has_both_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            result = LocalFilesystemStorage(StorageConfig(local_directory=Path(directory))).store_report(REPORT, "executive-customer-review")
            self.assertEqual(set(result["locations"]), {"json", "markdown"})


if __name__ == "__main__": unittest.main()
