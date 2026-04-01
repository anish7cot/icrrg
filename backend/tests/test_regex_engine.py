"""Tests for the regex secret detection engine."""

from app.git.diff_parser import parse_unified_diff
from app.detection.regex_engine import scan_diff_for_secrets, _redact


# ---------------------------------------------------------------------------
# Sample diffs with planted secrets
# ---------------------------------------------------------------------------

DIFF_WITH_AWS_KEY = """\
diff --git a/app/config.py b/app/config.py
index aaa..bbb 100644
--- a/app/config.py
+++ b/app/config.py
@@ -1,3 +1,5 @@
 import os
+AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
+AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
 
 DEBUG = True
"""

DIFF_WITH_PRIVATE_KEY = """\
diff --git a/deploy/key.pem b/deploy/key.pem
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/deploy/key.pem
@@ -0,0 +1,4 @@
+-----BEGIN RSA PRIVATE KEY-----
+MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF068r4...
+MIIEpAIBAAKCAQEA0Z3VS5JJcds3xf+/ygWyF068r4...
+-----END RSA PRIVATE KEY-----
"""

DIFF_WITH_PASSWORD = """\
diff --git a/src/db.py b/src/db.py
index ccc..ddd 100644
--- a/src/db.py
+++ b/src/db.py
@@ -5,2 +5,4 @@
 DB_HOST = "localhost"
+password = "SuperSecret123!"
+DB_URL = "postgres://admin:s3cretPass@localhost:5432/mydb"
"""

DIFF_WITH_GITHUB_TOKEN = """\
diff --git a/scripts/deploy.sh b/scripts/deploy.sh
index eee..fff 100644
--- a/scripts/deploy.sh
+++ b/scripts/deploy.sh
@@ -1,2 +1,3 @@
 #!/bin/bash
+GITHUB_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmn
 echo "deploying..."
"""

DIFF_WITH_GENERIC_API_KEY = """\
diff --git a/app/services.py b/app/services.py
index 111..222 100644
--- a/app/services.py
+++ b/app/services.py
@@ -1,2 +1,3 @@
 import requests
+api_key = "sk-proj-12345abcdef67890ABCDEF"
 BASE_URL = "https://api.example.com"
"""

# ── Files that should NOT be flagged ──────────────────────────────────

DIFF_IN_TEST_FILE = """\
diff --git a/tests/test_auth.py b/tests/test_auth.py
index 000..111 100644
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -1,2 +1,4 @@
 import pytest
+FAKE_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
+password = "test_password_123"
 
"""

DIFF_IN_EXAMPLE_FILE = """\
diff --git a/.env.example b/.env.example
index 000..111 100644
--- a/.env.example
+++ b/.env.example
@@ -0,0 +1,2 @@
+AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
+password = "changeit"
"""

DIFF_WITH_COMMENT = """\
diff --git a/app/auth.py b/app/auth.py
index 000..111 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,2 +1,4 @@
 import os
+# password = "this is just an example"
+# api_key = "sk-placeholder-your_key_here_xxxxx"
 TOKEN = os.environ["TOKEN"]
"""

DIFF_MULTI_FILE_MIXED = """\
diff --git a/app/config.py b/app/config.py
index aaa..bbb 100644
--- a/app/config.py
+++ b/app/config.py
@@ -1,2 +1,3 @@
 import os
+secret = "realSecret99!"
 DEBUG = False
diff --git a/tests/conftest.py b/tests/conftest.py
index ccc..ddd 100644
--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -1,2 +1,3 @@
 import pytest
+secret = "testOnlySecret"
 
"""


# ---------------------------------------------------------------------------
# Tests — detection
# ---------------------------------------------------------------------------

def test_detects_aws_access_key():
    parsed = parse_unified_diff(DIFF_WITH_AWS_KEY)
    findings = scan_diff_for_secrets(parsed)

    aws_key_findings = [f for f in findings if f.rule_name == "aws-access-key-id"]
    assert len(aws_key_findings) >= 1
    assert aws_key_findings[0].severity == "critical"
    assert aws_key_findings[0].file_path == "app/config.py"
    assert aws_key_findings[0].line_number == 2
    # Matched text should be redacted
    assert "****" in aws_key_findings[0].matched_text or "*" in aws_key_findings[0].matched_text


