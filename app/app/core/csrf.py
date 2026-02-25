from fastapi import Request, HTTPException
from .security import generate_token


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = generate_token(24)
        request.session["csrf_token"] = token
    return token


def validate_csrf(request: Request, token: str | None) -> None:
    session_token = request.session.get("csrf_token")
    if not token or not session_token or token != session_token:
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
