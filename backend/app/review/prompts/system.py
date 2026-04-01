"""System prompt for the AI code-review persona."""

# Output JSON schema shared with the LLM and used for validation downstream.
REVIEW_FINDING_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": [
            "severity",
            "category",
            "file",
            "line",
            "issue",
            "explanation",
            "suggestion",
        ],
        "properties": {
            "severity": {
                "type": "string",
                "enum": ["critical", "high", "medium", "low"],
            },
            "category": {
                "type": "string",
                "description": "OWASP or security category, e.g. 'Injection', 'Broken Access Control', 'Cryptographic Failure', 'Hardcoded Secret', 'Insecure Transport', 'Sensitive Data Exposure'.",
            },
            "file": {
                "type": "string",
                "description": "File path from the diff header.",
            },
            "line": {
                "type": "integer",
                "description": "Approximate line number in the new file.",
            },
            "issue": {
                "type": "string",
                "description": "One-sentence summary of the problem.",
            },
            "explanation": {
                "type": "string",
                "description": "Why this is a security risk (2-3 sentences max).",
            },
            "suggestion": {
                "type": "string",
                "description": "Concrete remediation advice or code fix.",
            },
        },
        "additionalProperties": False,
    },
}

SYSTEM_PROMPT = """\
You are a senior security engineer performing a code review on a unified diff.

## Your task
Analyse ONLY the **added lines** (lines starting with `+`) in the diff.
Identify security vulnerabilities, data leaks, hardcoded secrets, and dangerous anti-patterns.
Ignore style issues, formatting, naming conventions, and non-security concerns.

## Output rules
1. Return a JSON array of findings. Each finding MUST have exactly these keys:
   - "severity": one of "critical", "high", "medium", "low"
   - "category": OWASP or security category (e.g. "Injection", "Hardcoded Secret", "Insecure Transport")
   - "file": the file path from the diff header
   - "line": approximate line number in the new file
   - "issue": one-sentence summary
   - "explanation": why this is a risk (2-3 sentences)
   - "suggestion": concrete remediation
2. If the diff contains NO security issues, return an empty array: `[]`
3. Return ONLY the JSON array — no markdown fences, no commentary, no wrapper object.\
"""


def build_review_prompt(diff_text: str) -> list[dict]:
    """Return the messages list for a code-review chat completion call."""
    from .few_shot import FEW_SHOT_EXAMPLES  # deferred to avoid circular imports

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for example in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example["diff"]})
        messages.append({"role": "assistant", "content": example["response"]})
    messages.append({"role": "user", "content": diff_text})
    return messages
