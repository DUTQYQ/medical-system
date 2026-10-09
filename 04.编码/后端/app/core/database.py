from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings


def now():
    """MySQL DATETIME stores China local time without a timezone suffix."""
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# Never create, migrate, truncate or seed the production database at startup.
# An unset URL keeps import/tools usable; startup rejects it before serving.
engine = create_engine(settings.database_url or 'sqlite://', pool_pre_ping=True,
                       **({'connect_args': {'check_same_thread': False}} if settings.database_url.startswith('sqlite:') else {}))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        try:
            yield session
        except BaseException:
            session.rollback()
            raise
