from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import User


ROLE_ORDER = {"viewer": 1, "manager": 2, "admin": 3}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid session")
    return user


def require_role(min_role: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if ROLE_ORDER.get(user.role, 0) < ROLE_ORDER[min_role]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker
