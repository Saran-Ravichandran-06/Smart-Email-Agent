from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.auth.exceptions import InvalidSessionError, NotAuthenticatedError
from app.database.session import get_db
from app.models.oauth_token import OAuthToken
from app.models.user import User

SESSION_USER_ID_KEY = "user_id"


def set_session_user(request: Request, user_id: int) -> None:
    request.session[SESSION_USER_ID_KEY] = user_id


def clear_session(request: Request) -> None:
    request.session.clear()


def get_session_user_id(request: Request) -> int | None:
    user_id = request.session.get(SESSION_USER_ID_KEY)
    if user_id is None:
        return None
    try:
        return int(user_id)
    except (TypeError, ValueError) as exc:
        raise InvalidSessionError("Invalid user id in session.") from exc


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = get_session_user_id(request)
    except InvalidSessionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in with Google.",
        )

    user = (
        db.query(User)
        .options(joinedload(User.oauth_token))
        .filter(User.id == user_id)
        .one_or_none()
    )
    if user is None:
        clear_session(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session user not found. Please log in again.",
        )

    return user


def get_current_user_with_token(
    user: User = Depends(get_current_user),
) -> User:
    if user.oauth_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Gmail is not connected for this user. Please log in again.",
        )
    return user
