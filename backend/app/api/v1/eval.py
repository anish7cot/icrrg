"""Evaluation API — run benchmarks and view historical accuracy trends.

POST /api/v1/eval/run   — trigger an evaluation run
GET  /api/v1/eval/runs  — list past runs
GET  /api/v1/eval/runs/{id} — detailed per-scenario breakdown
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.db.models.eval_run import EvalRun

from eval.runner import (
    load_benchmarks,
    run_detection,
    run_llm_review,
    evaluate_scenario,
    aggregate,
)

router = APIRouter(prefix="/api/v1/eval", tags=["eval"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class EvalRunRequest(BaseModel):
    engine: str = "detection"  # "detection", "llm", "all"
    repeat: int = 1  # for LLM consistency


class EvalRunSummary(BaseModel):
    id: uuid.UUID
    engine: str
    model_name: str | None
    precision: float
    recall: float
    f1: float
    tp_count: int
    fp_count: int
    fn_count: int
    total_scenarios: int
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalRunDetail(EvalRunSummary):
    details_json: dict | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# POST /api/v1/eval/run — trigger an evaluation run
# ---------------------------------------------------------------------------

@router.post("/run", response_model=EvalRunSummary, status_code=201)
async def trigger_eval_run(
    body: EvalRunRequest,
    session: AsyncSession = Depends(get_session),
):
    entries = load_benchmarks(body.engine)
    if not entries:
        raise HTTPException(status_code=400, detail=f"No benchmarks for engine={body.engine}")

    all_results = []
    for entry in entries:
        is_llm = entry.engine == "llm"
        line_tol = 2 if is_llm else 0

        runs = body.repeat if is_llm else 1
        for _ in range(runs):
            if is_llm:
                actuals = await run_llm_review(entry.diff)
            else:
                actuals = run_detection(entry.diff)
            result = evaluate_scenario(entry, actuals, line_tol)
            all_results.append(result)

    agg = aggregate(all_results)

    details = [
        {
            "id": r.scenario_id,
            "description": r.description,
            "tp": r.tp, "fp": r.fp, "fn": r.fn,
            "matched": r.matched, "missed": r.missed, "extra": r.extra,
        }
        for r in all_results
    ]

    model_name = settings.REVIEW_MODEL if body.engine in ("llm", "all") else None

    eval_run = EvalRun(
        engine=body.engine,
        model_name=model_name,
        precision=round(agg.precision, 4),
        recall=round(agg.recall, 4),
        f1=round(agg.f1, 4),
        tp_count=agg.tp,
        fp_count=agg.fp,
        fn_count=agg.fn,
        total_scenarios=len(all_results),
        details_json={"scenarios": details},
    )
    session.add(eval_run)
    await session.commit()
    await session.refresh(eval_run)

    return eval_run


# ---------------------------------------------------------------------------
# GET /api/v1/eval/runs — list past runs
# ---------------------------------------------------------------------------

@router.get("/runs", response_model=list[EvalRunSummary])
async def list_eval_runs(
    engine: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(EvalRun).order_by(desc(EvalRun.created_at)).limit(limit)
    if engine:
        stmt = stmt.where(EvalRun.engine == engine)
    result = await session.execute(stmt)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# GET /api/v1/eval/runs/{id} — detailed breakdown
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}", response_model=EvalRunDetail)
async def get_eval_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    run = await session.get(EvalRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run
