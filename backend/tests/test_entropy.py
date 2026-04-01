"""Tests for the entropy-based secret detection engine."""

import string
import random
from app.git.diff_parser import parse_unified_diff
from app.detection.entropy import (
    shannon_entropy,
    scan_diff_for_entropy,
)


# ---------------------------------------------------------------------------
# Shannon entropy unit tests
# ---------------------------------------------------------------------------

def test_entropy_empty_string():
    assert shannon_entropy("") == 0.0


def test_entropy_single_char_repeated():
    # All same chars → 0 entropy
    assert shannon_entropy("aaaaaaaaaa") == 0.0


def test_entropy_high_randomness():
    # A truly random-looking string should have high entropy
    random_str = "a8f3Kz9Qp2Xw7LmN4Yd6Rc1Ej5Bh0Gv"
    ent = shannon_entropy(random_str)
    assert ent > 4.0


def test_entropy_moderate():
    # "hello world" has moderate entropy
    ent = shannon_entropy("hello world")
    assert 2.0 < ent < 4.0


# ---------------------------------------------------------------------------
# Sample diffs
# ---------------------------------------------------------------------------

# Random API key that regex engine would NOT catch (no AKIA prefix, no known pattern)
DIFF_RANDOM_API_KEY = """\
diff --git a/app/services.py b/app/services.py
index aaa..bbb 100644
--- a/app/services.py
+++ b/app/services.py
@@ -1,3 +1,4 @@
 import requests
+api_key = "a8f3Kz9Qp2Xw7LmNy4Yd6Rc1Ej5Bh0GvTs"
 BASE_URL = "https://api.example.com"
"""

DIFF_SECRET_TOKEN = """\
diff --git a/app/auth.py b/app/auth.py
index ccc..ddd 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -2,2 +2,3 @@
 import os
+auth_token = "xR9kL2mP5nQ8wJ4vB7yH3cF6gT1aD0eU"
 
"""

DIFF_PASSWORD_ASSIGNMENT = """\
diff --git a/app/db.py b/app/db.py
index eee..fff 100644
--- a/app/db.py
+++ b/app/db.py
@@ -1,2 +1,3 @@
 DB_HOST = "localhost"
+password = "Zk8mWp3nRx7Lq2Yv5Bg9Hc4Ft1Jd6Ae0Us"
"""

# UUID on a line — should NOT be flagged
DIFF_UUID = """\
diff --git a/app/models.py b/app/models.py
index 111..222 100644
--- a/app/models.py
+++ b/app/models.py
@@ -1,2 +1,3 @@
 import uuid
+DEFAULT_TOKEN = "550e8400-e29b-41d4-a716-446655440000"
"""

# Hash constant — should NOT be flagged
DIFF_HASH_CONST = """\
diff --git a/app/verify.py b/app/verify.py
index 333..444 100644
--- a/app/verify.py
+++ b/app/verify.py
@@ -1,2 +1,3 @@
 import hashlib
+sha256_checksum = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
"""

# No secret variable context — should NOT be flagged
DIFF_NO_CONTEXT = """\
diff --git a/app/utils.py b/app/utils.py
index 555..666 100644
--- a/app/utils.py
+++ b/app/utils.py
@@ -1,2 +1,3 @@
 import base64
+DATA = "a8f3Kz9Qp2Xw7LmNy4Yd6Rc1Ej5Bh0GvTs"
"""

# Test file — should be skipped
DIFF_IN_TEST_FILE = """\
diff --git a/tests/test_auth.py b/tests/test_auth.py
index 777..888 100644
--- a/tests/test_auth.py
+++ b/tests/test_auth.py
@@ -1,2 +1,3 @@
 import pytest
+api_key = "a8f3Kz9Qp2Xw7LmNy4Yd6Rc1Ej5Bh0GvTs"
"""

