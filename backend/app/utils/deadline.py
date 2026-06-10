from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def parse_deadline_value(
    value: str | None,
    *,
    reference: datetime | None = None,
) -> tuple[datetime | None, str | None]:
    """Parse deadline string into datetime when possible; always keep raw text."""
    if not value or not str(value).strip():
        return None, None

    text = str(value).strip()
    if text.lower() in {"null", "none", "n/a", ""}:
        return None, None

    iso_candidates = (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    )
    for fmt in iso_candidates:
        try:
            parsed = datetime.strptime(text[:19], fmt)
            return parsed.replace(tzinfo=timezone.utc), text
        except ValueError:
            continue

    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed, text
    except Exception:
        pass

    return None, text
