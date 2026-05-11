"""Mock LLM provider — returns canned responses for testing and demo backup."""

from __future__ import annotations

import json
import re

from .base import BaseLLMProvider, LLMResponse, ReviewFinding, TokenUsage

# Pre-loaded impressive responses keyed by simple heuristics.
_CANNED: dict[str, list[ReviewFinding]] = {
    "sql_injection": [
        ReviewFinding(
            severity="critical",
            category="Injection",
            file="app/db.py",
            line=14,
            issue="SQL query built via string concatenation with untrusted input.",
            explanation=(
                "Concatenating user-supplied values directly into a SQL string "
                "enables SQL injection. An attacker can read, modify, or delete "
                "arbitrary data."
            ),
            suggestion="Use parameterised queries: `db.execute(\"SELECT * FROM users WHERE id = %s\", (user_id,))`.",
        ),
    ],
    "hardcoded_secret": [
        ReviewFinding(
            severity="critical",
            category="Hardcoded Secret",
            file="config/settings.py",
            line=3,
            issue="Secret key is hardcoded in source code.",
            explanation=(
                "Committing credentials to version control exposes them to every "
                "developer and CI system. If the repo leaks, the secret is compromised."
            ),
            suggestion="Load from an environment variable or a secrets manager.",
        ),
    ],
    "command_injection": [
        ReviewFinding(
            severity="critical",
            category="Injection",
            file="app/service.py",
            line=15,
            issue="Command injection via unsanitized input passed to subprocess with shell=True.",
            explanation=(
                "Concatenating user input into a shell command allows an attacker "
                "to execute arbitrary OS commands by injecting shell metacharacters."
            ),
            suggestion="Use subprocess.run with a list of arguments instead of shell=True, or use a dedicated HTTP library.",
        ),
    ],
    "insecure_http": [
        ReviewFinding(
            severity="high",
            category="Insecure Transport",
            file="app/api/webhook.py",
            line=7,
            issue="HTTP request sent over plaintext with TLS verification disabled.",
            explanation=(
                "Using http:// transmits data in cleartext. verify=False disables "
                "certificate validation, enabling man-in-the-middle attacks."
            ),
            suggestion="Switch to https:// and remove verify=False.",
        ),
    ],
}

# Simple pattern → canned key mapping.
_PATTERNS: list[tuple[str, str]] = [
    (r"execute\(.*\+|SELECT.*\+|INSERT.*\+", "sql_injection"),
    (r"subprocess\.run\(.*shell\s*=\s*True", "command_injection"),
    (r"API_KEY\s*=\s*['\"]|SECRET.*=\s*['\"]|PASSWORD\s*=\s*['\"]", "hardcoded_secret"),
    (r"http://|verify\s*=\s*False", "insecure_http"),
]


class MockProvider(BaseLLMProvider):
    """Returns canned findings based on simple diff heuristics — no API call."""

    async def review(self, diff_text: str) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        seen: set[str] = set()

        for pattern, key in _PATTERNS:
            if key not in seen and re.search(pattern, diff_text, re.IGNORECASE):
                findings.extend(_CANNED[key])
                seen.add(key)

        return findings

    async def chat(self, messages: list[dict], temperature: float = 0) -> LLMResponse:
        """Mock chat that returns canned correlation/synthesis responses."""
        # Detect what type of call based on system message content
        system_content = messages[0].get("content", "") if messages else ""

        if "threat modeling" in system_content.lower() or "attack chain" in system_content.lower():
            # Level 3: Correlation mock
            content = json.dumps([{
                "chain_id": 1,
                "finding_refs": [0, 1],
                "combined_severity": "critical",
                "attack_narrative": "Combined vulnerabilities create an exploitable attack chain.",
                "compounded_risk": "An attacker could chain these findings to escalate from information disclosure to full system compromise."
            }])
        elif "remediation roadmap" in system_content.lower() or "principal security" in system_content.lower():
            # Level 4: Synthesis mock
            content = json.dumps({
                "overall_risk_rating": "high",
                "executive_summary": "The codebase contains multiple security findings that require immediate attention.",
                "remediation_priority": [{
                    "priority": 1,
                    "finding_refs": [0],
                    "action": "Fix critical vulnerability immediately",
                    "effort": "low",
                    "impact": "high"
                }],
                "architectural_recommendations": [
                    "Implement input validation layer",
                    "Add secrets management solution"
                ]
            })
        else:
            content = "[]"

        mock_usage = TokenUsage(prompt_tokens=150, completion_tokens=80, total_tokens=230)
        return LLMResponse(findings=[], usage=mock_usage, model="mock", duration_ms=50)
