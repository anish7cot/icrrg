"""Policy management API — CRUD and evaluation.

POST /api/v1/policies           — create/update a policy (admin/manager only)
GET  /api/v1/policies           — list policies
GET  /api/v1/policies/{repo}    — get policy for a repository
POST /api/v1/policies/evaluate  — evaluate findings against a policy
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models.policy import Policy
from app.api.deps import get_current_user, require_manager_or_admin
from app.db.models.user import User

router = APIRouter(prefix="/api/v1/policies", tags=["policies"])

# Severity ordering for comparison
_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PolicyRequest(BaseModel):
    repository: str = Field(..., description="Repository name (unique)")
    max_severity_allowed: str = Field(
        default="medium",
        description="Maximum allowed severity: critical|high|medium|low",
    )
    required_engines: dict | None = Field(
        default=None,
        description='Engines that must run, e.g. {"regex": true, "sca": true}',
    )
    sla_overrides: dict | None = Field(
        default=None,
        description='SLA hour overrides by severity, e.g. {"critical": 12}',
    )
    block_on_sla_breach: bool = Field(default=False)
    min_confidence: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Minimum confidence for a finding to trigger policy",
    )


class PolicyResponse(BaseModel):
    id: uuid.UUID
    repository: str
    max_severity_allowed: str
    required_engines: dict | None
    sla_overrides: dict | None
    block_on_sla_breach: bool
    min_confidence: float
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicyEvalRequest(BaseModel):
    repository: str
    findings: list[dict] = Field(
        ..., description="List of finding dicts with at least 'severity' and 'confidence'"
    )


class PolicyViolation(BaseModel):
    finding_index: int
    severity: str
    confidence: float
    reason: str


class PolicyEvalResponse(BaseModel):
    policy_exists: bool
    blocked: bool
    violations: list[PolicyViolation]
    max_severity_allowed: str | None = None


# ---------------------------------------------------------------------------
# POST /api/v1/policies — create or update
# ---------------------------------------------------------------------------

@router.post("", response_model=PolicyResponse, status_code=201)
async def create_or_update_policy(
    body: PolicyRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_manager_or_admin),
):
    if body.max_severity_allowed not in _SEVERITY_RANK:
        raise HTTPException(
            status_code=400,
            detail=f"max_severity_allowed must be one of {list(_SEVERITY_RANK.keys())}",
        )

    stmt = select(Policy).where(Policy.repository == body.repository)
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.max_severity_allowed = body.max_severity_allowed
        existing.required_engines = body.required_engines
        existing.sla_overrides = body.sla_overrides
        existing.block_on_sla_breach = body.block_on_sla_breach
        existing.min_confidence = body.min_confidence
        await session.commit()
        await session.refresh(existing)
        return existing

    policy = Policy(
        repository=body.repository,
        max_severity_allowed=body.max_severity_allowed,
        required_engines=body.required_engines,
        sla_overrides=body.sla_overrides,
        block_on_sla_breach=body.block_on_sla_breach,
        min_confidence=body.min_confidence,
        created_by=user.id,
    )
    session.add(policy)
    await session.commit()
    await session.refresh(policy)
    return policy


# ---------------------------------------------------------------------------
# GET /api/v1/policies — list all
# ---------------------------------------------------------------------------

@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(Policy).order_by(Policy.repository)
    result = await session.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /api/v1/policies/{repository} — get policy for repo
# ---------------------------------------------------------------------------

@router.get("/{repository:path}", response_model=PolicyResponse)
async def get_policy(
    repository: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    stmt = select(Policy).where(Policy.repository == repository)
    policy = (await session.execute(stmt)).scalar_one_or_none()
    if policy is None:
        raise HTTPException(status_code=404, detail="No policy for this repository")
    return policy


# ---------------------------------------------------------------------------
# POST /api/v1/policies/evaluate — check findings against a repo policy
# ---------------------------------------------------------------------------

def evaluate_findings_against_policy(
    policy: Policy, findings: list[dict]
) -> PolicyEvalResponse:
    """Pure function: evaluate findings against a policy, return violations."""
    max_rank = _SEVERITY_RANK.get(policy.max_severity_allowed, 1)
    violations: list[PolicyViolation] = []

    for i, f in enumerate(findings):
        sev = f.get("severity", "low")
        confidence = f.get("confidence") or 0.0
        sev_rank = _SEVERITY_RANK.get(sev, 0)

        # Skip low-confidence findings below threshold
        if confidence < policy.min_confidence:
            continue

        if sev_rank > max_rank:
            violations.append(PolicyViolation(
                finding_index=i,
                severity=sev,
                confidence=confidence,
                reason=f"Severity '{sev}' exceeds policy maximum '{policy.max_severity_allowed}'",
            ))

    return PolicyEvalResponse(
        policy_exists=True,
        blocked=len(violations) > 0,
        violations=violations,
        max_severity_allowed=policy.max_severity_allowed,
    )


@router.post("/evaluate", response_model=PolicyEvalResponse)
async def evaluate_policy(
    body: PolicyEvalRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Evaluate a set of findings against the repository's policy."""
    stmt = select(Policy).where(Policy.repository == body.repository)
    policy = (await session.execute(stmt)).scalar_one_or_none()

    if policy is None:
        return PolicyEvalResponse(
            policy_exists=False,
            blocked=False,
            violations=[],
        )

    return evaluate_findings_against_policy(policy, body.findings)
