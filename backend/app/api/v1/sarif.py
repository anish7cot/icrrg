"""SARIF 2.1.0 export endpoint.

GET /api/v1/sarif/{scan_id} — export scan findings in SARIF 2.1.0 JSON format
for integration with GitHub Code Scanning, VS Code SARIF Viewer, etc.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.db.models.scan import Scan
from app.db.models.scan_finding import ScanFinding
from app.api.deps import get_current_user, get_user_repos
from app.db.models.user import User
from app.detection.cwe_mapping import lookup_cwe

router = APIRouter(prefix="/api/v1/sarif", tags=["sarif"])

_SARIF_SCHEMA = "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
_TOOL_NAME = "SecureDiff ICRRG"
_TOOL_VERSION = "1.0.0"

# SARIF severity mapping
_SEVERITY_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
}

_LEVEL_RANK = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
}


def _build_sarif_document(scan: Scan, findings: list[ScanFinding]) -> dict:
    """Build a SARIF 2.1.0 compliant JSON document from scan findings."""

    # Collect unique rules
    rules_map: dict[str, dict] = {}
    results: list[dict] = []

    for f in findings:
        rule_id = f.finding_type
        cwe = lookup_cwe(f.finding_type, f.severity)

        if rule_id not in rules_map:
            rule_descriptor: dict = {
                "id": rule_id,
                "name": rule_id.replace(":", "_").replace("-", "_"),
                "shortDescription": {"text": rule_id},
                "defaultConfiguration": {
                    "level": _SEVERITY_MAP.get(f.severity, "warning"),
                },
                "properties": {
                    "tags": [cwe.cwe_id],
                    "security-severity": str(_LEVEL_RANK.get(f.severity, 0.5) * 10),
                },
                "helpUri": f"https://cwe.mitre.org/data/definitions/{cwe.cwe_id.split('-')[1]}.html",
            }
            rules_map[rule_id] = rule_descriptor

        # Build result
        result: dict = {
            "ruleId": rule_id,
            "ruleIndex": list(rules_map.keys()).index(rule_id),
            "level": _SEVERITY_MAP.get(f.severity, "warning"),
            "message": {"text": f.message},
            "properties": {
                "confidence": f.confidence,
                "cwe": cwe.cwe_id,
                "cvss_score": cwe.cvss_score,
                "cvss_vector": cwe.cvss_vector,
            },
        }

        # Location (if file path is known)
        if f.file_path:
            location: dict = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": f.file_path,
                        "uriBaseId": "%SRCROOT%",
                    },
                }
            }
            if f.line_number and f.line_number > 0:
                location["physicalLocation"]["region"] = {
                    "startLine": f.line_number,
                }
            result["locations"] = [location]

        if f.reasoning:
            result["message"]["markdown"] = f"**Reasoning:** {f.reasoning}"

        results.append(result)

    sarif = {
        "$schema": _SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": _TOOL_NAME,
                        "version": _TOOL_VERSION,
                        "informationUri": "https://github.com/securediff/icrrg",
                        "rules": list(rules_map.values()),
                    }
                },
                "results": results,
                "invocations": [
                    {
                        "executionSuccessful": scan.status == "completed",
                        "endTimeUtc": (
                            scan.updated_at.isoformat() + "Z"
                            if scan.updated_at else datetime.utcnow().isoformat() + "Z"
                        ),
                    }
                ],
                "properties": {
                    "scan_id": str(scan.id),
                    "repository": scan.repository,
                    "commit_hash": scan.commit_hash,
                    "risk_score": scan.risk_score,
                    "reasoning_level": scan.reasoning_level,
                },
            }
        ],
    }
    return sarif


@router.get("/{scan_id}")
async def export_sarif(
    scan_id: uuid.UUID,
    repos: list[str] = Depends(get_user_repos),
    session: AsyncSession = Depends(get_session),
):
    """Export a scan's findings as SARIF 2.1.0 JSON."""
    stmt = (
        select(Scan)
        .options(selectinload(Scan.findings))
        .where(Scan.id == scan_id)
    )
    if repos:
        stmt = stmt.where(Scan.repository.in_(repos))

    result = await session.execute(stmt)
    scan = result.scalar_one_or_none()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    sarif_doc = _build_sarif_document(scan, scan.findings)

    return JSONResponse(
        content=sarif_doc,
        media_type="application/sarif+json",
        headers={
            "Content-Disposition": f'attachment; filename="scan-{scan_id}.sarif"',
        },
    )
