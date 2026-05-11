"""One-time script to remove old cli-scan and owner/repo project data."""
import asyncio
from sqlalchemy import text
from app.db.session import engine as async_engine


async def cleanup():
    async with async_engine.begin() as conn:
        # Show current state
        rows = await conn.execute(text("SELECT DISTINCT repository FROM scans"))
        print("Existing repositories in scans:", [r[0] for r in rows.all()])

        rows = await conn.execute(text("SELECT DISTINCT repository FROM user_projects"))
        print("Existing repositories in user_projects:", [r[0] for r in rows.all()])

        # Delete findings linked to old scans
        r1 = await conn.execute(text(
            "DELETE FROM scan_findings WHERE scan_id IN "
            "(SELECT id FROM scans WHERE repository = 'cli-scan' OR repository LIKE '%/%')"
        ))
        print(f"Deleted {r1.rowcount} scan_findings")

        # Delete old scans
        r2 = await conn.execute(text(
            "DELETE FROM scans WHERE repository = 'cli-scan' OR repository LIKE '%/%'"
        ))
        print(f"Deleted {r2.rowcount} scans")

        # Delete old user_projects
        r3 = await conn.execute(text(
            "DELETE FROM user_projects WHERE repository = 'cli-scan' OR repository LIKE '%/%'"
        ))
        print(f"Deleted {r3.rowcount} user_projects")

        print("\nCleanup done!")


if __name__ == "__main__":
    asyncio.run(cleanup())
