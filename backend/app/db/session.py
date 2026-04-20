from urllib.parse import unquote

from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings


def _safe_database_url(raw: str):
    """Decode percent-encoded passwords and return a proper SQLAlchemy URL."""
    try:
        scheme_end = raw.index("://") + 3
        rest = raw[scheme_end:]
        at_idx = rest.rindex("@")
        creds = rest[:at_idx]
        colon_idx = creds.index(":")
        password = creds[colon_idx + 1:]
        real_password = unquote(password)
        url = make_url(raw)
        return url.set(password=real_password)
    except (ValueError, IndexError):
        return make_url(raw)


engine = create_async_engine(_safe_database_url(settings.DATABASE_URL), echo=settings.DEBUG)

async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