# Comment line — should be skipped
DIFF_COMMENT_LINE = """\
diff --git a/app/config.py b/app/config.py
index 999..aaa 100644
--- a/app/config.py
+++ b/app/config.py
@@ -1,2 +1,3 @@
 import os
+# secret = "a8f3Kz9Qp2Xw7LmNy4Yd6Rc1Ej5Bh0GvTs"
"""

# Low-entropy password — should NOT be flagged
DIFF_LOW_ENTROPY_PASSWORD = """\
diff --git a/app/config.py b/app/config.py
index bbb..ccc 100644
--- a/app/config.py
+++ b/app/config.py
@@ -1,2 +1,3 @@
 import os
+password = "aaaaaaaaaaaaaaaaaaaaaa"
"""

# Unquoted token assignment
DIFF_UNQUOTED_TOKEN = """\
diff --git a/app/config.py b/app/config.py
index ddd..eee 100644
--- a/app/config.py
+++ b/app/config.py
@@ -1,2 +1,3 @@
 import os
+secret= xR9kL2mP5nQ8wJ4vB7yH3cF6gT1aD0eU
"""


# ---------------------------------------------------------------------------
# Detection tests
# ---------------------------------------------------------------------------

def test_catches_random_api_key():
    """High-entropy string assigned to api_key — should be flagged."""
    parsed = parse_unified_diff(DIFF_RANDOM_API_KEY)
    findings = scan_diff_for_entropy(parsed)

    assert len(findings) >= 1
    f = findings[0]
    assert f.rule_name == "high-entropy-string"
    assert f.file_path == "app/services.py"
    assert f.line_number == 2
    assert f.entropy_score > 4.0
    assert "*" in f.matched_text  # redacted


def test_catches_auth_token():
    parsed = parse_unified_diff(DIFF_SECRET_TOKEN)
    findings = scan_diff_for_entropy(parsed)

    assert len(findings) >= 1
    assert findings[0].file_path == "app/auth.py"


def test_catches_password():
    parsed = parse_unified_diff(DIFF_PASSWORD_ASSIGNMENT)
    findings = scan_diff_for_entropy(parsed)

    assert len(findings) >= 1
    assert findings[0].severity == "medium"


def test_catches_unquoted_token():
    parsed = parse_unified_diff(DIFF_UNQUOTED_TOKEN)
    findings = scan_diff_for_entropy(parsed)

    assert len(findings) >= 1


# ---------------------------------------------------------------------------
# False-positive suppression tests
# ---------------------------------------------------------------------------

def test_skips_uuid():
    """UUIDs are high-entropy but should NOT be flagged."""
    parsed = parse_unified_diff(DIFF_UUID)
    findings = scan_diff_for_entropy(parsed)
    assert len(findings) == 0


def test_skips_hash_constant():
    """Hash/checksum constants should NOT be flagged."""
    parsed = parse_unified_diff(DIFF_HASH_CONST)
    findings = scan_diff_for_entropy(parsed)
    assert len(findings) == 0


def test_skips_no_secret_context():
    """High-entropy string without a secret variable name should NOT be flagged."""
    parsed = parse_unified_diff(DIFF_NO_CONTEXT)
    findings = scan_diff_for_entropy(parsed)
    assert len(findings) == 0


def test_skips_test_files():
    parsed = parse_unified_diff(DIFF_IN_TEST_FILE)
    findings = scan_diff_for_entropy(parsed)
    assert len(findings) == 0


def test_skips_comments():
    parsed = parse_unified_diff(DIFF_COMMENT_LINE)
    findings = scan_diff_for_entropy(parsed)
    assert len(findings) == 0


def test_skips_low_entropy():
    """Repeated chars have low entropy — should NOT be flagged."""
    parsed = parse_unified_diff(DIFF_LOW_ENTROPY_PASSWORD)
    findings = scan_diff_for_entropy(parsed)
    assert len(findings) == 0


def test_empty_diff():
    parsed = parse_unified_diff("")
    findings = scan_diff_for_entropy(parsed)
    assert len(findings) == 0
