"""
JWT Authentication:
- Hash password dengan bcrypt
- Buat dan verifikasi JWT token
- Dependency get_current_user untuk proteksi endpoint
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
bearer_scheme = HTTPBearer()


# ── Password ───────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── JWT ────────────────────────────────────────────────────────────────────────

def create_token(username: str) -> dict:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {'sub': username, 'exp': expire}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {
        'access_token': token,
        'token_type': 'bearer',
        'expires_in_hours': settings.jwt_expire_hours,
    }


def decode_token(token: str) -> str:
    """Decode JWT dan kembalikan username. Raise HTTPException jika tidak valid."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get('sub')
        if not username:
            raise JWTError()
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token tidak valid atau sudah kadaluarsa.',
            headers={'WWW-Authenticate': 'Bearer'},
        )


# ── Dependency ─────────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency untuk endpoint yang butuh autentikasi.
    Pakai dengan: current_user: User = Depends(get_current_user)
    """
    username = decode_token(credentials.credentials)

    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Akun tidak ditemukan atau sudah dinonaktifkan.',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # Update last_login
    user.last_login = datetime.utcnow()
    db.commit()

    return user


def authenticate_user(username: str, password: str, db: Session) -> User:
    """Verifikasi username + password, kembalikan User jika valid."""
    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Username atau password salah.',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return user
