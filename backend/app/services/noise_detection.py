import json
import re
from dataclasses import dataclass
from email.utils import parseaddr

from app.models.email import Email

NOISE_GMAIL_LABELS = frozenset(
    {
        "CATEGORY_PROMOTIONS",
        "CATEGORY_SOCIAL",
        "CATEGORY_UPDATES",
        "CATEGORY_FORUMS",
    }
)

NOISE_LOCAL_PARTS = (
    "no-reply",
    "noreply",
    "donotreply",
    "do-not-reply",
    "notification",
    "notifications",
    "mailer-daemon",
    "postmaster",
    "updates",
    "accounts",
    "account",
    "support",
    "alerts",
    "news",
    "newsletter",
    "marketing",
)

NOISE_SUBJECT_PATTERNS = (
    r"\bunsubscribe\b",
    r"\bnewsletter\b",
    r"\bdigest\b",
    r"\bproduct update\b",
    r"\bautomatic enablement\b",
    r"\brelease notes?\b",
    r"\bwhat'?s new\b",
    r"\bsecurity alert\b",
    r"\bsign[- ]?in alert\b",
    r"\bverification code\b",
    r"\bone[- ]time password\b",
    r"\b2fa\b",
    r"\bmarketing\b",
    r"\bwebinar\b",
    r"\bpromotion\b",
    r"\boffer\b",
    r"\bdiscount\b",
    r"\breceipt\b",
    r"\binvoice\b",
    r"\bpayment (received|failed|receipt)\b",
    r"\bnew feature\b",
    r"\bfeature update\b",
    r"\bproduct announcement\b",
    r"\bannouncing\b",
    r"\bintroducing\b",
    r"\bnew in\b",
    r"\bupdates? to\b",
    r"\baccount alert\b",
    r"\baccount notification\b",
    r"\bpolicy update\b",
    r"\bterms of service\b",
    r"\bprivacy policy\b",
    r"\bchatgpt\b.*\bupdate\b",
    r"\bgoogle\b.*\bnotification\b",
)

NOISE_SENDER_DOMAINS = (
    "accounts.google.com",
    "google.com",
    "notifications.google.com",
    "mail.openai.com",
    "openai.com",
)

NOISE_BODY_PATTERNS = (
    r"\byou are receiving this email because\b",
    r"\bmanage your email preferences\b",
    r"\bview this email in your browser\b",
    r"\bnew features? (are|is) available\b",
    r"\bproduct updates?\b",
    r"\bthis is an automated (message|notification)\b",
    r"\bplease do not reply\b",
)


@dataclass(frozen=True)
class NoiseDetectionResult:
    is_noise: bool
    reason: str | None = None


def address_from_header(value: str | None) -> str:
    _, address = parseaddr(value or "")
    return address.lower().strip()


def local_part(address: str) -> str:
    return address.split("@", 1)[0].lower() if "@" in address else address.lower()


def domain_part(address: str) -> str:
    return address.split("@", 1)[1].lower() if "@" in address else ""


def parse_label_ids(email: Email) -> set[str]:
    if not email.label_ids:
        return set()
    try:
        parsed = json.loads(email.label_ids)
    except (TypeError, ValueError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {str(item) for item in parsed}


def detect_noise_email(email: Email) -> NoiseDetectionResult:
    if (email.priority or "").lower() == "noise":
        return NoiseDetectionResult(True, "noise priority")

    sender_address = address_from_header(email.sender)
    recipient_address = address_from_header(email.recipient)
    sender_local = local_part(sender_address)
    recipient_local = local_part(recipient_address)
    sender_domain = domain_part(sender_address)
    subject = (email.subject or "").lower()
    labels = parse_label_ids(email)
    body_sample = (email.body_raw or email.body_cleaned or email.body or "").lower()[:2000]

    if sender_local.startswith(NOISE_LOCAL_PARTS):
        return NoiseDetectionResult(True, "no-reply or automated sender")
    if recipient_local.startswith(NOISE_LOCAL_PARTS):
        return NoiseDetectionResult(True, "automated recipient")
    if any(sender_domain == domain or sender_domain.endswith(f".{domain}") for domain in NOISE_SENDER_DOMAINS):
        if any(re.search(pattern, subject, flags=re.IGNORECASE) for pattern in NOISE_SUBJECT_PATTERNS):
            return NoiseDetectionResult(True, "automated product/account sender")
    if labels & NOISE_GMAIL_LABELS:
        return NoiseDetectionResult(True, "Gmail noise category")
    if any(re.search(pattern, subject, flags=re.IGNORECASE) for pattern in NOISE_SUBJECT_PATTERNS):
        return NoiseDetectionResult(True, "noise subject")
    if any(re.search(pattern, body_sample, flags=re.IGNORECASE) for pattern in NOISE_BODY_PATTERNS):
        return NoiseDetectionResult(True, "noise body")
    if "list-unsubscribe" in body_sample or "unsubscribe" in body_sample:
        return NoiseDetectionResult(True, "unsubscribe footer")

    return NoiseDetectionResult(False)
