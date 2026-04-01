"""spaCy NER + regex pipeline for PHI (Protected Health Information) detection.

Detects:
  - SSN patterns
  - US phone numbers
  - MRN-like IDs
  - Dates of birth near healthcare keywords
  - PERSON entities (via spaCy NER) near healthcare context keywords

Only flags findings when healthcare/patient context is present to avoid
flagging ordinary developer names or test data.
"""

from __future__ import annotations

import re
import spacy
from pydantic import BaseModel

from app.git.diff_parser import ParsedDiff

# ---------------------------------------------------------------------------
# Load spaCy model (singleton)
# ---------------------------------------------------------------------------
_nlp = spacy.load("en_core_web_sm")

# ---------------------------------------------------------------------------
# Healthcare context keywords — used for proximity checks
# ---------------------------------------------------------------------------
_HEALTHCARE_KEYWORDS = re.compile(
    r"(?i)\b(patient|diagnosis|medical|clinical|health|hospital|"
    r"physician|doctor|nurse|treatment|prescription|medication|"
    r"admission|discharge|surgery|lab\s*result|record|hipaa|"
    r"mrn|ssn|dob|insurance|claim|billing|encounter|"
    r"allergies|vitals|chart|ehr|emr)\b"
)

# ---------------------------------------------------------------------------
# PHI regex patterns
# ---------------------------------------------------------------------------

_SSN_RE = re.compile(r"\b(?P<phi>\d{3}-\d{2}-\d{4})\b")

_PHONE_RE = re.compile(
    r"(?P<phi>"
    r"(?:\+?1[-.\s]?)?"                     # optional country code
    r"(?:\(?\d{3}\)?[-.\s]?)"               # area code
    r"\d{3}[-.\s]?\d{4}"                    # subscriber number
    r")\b"
)

_MRN_RE = re.compile(
    r"(?i)(?:mrn|medical\s*record|record\s*(?:number|no|#|id))\s*[:=]?\s*(?P<phi>\d{5,12})\b"
)

_DOB_RE = re.compile(
    r"(?i)(?:dob|date\s*of\s*birth|birth\s*date)\s*[:=]?\s*"
    r"(?P<phi>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"
)


class _PhiRule:
    """A named regex rule for PHI detection."""

    def __init__(self, name: str, pattern: re.Pattern[str], severity: str,
                 confidence: float, needs_context: bool = False):
        self.name = name
        self.pattern = pattern
        self.severity = severity
        self.confidence = confidence
        self.needs_context = needs_context  # if True, require healthcare keywords on same line


_PHI_RULES: list[_PhiRule] = [
    _PhiRule("ssn", _SSN_RE, "critical", 0.95, needs_context=False),
    _PhiRule("phone-number", _PHONE_RE, "high", 0.70, needs_context=True),
    _PhiRule("mrn", _MRN_RE, "critical", 0.90, needs_context=False),  # keyword is in the pattern itself
    _PhiRule("date-of-birth", _DOB_RE, "high", 0.85, needs_context=False),  # keyword is in the pattern
]

# ---------------------------------------------------------------------------
# Path-skip patterns (reuse from other engines)
# ---------------------------------------------------------------------------
_SKIP_PATH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\.example$"),
    re.compile(r"(?i)\.sample$"),
    re.compile(r"(?i)(?:^|/)tests?/"),
    re.compile(r"(?i)_test\.\w+$"),
    re.compile(r"(?i)\.test\.\w+$"),
    re.compile(r"(?i)test_[^/]+\.\w+$"),
    re.compile(r"(?i)/fixtures?/"),
    re.compile(r"(?i)\.md$"),
]

_COMMENT_RE = re.compile(r"^\s*(#|//|/?\*)")


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------
class PhiFinding(BaseModel):
    """A PHI detection finding."""

    rule_name: str           # e.g. "ssn", "person-name", "phone-number"
    description: str
    severity: str            # critical / high / medium
    confidence: float
    file_path: str
    line_number: int
    matched_text: str        # redacted
    entity_type: str         # SSN, PERSON, PHONE, MRN, DOB
    line_content: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact(text: str) -> str:
    if len(text) <= 6:
        return text[:1] + "*" * (len(text) - 1)
    return text[:3] + "*" * (len(text) - 5) + text[-2:]


