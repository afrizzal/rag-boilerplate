from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # reconnect otomatis jika koneksi MySQL putus
    pool_recycle=3600,        # recycle koneksi setiap 1 jam
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency injection untuk database session di setiap request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
