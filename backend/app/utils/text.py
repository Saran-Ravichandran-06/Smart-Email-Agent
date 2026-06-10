import html
import re
from html.parser import HTMLParser


class _HTMLTextExtractor(HTMLParser):
    """Extract visible text while skipping script and style blocks."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "head"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "head"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts)


def decode_text(value: str) -> str:
    if not value:
        return ""
    try:
        return html.unescape(value)
    except Exception:
        return value


def strip_html(value: str) -> str:
    if not value:
        return ""
    if "<" not in value or ">" not in value:
        return value

    try:
        parser = _HTMLTextExtractor()
        parser.feed(value)
        parser.close()
        return parser.get_text()
    except Exception:
        return re.sub(r"<[^>]+>", " ", value)


def normalize_whitespace(value: str) -> str:
    if not value:
        return ""

    text = value.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_repeated_separators(value: str) -> str:
    if not value:
        return ""
    patterns = [
        r"-{5,}",
        r"_{5,}",
        r"={5,}",
        r"\*{5,}",
    ]
    result = value
    for pattern in patterns:
        result = re.sub(pattern, "\n", result)
    return result
