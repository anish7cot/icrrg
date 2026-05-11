from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.api.v1.scans import router as scans_router
from app.api.v1.reports import router as reports_router
from app.api.v1.stats import router as stats_router
from app.api.v1.auth import router as auth_router
from app.api.v1.eval import router as eval_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.scoreboard import router as scoreboard_router

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(scans_router)
app.include_router(reports_router)
app.include_router(stats_router)
app.include_router(eval_router)
app.include_router(feedback_router)
app.include_router(metrics_router)
app.include_router(scoreboard_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/v1/")
async def api_root():
    return {"message": "ICRRG API v1"}


@app.get("/api/v1/db-check")
async def db_check(session: AsyncSession = Depends(get_session)):
    result = await session.execute(text("SELECT 1"))
    return {"db": "connected", "result": result.scalar()}
