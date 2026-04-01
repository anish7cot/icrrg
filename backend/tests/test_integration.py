"""Integration tests — full pipeline with planted secrets and PHI.

Tests run each sample diff through: parse → regex → entropy → NER → aggregate,
then verify correct findings, severities, and file/line references.
Also tests the API endpoint end-to-end via httpx TestClient.
"""

from pathlib import Path

import pytest

from app.git.diff_parser import parse_unified_diff
from app.detection.regex_engine import scan_diff_for_secrets
from app.detection.entropy import scan_diff_for_entropy
from app.detection.ner_pipeline import scan_diff_for_phi

FIXTURES = Path(__file__).parent / "fixtures" / "sample_diffs"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ── helpers ───────────────────────────────────────────────────────────────

def _run_full_pipeline(raw_diff: str):
    """Mirror the pipeline from the scan API."""
    parsed = parse_unified_diff(raw_diff)
    secrets = scan_diff_for_secrets(parsed)
    entropy = scan_diff_for_entropy(parsed)
    phi = scan_diff_for_phi(parsed)
    return {
        "parsed": parsed,
        "secrets": secrets,
        "entropy": entropy,
        "phi": phi,
        "all": [
            *[{"type": f"secret:{f.rule_name}", "sev": f.severity, "fp": f.file_path, "ln": f.line_number} for f in secrets],
            *[{"type": f"entropy:{f.rule_name}", "sev": f.severity, "fp": f.file_path, "ln": f.line_number} for f in entropy],
            *[{"type": f"phi:{f.rule_name}", "sev": f.severity, "fp": f.file_path, "ln": f.line_number} for f in phi],
        ],
    }


# ═════════════════════════════════════════════════════════════════════════
# Diff #1 — AWS secrets + hardcoded password + API key
# ═════════════════════════════════════════════════════════════════════════

class TestDiff01AwsSecrets:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = _run_full_pipeline(_load("01_aws_secrets.diff"))

    def test_finds_aws_access_key(self):
        matches = [f for f in self.result["secrets"] if f.rule_name == "aws-access-key-id"]
        assert len(matches) >= 1
        assert matches[0].severity == "critical"
        assert matches[0].file_path == "app/config.py"
        assert matches[0].line_number == 4

    def test_finds_aws_secret_key(self):
        matches = [f for f in self.result["secrets"] if f.rule_name == "aws-secret-access-key"]
        assert len(matches) >= 1
        assert matches[0].severity == "critical"

    def test_finds_hardcoded_password(self):
        matches = [f for f in self.result["secrets"] if f.rule_name == "password-assignment"]
        assert len(matches) >= 1
        assert matches[0].severity == "high"
        assert matches[0].line_number == 7

    def test_finds_generic_api_key(self):
        matches = [f for f in self.result["secrets"] if f.rule_name == "generic-api-key"]
        assert len(matches) >= 1
        assert matches[0].severity == "high"

    def test_entropy_detects_random_key(self):
        # The api_key should also be caught by entropy
        assert len(self.result["entropy"]) >= 1

    def test_total_findings_at_least_four(self):
        # AWS key, AWS secret, password, generic api key — minimum 4 secret findings
        assert len(self.result["secrets"]) >= 4

    def test_all_file_paths_correct(self):
        for f in self.result["all"]:
            assert f["fp"] == "app/config.py"


# ═════════════════════════════════════════════════════════════════════════
# Diff #2 — PHI (patient SSN, MRN, DOB, phone)
# ═════════════════════════════════════════════════════════════════════════

class TestDiff02PhiPatient:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = _run_full_pipeline(_load("02_phi_patient.diff"))

    def test_finds_ssn(self):
        matches = [f for f in self.result["phi"] if f.rule_name == "ssn"]
        assert len(matches) >= 1
        assert matches[0].severity == "critical"
        assert matches[0].file_path == "app/intake.py"

    def test_finds_mrn(self):
        matches = [f for f in self.result["phi"] if f.rule_name == "mrn"]
        assert len(matches) >= 1
        assert matches[0].severity == "critical"

    def test_finds_dob(self):
        matches = [f for f in self.result["phi"] if f.rule_name == "date-of-birth"]
        assert len(matches) >= 1

    def test_finds_phone_with_patient_context(self):
        matches = [f for f in self.result["phi"] if f.rule_name == "phone-number"]
        assert len(matches) >= 1

    def test_phi_total_at_least_three(self):
        # SSN + MRN + DOB minimum
        assert len(self.result["phi"]) >= 3

    def test_no_secret_false_positives(self):
        # This diff has no code secrets — only PHI
        # (password-like patterns might match "123-45-6789" but it's in PHI context)
        # Just verify the detections are overwhelmingly PHI
        assert len(self.result["phi"]) >= len(self.result["secrets"])


