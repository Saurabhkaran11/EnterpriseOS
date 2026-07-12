"""Final-report artifact storage with automatic S3-to-local fallback."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StorageConfig:
    region: str = "us-west-2"
    bucket: str = ""
    use_local_mode: bool = True
    local_directory: Path = Path(__file__).resolve().parent.parent / "outputs" / "artifacts"
    @classmethod
    def from_env(cls): return cls(region=os.getenv("AWS_REGION", "us-west-2"), bucket=os.getenv("AWS_S3_BUCKET", ""), use_local_mode=os.getenv("AWS_USE_LOCAL_MODE", "true").lower() not in ("false", "0", "no"))


class ArtifactStorage(ABC):
    @abstractmethod
    def store_report(self, report: dict[str, Any], artifact_id: str) -> dict[str, Any]: ...
    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...


def report_markdown(report):
    issues = "\n".join(f"- {item}" for item in report["relatedEngineeringIssues"])
    actions = "\n".join(f"{index}. {item}" for index, item in enumerate(report["recommendedActions"], 1))
    agenda = "\n".join(f"- {item}" for item in report["proposedMeetingAgenda"])
    return f"# Executive Customer Review\n\n## Customer at risk\n\n**{report['customerAtRisk']} — {report['contractValue']}**\n\n{report['riskExplanation']}\n\n## Related engineering issues\n\n{issues}\n\n## Recommended actions\n\n{actions}\n\n## Draft customer response\n\n> {report['draftCustomerResponse']}\n\n## Proposed meeting agenda\n\n{agenda}\n\n## Verification\n\nScore: **{report['verificationScore']}/100**\n"


class LocalFilesystemStorage(ArtifactStorage):
    def __init__(self, config: StorageConfig | None = None): self.config = config or StorageConfig.from_env()
    def store_report(self, report, artifact_id):
        self.config.local_directory.mkdir(parents=True, exist_ok=True)
        json_path = self.config.local_directory / f"{artifact_id}.json"; markdown_path = self.config.local_directory / f"{artifact_id}.md"
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8"); markdown_path.write_text(report_markdown(report), encoding="utf-8")
        return {"mode": "Local", "status": "Stored", "locations": {"json": str(json_path), "markdown": str(markdown_path)}, "fallbackReason": None}
    def health_check(self): return {"healthy": True, "mode": "Local", "provider": "LocalFilesystemStorage", "location": str(self.config.local_directory)}


class S3ArtifactStorage(ArtifactStorage):
    def __init__(self, config: StorageConfig | None = None, client=None): self.config = config or StorageConfig.from_env(); self.client = client
    def _client(self):
        if self.client is None:
            import boto3
            self.client = boto3.client("s3", region_name=self.config.region)
        return self.client
    def store_report(self, report, artifact_id):
        if not self.config.bucket: raise RuntimeError("AWS_S3_BUCKET is not configured")
        prefix = f"enterpriseos/{artifact_id}"; json_key = prefix + ".json"; markdown_key = prefix + ".md"
        client = self._client(); client.put_object(Bucket=self.config.bucket, Key=json_key, Body=(json.dumps(report, indent=2)+"\n").encode(), ContentType="application/json"); client.put_object(Bucket=self.config.bucket, Key=markdown_key, Body=report_markdown(report).encode(), ContentType="text/markdown")
        return {"mode": "S3", "status": "Stored", "locations": {"json": f"s3://{self.config.bucket}/{json_key}", "markdown": f"s3://{self.config.bucket}/{markdown_key}"}, "fallbackReason": None}
    def health_check(self):
        if not self.config.bucket: return {"healthy": False, "mode": "Unavailable", "provider": "S3ArtifactStorage", "error": "Missing bucket"}
        return {"healthy": True, "mode": "Configured", "provider": "S3ArtifactStorage", "bucket": self.config.bucket, "region": self.config.region}


class FallbackArtifactStorage(ArtifactStorage):
    def __init__(self, primary: ArtifactStorage, fallback: LocalFilesystemStorage): self.primary, self.fallback = primary, fallback
    def store_report(self, report, artifact_id):
        try: return self.primary.store_report(report, artifact_id)
        except Exception as exc:
            result = self.fallback.store_report(report, artifact_id); result["fallbackReason"] = f"S3 unavailable: {exc}"; return result
    def health_check(self): return {"healthy": True, "mode": "Local", "primary": self.primary.health_check(), "fallback": self.fallback.health_check()}


def configured_artifact_storage(config: StorageConfig | None = None, s3_client=None, execution_mode: str | None = None):
    config = config or StorageConfig.from_env(); local = LocalFilesystemStorage(config)
    if execution_mode == "DEMO" or config.use_local_mode or not config.bucket: return local
    return FallbackArtifactStorage(S3ArtifactStorage(config, s3_client), local)
