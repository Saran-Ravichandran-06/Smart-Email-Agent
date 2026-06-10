import base64
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Any, Iterator

from app.gmail.client import execute_gmail_request
from app.gmail.parser import ParsedGmailMessage, parse_gmail_message, parse_thread_metadata


class GmailService:
    """Thin wrapper around Gmail API operations used by sync."""

    def __init__(self, gmail_client) -> None:
        self._client = gmail_client

    def list_inbox_message_ids(
        self,
        *,
        max_results: int = 50,
        page_token: str | None = None,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        request = (
            self._client.users()
            .messages()
            .list(
                userId="me",
                labelIds=label_ids or ["INBOX"],
                maxResults=max_results,
                pageToken=page_token,
            )
        )
        return execute_gmail_request(request)

    def iter_inbox_message_ids(
        self,
        *,
        max_results_per_page: int = 50,
        max_messages: int | None = None,
    ) -> Iterator[str]:
        page_token: str | None = None
        fetched = 0

        while True:
            response = self.list_inbox_message_ids(
                max_results=max_results_per_page,
                page_token=page_token,
            )
            messages = response.get("messages") or []
            for item in messages:
                message_id = item.get("id")
                if message_id:
                    yield message_id
                    fetched += 1
                    if max_messages is not None and fetched >= max_messages:
                        return

            page_token = response.get("nextPageToken")
            if not page_token:
                break

    def get_message(self, message_id: str, *, format: str = "full") -> dict[str, Any]:
        request = (
            self._client.users()
            .messages()
            .get(userId="me", id=message_id, format=format)
        )
        return execute_gmail_request(request)

    def get_message_details(self, message_id: str) -> ParsedGmailMessage:
        message = self.get_message(message_id, format="full")
        return parse_gmail_message(message)

    def get_thread(self, thread_id: str, *, format: str = "metadata") -> dict[str, Any]:
        request = (
            self._client.users()
            .threads()
            .get(userId="me", id=thread_id, format=format)
        )
        return execute_gmail_request(request)

    def get_thread_metadata(self, thread_id: str) -> dict[str, Any]:
        thread = self.get_thread(thread_id, format="metadata")
        return parse_thread_metadata(thread)

    def send_reply(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        from_email: str | None = None,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        message = EmailMessage()
        message["To"] = to
        if from_email:
            name, address = parseaddr(from_email)
            message["From"] = formataddr((name, address)) if name and address else from_email
        message["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
        message.set_content(body.strip())

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        payload: dict[str, Any] = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        request = (
            self._client.users()
            .messages()
            .send(userId="me", body=payload)
        )
        return execute_gmail_request(request)
