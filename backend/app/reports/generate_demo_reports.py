"""Generate all 3 audience reports and save as demo backups.

Usage:  cd backend && poetry run python -m app.reports.generate_demo_reports
"""

import asyncio
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.reports.aggregator import aggregate_scan_data
from app.reports.service import generate_report_content

BACKUP_DIR = Path(__file__).parent.parent.parent / "demo_reports"

AUDIENCES = ["developer", "manager", "leadership"]


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async with sf() as session:
        agg = await aggregate_scan_data(
            session, "acme-webapp", date(2026, 3, 17), date(2026, 3, 31)
        )
    await engine.dispose()

    print(f"Aggregation: {agg.total_scans} scans, {agg.total_findings} findings\n")

    BACKUP_DIR.mkdir(exist_ok=True)

    for audience in AUDIENCES:
        print(f"Generating {audience} report...")
        content = await generate_report_content(agg, audience)

        out_path = BACKUP_DIR / f"{audience}_report.md"
        out_path.write_text(content, encoding="utf-8")
        print(f"  Saved {out_path} ({len(content)} chars)\n")

    print("All demo reports generated and saved!")


if __name__ == "__main__":
    asyncio.run(main())
