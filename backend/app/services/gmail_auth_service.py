import httpx
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.auth.oauth import refresh_credentials_if_needed
from app.gmail.client import build_gmail_service
from app.gmail.service import GmailService
from app.models.user import User


async def fetch_google_user_profile(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()


def get_gmail_service_for_user(
    db: Session,
    user: User,
    credentials: Credentials | None = None,
) -> GmailService:
    credentials = credentials or refresh_credentials_if_needed(db, user)
    client = build_gmail_service(credentials)
    return GmailService(client)
