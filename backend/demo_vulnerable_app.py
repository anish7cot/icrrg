"""
Sample vulnerable application module — FOR TESTING/DEMO ONLY.
This file contains intentionally insecure code patterns that the ICRRG
scanner should detect across all engines (regex, entropy, NER/PHI, SCA).
DO NOT deploy this file in production.
"""

# ── CWE-798: Hard-coded AWS Credentials ──────────────────────────────
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# ── CWE-321: Hard-coded Private Key ──────────────────────────────────
PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGcY5unAj0lmPsSi2LzuE1Xe
n5M5rXQEOL9kBR7t3gqxFUV5vUMOGl5Kbn8tVJQ7GhRDr3b5EXAMPLE00000AAAAA
BBBBBCCCCCdddddEEEEE11111222223333344444555556666677777example==
-----END RSA PRIVATE KEY-----"""

# ── CWE-259: Hard-coded Passwords & Connection Strings ───────────────
DB_PASSWORD = "SuperSecret123!"
password = "admin_p@ssw0rd_2026"
DATABASE_URL = "postgresql://admin:s3cretPassw0rd@prod-db.internal:5432/users"
REDIS_CONN = "redis://default:hunter2@cache.internal:6379/0"

# ── CWE-798: Hard-coded API / Service Tokens ─────────────────────────
GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijkl"
GITLAB_TOKEN = "glpat-xxxxxxxxxxxxxxxxxxxx"
SLACK_BOT_TOKEN = "xoxb-fake-000000000-000000000000-EXAMPLE_PLACEHOLDER"
GENERIC_API_KEY = "api_key=sk_test_EXAMPLE_PLACEHOLDER_not_real_key_00"
bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwidGVzdCI6dHJ1ZX0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

# ── CWE-200: High-Entropy Secrets (triggers entropy engine) ──────────
secret_key = "a8F3kL9mN2pQ5rT8vX1zA4cE7gI0jM3oR6sU9wB2dH5fK8nP1qS4tV7xY0bD3eG"
api_token = "4f9b2e7a1c8d3f6e0a5b9c2d7f4e1a8b3c6d0f5e9a2b7c4d8f1e6a0b5c9d3f7"

# ── CWE-359: PHI / PII Exposure (triggers NER + regex PHI engine) ────
# Patient records with SSN, MRN, DOB
patient_data = {
    "patient_name": "John Smith",
    "ssn": "123-45-6789",
    "date_of_birth": "03/15/1985",
    "medical_record_number": "MRN-00123456",
    "phone": "(555) 867-5309",
    "diagnosis": "Type 2 Diabetes Mellitus",
    "physician": "Dr. Sarah Johnson",
    "insurance_id": "BCBS-9876543210",
}

# Another patient record
clinical_note = """
Patient: Jane Doe, DOB: 11/22/1990, SSN: 987-65-4321
MRN: 00789012
Prescription: Metformin 500mg twice daily
Treating physician: Dr. Michael Chen
Hospital: Memorial General Hospital
Billing code: 99213
"""

# ── CWE-312: Cleartext Storage of Sensitive Information ──────────────
def store_user_credentials(username, password):
    """Stores credentials in plaintext — DO NOT DO THIS."""
    with open("/tmp/credentials.txt", "w") as f:
        f.write(f"username={username}\npassword={password}\n")


def get_patient_record(patient_ssn):
    """Returns patient data using SSN as lookup key — PHI exposure."""
    records = {
        "123-45-6789": {"name": "John Smith", "dob": "03/15/1985"},
        "987-65-4321": {"name": "Jane Doe", "dob": "11/22/1990"},
    }
    return records.get(patient_ssn)


# ── CWE-502: SQL Injection Vector ────────────────────────────────────
def unsafe_query(user_input):
    """Concatenates user input into SQL — injection risk."""
    query = f"SELECT * FROM users WHERE username = '{user_input}'"
    return query


# ── Vulnerable Dependencies (triggers SCA engine via requirements) ───
# See: vulnerable_requirements.txt in this directory
VULNERABLE_DEPS = """
flask==1.0
requests==2.19.0
django==2.0
pyyaml==5.1
urllib3==1.24.1
jinja2==2.10
cryptography==2.1
pillow==5.0.0
"""
