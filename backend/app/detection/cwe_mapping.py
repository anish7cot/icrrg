"""CWE classification and CVSS scoring for scan findings.

Maps finding_type prefixes to CWE IDs and computes base CVSS 3.1 scores
based on severity and finding category.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CweEntry:
    cwe_id: str
    name: str
    cvss_score: float
    cvss_vector: str


# ---------------------------------------------------------------------------
# Static CWE mapping by finding_type prefix / pattern
# ---------------------------------------------------------------------------

_SECRET_CWE: dict[str, CweEntry] = {
    "secret:aws-access-key-id": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "secret:aws-secret-access-key": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "secret:private-key-header": CweEntry(
        "CWE-321", "Use of Hard-coded Cryptographic Key", 9.1,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
    ),
    "secret:generic-api-key": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "secret:bearer-token": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "secret:password-assignment": CweEntry(
        "CWE-259", "Use of Hard-coded Password", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "secret:connection-string-password": CweEntry(
        "CWE-259", "Use of Hard-coded Password", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "secret:github-token": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "secret:gitlab-token": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "secret:slack-token": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
}

_LLM_CWE: dict[str, CweEntry] = {
    "llm:Injection": CweEntry(
        "CWE-89", "SQL Injection", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "llm:XSS": CweEntry(
        "CWE-79", "Cross-site Scripting", 6.1,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
    ),
    "llm:AuthZ": CweEntry(
        "CWE-862", "Missing Authorization", 8.1,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
    ),
    "llm:AuthN": CweEntry(
        "CWE-287", "Improper Authentication", 8.1,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
    ),
    "llm:Crypto": CweEntry(
        "CWE-327", "Use of Broken Crypto Algorithm", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "llm:PathTraversal": CweEntry(
        "CWE-22", "Path Traversal", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "llm:SSRF": CweEntry(
        "CWE-918", "Server-Side Request Forgery", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "llm:Deserialization": CweEntry(
        "CWE-502", "Deserialization of Untrusted Data", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "llm:Logging": CweEntry(
        "CWE-532", "Info Exposure Through Log Files", 5.3,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    ),
    "llm:IDOR": CweEntry(
        "CWE-639", "Insecure Direct Object Reference", 6.5,
        "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N",
    ),
    "llm:CommandInjection": CweEntry(
        "CWE-78", "OS Command Injection", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "llm:MassAssignment": CweEntry(
        "CWE-915", "Mass Assignment", 6.5,
        "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N",
    ),
    "llm:HardcodedSecret": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
}

# Severity-based fallbacks when no specific mapping is found
_SEVERITY_FALLBACK: dict[str, CweEntry] = {
    "critical": CweEntry(
        "CWE-20", "Improper Input Validation", 9.8,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    ),
    "high": CweEntry(
        "CWE-20", "Improper Input Validation", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "medium": CweEntry(
        "CWE-20", "Improper Input Validation", 5.3,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    ),
    "low": CweEntry(
        "CWE-20", "Improper Input Validation", 3.1,
        "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N",
    ),
}

# PHI / entropy prefixes with fixed CWEs
_PREFIX_CWE: dict[str, CweEntry] = {
    "phi:": CweEntry(
        "CWE-359", "Exposure of Private Personal Information", 6.5,
        "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N",
    ),
    "entropy:": CweEntry(
        "CWE-798", "Use of Hard-coded Credentials", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
    "sca:": CweEntry(
        "CWE-1395", "Dependency on Vulnerable Third-Party Component", 7.5,
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    ),
}


def lookup_cwe(finding_type: str, severity: str = "medium") -> CweEntry:
    """Return the CWE entry for a finding type, falling back to severity-based default."""
    # Exact match (secret rules, LLM categories)
    if finding_type in _SECRET_CWE:
        return _SECRET_CWE[finding_type]
    if finding_type in _LLM_CWE:
        return _LLM_CWE[finding_type]

    # Prefix match (phi:*, entropy:*, sca:*)
    for prefix, entry in _PREFIX_CWE.items():
        if finding_type.startswith(prefix):
            return entry

    # Fallback by severity
    return _SEVERITY_FALLBACK.get(severity, _SEVERITY_FALLBACK["medium"])


def enrich_finding(finding_dict: dict) -> dict:
    """Add cwe_id, cvss_score, cvss_vector to a finding dict in-place and return it."""
    entry = lookup_cwe(finding_dict.get("finding_type", ""), finding_dict.get("severity", "medium"))
    finding_dict["cwe_id"] = entry.cwe_id
    finding_dict["cvss_score"] = entry.cvss_score
    finding_dict["cvss_vector"] = entry.cvss_vector
    return finding_dict
