"""Software Composition Analysis (SCA) engine.

Scans parsed diffs for changes to dependency manifest files
(requirements.txt, package.json, etc.) and queries the OSV.dev API
to detect known vulnerabilities in added dependencies.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from app.git.diff_parser import ParsedDiff

logger = logging.getLogger(__name__)

_OSV_API_URL = "https://api.osv.dev/v1/query"
_OSV_TIMEOUT = 10.0  # seconds per request

# Which files we recognise as dependency manifests
_MANIFEST_PATTERNS: dict[str, str] = {
    "requirements.txt": "PyPI",
    "requirements-dev.txt": "PyPI",
    "requirements-prod.txt": "PyPI",
    "setup.cfg": "PyPI",
    "Pipfile.lock": "PyPI",
    "poetry.lock": "PyPI",
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "npm",
    "go.mod": "Go",
    "go.sum": "Go",
    "Gemfile.lock": "RubyGems",
    "pom.xml": "Maven",
    "build.gradle": "Maven",
    "Cargo.lock": "crates.io",
    "composer.lock": "Packagist",
}


@dataclass
class ScaDependency:
    """A single dependency extracted from a manifest."""
    name: str
    version: str
    ecosystem: str
    file_path: str
    line_number: int


@dataclass
class ScaFinding:
    """A vulnerability found in a dependency."""
    rule_name: str
    severity: str
    description: str
    matched_text: str
    file_path: str
    line_number: int
    confidence: float
    cve_id: str | None
    osv_id: str
    affected_package: str
    affected_version: str


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

# requirements.txt: package==version or package>=version
_PIP_RE = re.compile(r"^\s*([A-Za-z0-9_][A-Za-z0-9._-]*)\s*[=~<>!]=\s*([^\s;#,]+)")

# package.json: "name": "^1.2.3"
_NPM_RE = re.compile(r'^\s*"([^"]+)"\s*:\s*"[~^]?(\d+\.\d+[^"]*)"')

# go.mod: require github.com/pkg v1.2.3
_GO_RE = re.compile(r"^\s*(?:require\s+)?([A-Za-z0-9_./-]+)\s+(v[\d.]+)")


def _detect_ecosystem(file_path: str) -> str | None:
    """Return the OSV ecosystem for a file path, or None."""
    for pattern, eco in _MANIFEST_PATTERNS.items():
        if file_path.endswith(pattern):
            return eco
    return None


def _extract_dependencies(parsed_diff: ParsedDiff) -> list[ScaDependency]:
    """Extract newly-added dependencies from parsed diff."""
    deps: list[ScaDependency] = []

    for file_diff in parsed_diff.files:
        file_path = file_diff.new_path or file_diff.old_path or ""
        ecosystem = _detect_ecosystem(file_path)
        if ecosystem is None:
            continue

        for line in file_diff.added_lines:
            content = line.content.strip()
            if not content or content.startswith("#"):
                continue

            match = None
            if ecosystem == "PyPI":
                match = _PIP_RE.match(content)
            elif ecosystem == "npm":
                match = _NPM_RE.match(content)
            elif ecosystem == "Go":
                match = _GO_RE.match(content)

            if match:
                deps.append(ScaDependency(
                    name=match.group(1),
                    version=match.group(2),
                    ecosystem=ecosystem,
                    file_path=file_path,
                    line_number=line.line_number,
                ))

    return deps


def _query_osv(dep: ScaDependency) -> list[dict]:
    """Query OSV.dev for vulnerabilities affecting a specific package version."""
    payload = {
        "package": {
            "name": dep.name,
            "ecosystem": dep.ecosystem,
        },
        "version": dep.version,
    }
    try:
        with httpx.Client(timeout=_OSV_TIMEOUT) as client:
            resp = client.post(_OSV_API_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("vulns", [])
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("OSV query failed for %s@%s: %s", dep.name, dep.version, exc)
        return []


def _osv_to_severity(vuln: dict) -> str:
    """Extract severity from OSV vulnerability data."""
    severity_list = vuln.get("severity", [])
    for sev in severity_list:
        score_str = sev.get("score", "")
        try:
            score = float(score_str)
            if score >= 9.0:
                return "critical"
            elif score >= 7.0:
                return "high"
            elif score >= 4.0:
                return "medium"
            else:
                return "low"
        except (ValueError, TypeError):
            continue

    # Fallback: check database_specific
    db_specific = vuln.get("database_specific", {})
    db_severity = db_specific.get("severity", "").upper()
    if db_severity in ("CRITICAL",):
        return "critical"
    elif db_severity in ("HIGH",):
        return "high"
    elif db_severity in ("MODERATE", "MEDIUM"):
        return "medium"
    return "high"  # Default for known vulns


def _extract_cve(vuln: dict) -> str | None:
    """Extract CVE ID from OSV aliases."""
    for alias in vuln.get("aliases", []):
        if alias.startswith("CVE-"):
            return alias
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_diff_for_sca(parsed_diff: ParsedDiff) -> list[ScaFinding]:
    """Scan a parsed diff for vulnerable dependencies using the OSV API.

    Args:
        parsed_diff: Output from ``parse_unified_diff()``.

    Returns:
        A list of ``ScaFinding`` objects, one per known vulnerability.
    """
    deps = _extract_dependencies(parsed_diff)
    if not deps:
        return []

    findings: list[ScaFinding] = []

    for dep in deps:
        vulns = _query_osv(dep)
        for vuln in vulns:
            osv_id = vuln.get("id", "UNKNOWN")
            summary = vuln.get("summary", f"Known vulnerability in {dep.name}")
            cve_id = _extract_cve(vuln)
            severity = _osv_to_severity(vuln)

            findings.append(ScaFinding(
                rule_name=f"sca:{osv_id}",
                severity=severity,
                description=f"{dep.name}@{dep.version}: {summary}",
                matched_text=f"{dep.name}=={dep.version}",
                file_path=dep.file_path,
                line_number=dep.line_number,
                confidence=0.95,
                cve_id=cve_id,
                osv_id=osv_id,
                affected_package=dep.name,
                affected_version=dep.version,
            ))

    return findings
