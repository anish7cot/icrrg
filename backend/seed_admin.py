"""One-shot script to seed/update the admin user."""
import asyncio
from app.db.session import async_session
from app.api.auth import hash_password
from sqlalchemy import update, select
from app.db.models.user import User


async def main():
    async with async_session() as s:
        result = await s.execute(select(User).where(User.username == "admin"))
        user = result.scalar_one_or_none()
        if user:
            await s.execute(
                update(User)
                .where(User.username == "admin")
                .values(hashed_password=hash_password("Admin@123"))
            )
            await s.commit()
            print("admin password updated to Admin@123")
        else:
            s.add(User(username="admin", hashed_password=hash_password("Admin@123")))
            await s.commit()
            print("admin user created with password Admin@123")


asyncio.run(main())