def _should_skip_path(path: str) -> bool:
    return any(p.search(path) for p in _SKIP_PATH_PATTERNS)


def _has_healthcare_context(line: str) -> bool:
    return bool(_HEALTHCARE_KEYWORDS.search(line))


def _build_context_window(lines_content: list[str], idx: int, window: int = 3) -> str:
    """Build a text window around a line for context checking."""
    start = max(0, idx - window)
    end = min(len(lines_content), idx + window + 1)
    return " ".join(lines_content[start:end])


# ---------------------------------------------------------------------------
# NER-based person detection
# ---------------------------------------------------------------------------

def _detect_person_entities(
    content: str,
    context_text: str,
) -> list[tuple[str, int, int]]:
    """Run spaCy NER on a line, return PERSON entities if healthcare context is present.

    Returns list of (entity_text, start_char, end_char).
    """
    # Only look for person names if healthcare context exists
    if not _has_healthcare_context(context_text):
        return []

    doc = _nlp(content)
    persons = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            persons.append((ent.text, ent.start_char, ent.end_char))
    return persons


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

def scan_diff_for_phi(
    parsed_diff: ParsedDiff,
    *,
    skip_tests: bool = True,
    context_window: int = 3,
) -> list[PhiFinding]:
    """Scan a parsed diff for PHI using regex rules and spaCy NER.

    Args:
        parsed_diff: Output from ``parse_unified_diff()``.
        skip_tests:  Skip test / example files.
        context_window: Number of surrounding lines to check for context.

    Returns:
        List of ``PhiFinding`` objects.
    """
    findings: list[PhiFinding] = []

    for file_diff in parsed_diff.files:
        file_path = file_diff.new_path or file_diff.old_path or "<unknown>"

        if file_diff.is_binary:
            continue
        if skip_tests and _should_skip_path(file_path):
            continue

        added_lines = file_diff.added_lines
        added_contents = [dl.content for dl in added_lines]

        for idx, diff_line in enumerate(added_lines):
            content = diff_line.content

            # Skip comment lines
            if _COMMENT_RE.match(content):
                continue

            context_text = _build_context_window(added_contents, idx, context_window)

            # ── Regex PHI rules ───────────────────────────────────
            for rule in _PHI_RULES:
                match = rule.pattern.search(content)
                if not match:
                    continue
                # If rule needs healthcare context on the line, check
                if rule.needs_context and not _has_healthcare_context(context_text):
                    continue

                phi_text = match.group("phi")
                entity_type_map = {
                    "ssn": "SSN",
                    "phone-number": "PHONE",
                    "mrn": "MRN",
                    "date-of-birth": "DOB",
                }
                findings.append(
                    PhiFinding(
                        rule_name=rule.name,
                        description=f"{entity_type_map.get(rule.name, rule.name)} detected",
                        severity=rule.severity,
                        confidence=rule.confidence,
                        file_path=file_path,
                        line_number=diff_line.line_number,
                        matched_text=_redact(phi_text),
                        entity_type=entity_type_map.get(rule.name, rule.name.upper()),
                        line_content=content,
                    )
                )

            # ── spaCy PERSON NER ──────────────────────────────────
            persons = _detect_person_entities(content, context_text)
            for person_text, _, _ in persons:
                # Skip very short names (likely false positives)
                if len(person_text.strip()) < 4:
                    continue
                findings.append(
                    PhiFinding(
                        rule_name="person-name",
                        description="Person name detected in healthcare context",
                        severity="high",
                        confidence=0.75,
                        file_path=file_path,
                        line_number=diff_line.line_number,
                        matched_text=_redact(person_text),
                        entity_type="PERSON",
                        line_content=content,
                    )
                )

    return findings
