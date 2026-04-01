"""Quick test: render all three report templates with real DB data."""

import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.reports.aggregator import aggregate_scan_data
from app.reports.prompt_builder import build_report_prompt


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async with sf() as session:
        agg = await aggregate_scan_data(
            session, "acme-webapp", date(2026, 3, 17), date(2026, 3, 31)
        )
    await engine.dispose()

    print(f"Aggregation: {agg.total_scans} scans, {agg.total_findings} findings\n")

    for audience in ["developer", "manager", "leadership"]:
        prompt = build_report_prompt(agg, audience)
        print(f"{'=' * 60}")
        print(f"  {audience.upper()} TEMPLATE  ({len(prompt)} chars)")
        print(f"{'=' * 60}")
        print(prompt)
        print()


if __name__ == "__main__":
    asyncio.run(main())
