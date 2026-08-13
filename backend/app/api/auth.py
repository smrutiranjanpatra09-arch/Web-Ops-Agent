from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.security import create_access_token, verify_password
from backend.app.database.session import get_db
from backend.app.models.user import Role, User
from backend.app.schemas.auth import CurrentUserResponse, LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).one_or_none()
    if user is None or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password.")

    role = db.get(Role, user.role_id)
    token = create_access_token(user.id, role.name)
    return LoginResponse(access_token=token, user_id=user.id, display_name=user.display_name, role=role.name)


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.get(Role, user.role_id)
    return CurrentUserResponse(id=user.id, email=user.email, display_name=user.display_name, role=role.name)
