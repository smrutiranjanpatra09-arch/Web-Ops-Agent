from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    display_name: str
    role: str


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
