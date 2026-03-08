"""HTML conversion and metadata helpers for SharePoint content."""

from __future__ import annotations

import html as html_lib
import re


def extract_webparts_html(webparts: list[dict]) -> str:
    """Extract readable HTML from a list of web parts."""
    fragments: list[str] = []

    for webpart in webparts:
        odata_type = webpart.get("@odata.type") or ""

        if "textWebPart" in odata_type:
            inner_html = webpart.get("innerHtml") or ""
            if inner_html:
                fragments.append(inner_html)
            continue

        server_processed = (webpart.get("data") or {}).get(
            "serverProcessedContent"
        ) or {}
        searchable_plain_texts = (
            server_processed.get("searchablePlainTexts") or []
        )
        for entry in searchable_plain_texts:
            value = entry.get("value", "")
            if value:
                fragments.append(value)

    return "\n\n".join(fragments)


def html_to_plain_text(html: str) -> str:
    """Convert HTML to clean plain text."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def parse_site_url(url: str) -> tuple[str, str]:
    """Parse SharePoint site URL into ``(host, path)``."""
    trimmed = url.rstrip("/")
    cleaned = trimmed.replace("https://", "").replace("http://", "")
    parts = cleaned.split("/", 1)
    host = parts[0]
    path = parts[1] if len(parts) > 1 else ""
    return host, path


def get_folder_path(item: dict) -> str:
    """Extract folder path from a drive item."""
    parent = item.get("parentReference") or {}
    path = parent.get("path") or ""

    if ":/" in path:
        return path.split(":/", 1)[1]
    if ":" in path:
        return path.split(":", 1)[1].lstrip("/")
    return ""


__all__ = [
    "extract_webparts_html",
    "get_folder_path",
    "html_to_plain_text",
    "parse_site_url",
]
