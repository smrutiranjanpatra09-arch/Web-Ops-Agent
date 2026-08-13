import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.auth.security import decode_access_token
from backend.app.database.session import get_db
from backend.app.models.user import Role, User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(401, "Missing authentication token.")
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token.")

    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(401, "User no longer exists.")
    return user


def require_role(*allowed_role_names: str):
    def _check(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        role = db.get(Role, user.role_id)
        if role is None or role.name not in allowed_role_names:
            raise HTTPException(403, f"Role '{role.name if role else None}' cannot perform this action.")
        return user

    return _check
