from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


def _require_dev_endpoints_enabled() -> None:
    if not get_settings().enable_dev_endpoints:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development user endpoints are disabled.",
        )


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    _require_dev_endpoints_enabled()
    user = User(
        email=payload.email,
        name=payload.name,
        google_id=payload.google_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    _require_dev_endpoints_enabled()
    return db.query(User).order_by(User.id).all()
