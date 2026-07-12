"""Release-safe reset and deterministic demo runner."""
import json
import os
from pathlib import Path
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=False)
except ImportError:
    pass

os.environ["ENTERPRISEOS_MODE"] = "DEMO"
os.environ["HCOMPANY_MOCK_MODE"] = "true"
os.environ["NVIDIA_MOCK_MODE"] = "true"
os.environ["AWS_USE_LOCAL_MODE"] = "true"

import app


def reset():
    app.reset_data()
    workflow = app.load_workflow(app.WORKFLOW_ID)
    assert workflow["status"] == "IDLE"
    resolved_mode = workflow["executionMode"]["resolved"]
    print(f"EnterpriseOS demo reset: IDLE / {resolved_mode}")


def run():
    app.reset_data()
    workflow = app.start_workflow(app.WORKFLOW_ID)
    assert workflow["status"] == "PLANNING"
    for _ in range(10): workflow = app.advance_workflow(workflow)
    assert workflow["status"] == "AWAITING_APPROVAL"
    workflow = app.approve_workflow(app.WORKFLOW_ID)
    for _ in range(3): workflow = app.advance_workflow(workflow)
    assert workflow["status"] == "COMPLETED"
    assert workflow["report"]["customerAtRisk"] == "Acme Health"
    assert workflow["reasoning"]["riskScore"] == 92
    assert workflow["artifactStorage"]["status"] == "Stored"
    for location in workflow["artifactStorage"]["locations"].values(): assert Path(location).is_file()
    print(json.dumps({"status": workflow["status"], "mode": workflow["executionMode"]["resolved"], "customer": workflow["report"]["customerAtRisk"], "riskScore": workflow["reasoning"]["riskScore"], "verification": workflow["report"]["verificationScore"], "artifacts": workflow["artifactStorage"]["locations"]}, indent=2))


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    if command == "reset": reset()
    elif command == "run": run()
    else: raise SystemExit(f"Unknown command: {command}")
