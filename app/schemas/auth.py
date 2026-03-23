from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in_hours: int


class UserInfo(BaseModel):
    id: str
    username: str
    description: str
    is_active: bool

    model_config = {'from_attributes': True}