def test_detects_aws_secret_key():
    parsed = parse_unified_diff(DIFF_WITH_AWS_KEY)
    findings = scan_diff_for_secrets(parsed)

    secret_key_findings = [f for f in findings if f.rule_name == "aws-secret-access-key"]
    assert len(secret_key_findings) >= 1
    assert secret_key_findings[0].severity == "critical"


def test_detects_private_key():
    parsed = parse_unified_diff(DIFF_WITH_PRIVATE_KEY)
    findings = scan_diff_for_secrets(parsed)

    pk_findings = [f for f in findings if f.rule_name == "private-key-header"]
    assert len(pk_findings) == 1
    assert pk_findings[0].severity == "critical"
    assert pk_findings[0].confidence == 0.99
    assert pk_findings[0].file_path == "deploy/key.pem"


def test_detects_hardcoded_password():
    parsed = parse_unified_diff(DIFF_WITH_PASSWORD)
    findings = scan_diff_for_secrets(parsed)

    pwd_findings = [f for f in findings if f.rule_name == "password-assignment"]
    assert len(pwd_findings) >= 1
    assert pwd_findings[0].severity == "high"


def test_detects_connection_string():
    parsed = parse_unified_diff(DIFF_WITH_PASSWORD)
    findings = scan_diff_for_secrets(parsed)

    conn_findings = [f for f in findings if f.rule_name == "connection-string-password"]
    assert len(conn_findings) == 1
    assert conn_findings[0].severity == "high"
    assert conn_findings[0].line_number == 7


def test_detects_github_token():
    parsed = parse_unified_diff(DIFF_WITH_GITHUB_TOKEN)
    findings = scan_diff_for_secrets(parsed)

    gh_findings = [f for f in findings if f.rule_name == "github-token"]
    assert len(gh_findings) == 1
    assert gh_findings[0].severity == "critical"


def test_detects_generic_api_key():
    parsed = parse_unified_diff(DIFF_WITH_GENERIC_API_KEY)
    findings = scan_diff_for_secrets(parsed)

    api_findings = [f for f in findings if f.rule_name == "generic-api-key"]
    assert len(api_findings) == 1
    assert api_findings[0].severity == "high"


# ---------------------------------------------------------------------------
# Tests — false-positive suppression
# ---------------------------------------------------------------------------

def test_skips_test_files():
    parsed = parse_unified_diff(DIFF_IN_TEST_FILE)
    findings = scan_diff_for_secrets(parsed, skip_tests=True)
    assert len(findings) == 0


def test_skips_example_files():
    parsed = parse_unified_diff(DIFF_IN_EXAMPLE_FILE)
    findings = scan_diff_for_secrets(parsed, skip_tests=True)
    assert len(findings) == 0


def test_skips_comments():
    parsed = parse_unified_diff(DIFF_WITH_COMMENT)
    findings = scan_diff_for_secrets(parsed)
    assert len(findings) == 0


def test_multi_file_only_flags_non_test():
    """Real source file should be flagged, test file should not."""
    parsed = parse_unified_diff(DIFF_MULTI_FILE_MIXED)
    findings = scan_diff_for_secrets(parsed)

    assert len(findings) >= 1
    # All findings should be from app/config.py, not tests/conftest.py
    for f in findings:
        assert f.file_path == "app/config.py"


def test_skip_tests_can_be_disabled():
    """When skip_tests=False, test files ARE scanned."""
    parsed = parse_unified_diff(DIFF_IN_TEST_FILE)
    findings = scan_diff_for_secrets(parsed, skip_tests=False)
    assert len(findings) >= 1


# ---------------------------------------------------------------------------
# Tests — redaction
# ---------------------------------------------------------------------------

def test_redaction_short():
    assert _redact("abcdef") == "ab****"


def test_redaction_long():
    result = _redact("AKIAIOSFODNN7EXAMPLE")
    assert result.startswith("AKIA")
    assert result.endswith("LE")
    assert "*" in result
