"""
Koneksi ke database MIS — READ ONLY.

PENTING:
- Gunakan MySQL user yang hanya punya hak SELECT
- Koneksi ini TIDAK boleh digunakan untuk write apapun
- Aktifkan dengan MIS_DB_ENABLED=True di .env
"""
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from app.config import settings

_mis_engine = None


def get_mis_engine():
    """Lazy init engine MIS. Return None jika fitur dinonaktifkan."""
    global _mis_engine
    if not settings.mis_db_enabled:
        return None
    if _mis_engine is None:
        _mis_engine = create_engine(
            settings.mis_database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={'connect_timeout': settings.mis_query_timeout},
        )
    return _mis_engine


def test_mis_connection() -> tuple[bool, str]:
    """Test koneksi ke MIS DB. Return (success, message)."""
    engine = get_mis_engine()
    if engine is None:
        return False, "MIS_DB_ENABLED=False di .env"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "Koneksi berhasil"
    except OperationalError as e:
        return False, str(e)