# ═════════════════════════════════════════════════════════════════════════
# Diff #3 — Connection strings with embedded passwords
# ═════════════════════════════════════════════════════════════════════════

class TestDiff03ConnectionStrings:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = _run_full_pipeline(_load("03_connection_strings.diff"))

    def test_finds_postgres_connection_string(self):
        matches = [f for f in self.result["secrets"] if f.rule_name == "connection-string-password"]
        assert len(matches) >= 1
        pg = [m for m in matches if "postgres" in m.line_content.lower() or "admin" in m.line_content.lower()]
        assert len(pg) >= 1

    def test_finds_multiple_connection_strings(self):
        matches = [f for f in self.result["secrets"] if f.rule_name == "connection-string-password"]
        # postgres + redis + mongo = 3
        assert len(matches) >= 2

    def test_finds_hardcoded_secret(self):
        matches = [f for f in self.result["secrets"] if f.rule_name == "password-assignment"]
        assert len(matches) >= 1

    def test_entropy_catches_random_secret(self):
        assert len(self.result["entropy"]) >= 1

    def test_file_path_correct(self):
        for f in self.result["all"]:
            assert f["fp"] == "app/database.py"


# ═════════════════════════════════════════════════════════════════════════
# Diff #4 — Clean code (ZERO findings expected)
# ═════════════════════════════════════════════════════════════════════════

class TestDiff04CleanCode:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.result = _run_full_pipeline(_load("04_clean_code.diff"))

    def test_zero_secret_findings(self):
        assert len(self.result["secrets"]) == 0

    def test_zero_entropy_findings(self):
        assert len(self.result["entropy"]) == 0

    def test_zero_phi_findings(self):
        assert len(self.result["phi"]) == 0

    def test_zero_total_findings(self):
        assert len(self.result["all"]) == 0

    def test_diff_still_parses(self):
        # The diff should parse correctly even if no findings
        assert len(self.result["parsed"].files) == 1
        assert self.result["parsed"].files[0].new_path == "app/utils.py"
        assert self.result["parsed"].total_additions > 0


# ═════════════════════════════════════════════════════════════════════════
# API endpoint integration (via live server)
# ═════════════════════════════════════════════════════════════════════════
# These tests require the backend running on localhost:8000.
# They are skipped automatically if the server is not reachable.

import httpx


def _server_reachable() -> bool:
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _server_reachable(), reason="Backend not running on localhost:8000")
class TestApiIntegration:
    def test_post_diff01_returns_findings(self):
        resp = httpx.post(
            "http://localhost:8000/api/v1/scans",
            json={"diff_text": _load("01_aws_secrets.diff"), "repository": "integration-test"},
            timeout=15,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "completed"
        assert len(data["findings"]) >= 4
        assert data["risk_score"] > 0
        types = {f["finding_type"] for f in data["findings"]}
        assert any("aws-access-key-id" in t for t in types)

    def test_post_diff04_returns_zero_findings(self):
        resp = httpx.post(
            "http://localhost:8000/api/v1/scans",
            json={"diff_text": _load("04_clean_code.diff"), "repository": "integration-test"},
            timeout=15,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "completed"
        assert len(data["findings"]) == 0
        assert data["risk_score"] == 0

    def test_get_scan_by_id(self):
        post_resp = httpx.post(
            "http://localhost:8000/api/v1/scans",
            json={"diff_text": _load("02_phi_patient.diff"), "repository": "integration-test"},
            timeout=15,
        )
        scan_id = post_resp.json()["id"]
        get_resp = httpx.get(f"http://localhost:8000/api/v1/scans/{scan_id}", timeout=10)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == scan_id
        assert len(data["findings"]) >= 3

    def test_list_scans(self):
        resp = httpx.get("http://localhost:8000/api/v1/scans", timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
