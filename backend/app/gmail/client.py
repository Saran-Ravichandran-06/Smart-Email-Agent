from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

GMAIL_API_SERVICE = "gmail"
GMAIL_API_VERSION = "v1"


class GmailApiError(Exception):
    """Raised when the Gmail API returns an error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def build_gmail_service(credentials: Credentials):
    try:
        return build(
            GMAIL_API_SERVICE,
            GMAIL_API_VERSION,
            credentials=credentials,
            cache_discovery=False,
        )
    except Exception as exc:
        raise GmailApiError("Failed to initialize Gmail API client.") from exc


def execute_gmail_request(request):
    try:
        return request.execute()
    except HttpError as exc:
        status = getattr(exc.resp, "status", None)
        detail = getattr(exc, "reason", None) or str(exc)
        raise GmailApiError(
            f"Gmail API request failed: {detail}",
            status_code=int(status) if status else None,
        ) from exc
    except Exception as exc:
        raise GmailApiError("Unexpected Gmail API error.") from exc
