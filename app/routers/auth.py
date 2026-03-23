from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_token, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo

router = APIRouter(prefix='/api/auth', tags=['Auth'])


@router.post('/token', response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    Login dengan username + password → dapat JWT token.

    Token berlaku selama JWT_EXPIRE_HOURS (default 24 jam).
    Kirim token di header setiap request:
        Authorization: Bearer <token>
    """
    user = authenticate_user(body.username, body.password, db)
    return create_token(user.username)


@router.get('/me', response_model=UserInfo)
def me(current_user: User = Depends(get_current_user)):
    """Cek identitas akun yang sedang login."""
    return current_user
