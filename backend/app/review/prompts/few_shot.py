"""Few-shot examples for the code-review prompt.

Each example is a dict with:
  - "diff": a short unified diff the user would submit
  - "response": the expected JSON array the assistant should return

Keep examples concise — they count toward the token budget on every request.
"""

import json

_EXAMPLE_1_DIFF = """\
--- a/app/db.py
+++ b/app/db.py
@@ -12,6 +12,9 @@
 from flask import request
 
+def get_user(user_id):
+    query = "SELECT * FROM users WHERE id = '" + user_id + "'"
+    return db.execute(query)
"""

_EXAMPLE_1_FINDINGS = [
    {
        "severity": "critical",
        "category": "Injection",
        "file": "app/db.py",
        "line": 14,
        "issue": "SQL query built via string concatenation with untrusted input.",
        "explanation": "Concatenating user-supplied values directly into a SQL string enables SQL injection. An attacker can manipulate `user_id` to read, modify, or delete arbitrary data.",
        "suggestion": "Use parameterised queries: `db.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))`.",
    }
]

_EXAMPLE_2_DIFF = """\
--- a/config/settings.py
+++ b/config/settings.py
@@ -1,4 +1,6 @@
 import os
 
+AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
+DATABASE_URL = "postgresql://admin:SuperSecret123@prod-db.internal:5432/app"
 DEBUG = os.getenv("DEBUG", False)
"""

_EXAMPLE_2_FINDINGS = [
    {
        "severity": "critical",
        "category": "Hardcoded Secret",
        "file": "config/settings.py",
        "line": 3,
        "issue": "AWS secret access key is hardcoded in source code.",
        "explanation": "Committing cloud credentials to version control allows anyone with repo access to impersonate the AWS identity. Automated scanners and leaked repos are common attack vectors.",
        "suggestion": "Load from an environment variable: `AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')` and store the value in a secrets manager.",
    },
    {
        "severity": "high",
        "category": "Hardcoded Secret",
        "file": "config/settings.py",
        "line": 4,
        "issue": "Database connection string contains an embedded password.",
        "explanation": "Plaintext passwords in source files are exposed to every developer and CI system with repository access. If the repo leaks, the database is immediately compromised.",
        "suggestion": "Use an environment variable for the full connection string or at least the password portion.",
    },
]

_EXAMPLE_3_DIFF = """\
--- a/app/api/webhook.py
+++ b/app/api/webhook.py
@@ -5,6 +5,8 @@
 import requests
 
+def notify_partner(event):
+    requests.post("http://partner-api.example.com/hook", json=event, verify=False)
"""

_EXAMPLE_3_FINDINGS = [
    {
        "severity": "high",
        "category": "Insecure Transport",
        "file": "app/api/webhook.py",
        "line": 7,
        "issue": "HTTP request sent over plaintext with TLS verification disabled.",
        "explanation": "Using `http://` instead of `https://` transmits data in cleartext. Additionally, `verify=False` disables certificate validation even if HTTPS were used, enabling man-in-the-middle attacks.",
        "suggestion": "Switch to an `https://` URL and remove `verify=False` (or set `verify=True`).",
    }
]

FEW_SHOT_EXAMPLES = [
    {"diff": _EXAMPLE_1_DIFF, "response": json.dumps(_EXAMPLE_1_FINDINGS)},
    {"diff": _EXAMPLE_2_DIFF, "response": json.dumps(_EXAMPLE_2_FINDINGS)},
    {"diff": _EXAMPLE_3_DIFF, "response": json.dumps(_EXAMPLE_3_FINDINGS)},
]
