from pydantic import BaseModel, ConfigDict, EmailStr


class AuthUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str | None
    google_id: str | None
    gmail_connected: bool


class OAuthCallbackResponse(BaseModel):
    message: str
    user: AuthUserResponse


class EmailSyncResponse(BaseModel):
    message: str
    synced: int
    skipped: int
    total_fetched: int
