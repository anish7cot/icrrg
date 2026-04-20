"""Tests for the diff sanitization layer."""

from __future__ import annotations

import textwrap

import pytest

from app.detection.sanitizer import sanitize_diff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_diff(added_lines: list[str], file_path: str = "config.py") -> str:
    """Build a minimal unified diff with the given added lines."""
    header = textwrap.dedent(f"""\
        diff --git a/{file_path} b/{file_path}
        --- a/{file_path}
        +++ b/{file_path}
        @@ -1,3 +1,{3 + len(added_lines)} @@
         import os
         import sys
         """)
    body = "\n".join(f"+{line}" for line in added_lines)
    return header + body


# ---------------------------------------------------------------------------
# Secret detection (regex engine patterns)
# ---------------------------------------------------------------------------

class TestSecretRedaction:
    def test_aws_access_key(self):
        diff = _make_diff(["AWS_KEY = 'AKIAIOSFODNN7EXAMPLE'"])
        result = sanitize_diff(diff)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED-secret]" in result

    def test_aws_secret_key(self):
        diff = _make_diff(
            ["aws_secret_access_key = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'"]
        )
        result = sanitize_diff(diff)
        assert "wJalrXUtnFEMI" not in result
        assert "[REDACTED-secret]" in result

    def test_github_token(self):
        diff = _make_diff(["GITHUB_TOKEN = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij'"])
        result = sanitize_diff(diff)
        assert "ghp_ABCDEFGHIJKLMNOPQRST" not in result
        assert "[REDACTED-secret]" in result

    def test_private_key_header(self):
        diff = _make_diff(["key = '-----BEGIN RSA PRIVATE KEY-----'"])
        result = sanitize_diff(diff)
        assert "-----BEGIN RSA PRIVATE KEY-----" not in result
        assert "[REDACTED-secret]" in result

    def test_password_assignment(self):
        diff = _make_diff(["password = 'SuperSecret123!'"])
        result = sanitize_diff(diff)
        assert "SuperSecret123!" not in result
        assert "[REDACTED-secret]" in result

    def test_connection_string(self):
        diff = _make_diff(
            ["DATABASE_URL = 'postgresql://admin:SuperSecret123@prod-db:5432/app'"]
        )
        result = sanitize_diff(diff)
        assert "SuperSecret123" not in result
        assert "[REDACTED-secret]" in result

    def test_bearer_token(self):
        diff = _make_diff(
            ["authorization = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123def456'"]
        )
        result = sanitize_diff(diff)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED-secret]" in result

    def test_secret_in_removed_line(self):
        """Removed lines (prefixed with -) should also be redacted."""
        diff = textwrap.dedent("""\
            diff --git a/config.py b/config.py
            --- a/config.py
            +++ b/config.py
            @@ -1,3 +1,3 @@
             import os
            -password = 'OldSecret123!'
            +password = os.environ["PASSWORD"]
             """)
        result = sanitize_diff(diff)
        assert "OldSecret123!" not in result
        assert "[REDACTED-secret]" in result

    def test_multiple_secrets_same_line(self):
        diff = _make_diff(
            ["password = 'Secret1!'; api_key = 'AKIAIOSFODNN7EXAMPLE'"]
        )
        result = sanitize_diff(diff)
        assert "Secret1!" not in result
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert result.count("[REDACTED-secret]") >= 2


# ---------------------------------------------------------------------------
# Entropy detection
# ---------------------------------------------------------------------------

class TestEntropyRedaction:
    def test_high_entropy_token(self):
        # A random-looking string assigned to a secret-like variable name
        # that doesn't match any known secret regex pattern.
        diff = _make_diff(
            ["auth_token = 'aB3xQ9zR7wK2mN5pL8vF4jH6tY1uC0eD'"]
        )
        result = sanitize_diff(diff)
        assert "aB3xQ9zR7wK2mN5pL8vF4jH6tY1uC0eD" not in result
        # May be caught by secret regex or entropy — either is acceptable
        assert "[REDACTED-" in result


# ---------------------------------------------------------------------------
# PHI detection
# ---------------------------------------------------------------------------

class TestPhiRedaction:
    def test_ssn(self):
        diff = _make_diff(["ssn = '123-45-6789'"])
        result = sanitize_diff(diff)
        assert "123-45-6789" not in result
        assert "[REDACTED-phi]" in result

    def test_mrn(self):
        diff = _make_diff(["MRN: 12345678"])
        result = sanitize_diff(diff)
        assert "12345678" not in result
        assert "[REDACTED-phi]" in result

    def test_dob(self):
        diff = _make_diff(["date of birth: 01/15/1990"])
        result = sanitize_diff(diff)
        assert "01/15/1990" not in result
        assert "[REDACTED-phi]" in result


# ---------------------------------------------------------------------------
# Clean diffs — no redaction
# ---------------------------------------------------------------------------

class TestCleanDiff:
    def test_no_secrets(self):
        diff = _make_diff(["x = 42", "name = 'hello world'"])
        result = sanitize_diff(diff)
        assert "[REDACTED-" not in result
        assert "x = 42" in result
        assert "name = 'hello world'" in result

    def test_diff_headers_preserved(self):
        diff = _make_diff(["x = 1"])
        result = sanitize_diff(diff)
        assert "diff --git" in result
        assert "--- a/config.py" in result
        assert "+++ b/config.py" in result
        assert "@@ -1,3" in result


# ---------------------------------------------------------------------------
# Structural integrity
# ---------------------------------------------------------------------------

class TestStructure:
    def test_line_count_preserved(self):
        """Redaction must not change the number of lines."""
        diff = _make_diff(["password = 'Secret!'", "x = 1", "api_key = 'AKIAIOSFODNN7EXAMPLE'"])
        original_lines = diff.count("\n")
        result = sanitize_diff(diff)
        assert result.count("\n") == original_lines

    def test_diff_prefix_preserved(self):
        """The +/- prefix on each line must survive redaction."""
        diff = textwrap.dedent("""\
            diff --git a/f.py b/f.py
            --- a/f.py
            +++ b/f.py
            @@ -1,2 +1,2 @@
            -password = 'OldPass123!'
            +password = 'NewPass456!'
             keep = True""")
        result = sanitize_diff(diff)
        lines = result.splitlines()
        # Find the content lines (after @@)
        content_lines = [l for l in lines if not l.startswith(("diff ", "--- ", "+++ ", "@@ "))]
        prefixes = [l[0] for l in content_lines if l]
        assert prefixes == ["-", "+", " "]
