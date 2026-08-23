"""Template plumbing shared by every web route."""

from datetime import date, datetime
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.models.base import (
    ContactType,
    FollowUpStatus,
    InteractionType,
    InterestLevel,
    MeetingType,
    NoteSource,
    OpportunityStage,
    OpportunityType,
    PriorityTier,
    Sentiment,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from app.web import TEMPLATES_DIR

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Every enum a form or filter offers, so dropdowns are generated from the
# model rather than hardcoded in a template and left to drift.
ENUMS: dict[str, Any] = {
    "ContactType": ContactType,
    "PriorityTier": PriorityTier,
    "InterestLevel": InterestLevel,
    "FollowUpStatus": FollowUpStatus,
    "TaskType": TaskType,
    "TaskStatus": TaskStatus,
    "TaskPriority": TaskPriority,
    "Sentiment": Sentiment,
    "OpportunityType": OpportunityType,
    "OpportunityStage": OpportunityStage,
    "MeetingType": MeetingType,
    "InteractionType": InteractionType,
    "NoteSource": NoteSource,
}


def label(value: Any) -> str:
    """`send_email` -> `Send email`, and a passthrough for anything else."""
    if value is None:
        return ""
    raw = value.value if hasattr(value, "value") else str(value)
    return raw.replace("_", " ").capitalize()


def fmt_date(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    if isinstance(value, date):
        return value.strftime("%b %d, %Y")
    return str(value)


def fmt_datetime(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y · %H:%M")
    return fmt_date(value)


def date_input(value: Any) -> str:
    """Format for an <input type="date"> / <input type="datetime-local"> value."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def join_lines(value: Any) -> str:
    """ARRAY(String) column -> textarea contents, one entry per line."""
    if not value:
        return ""
    return "\n".join(str(v) for v in value)


def truncate(value: Any, length: int = 90) -> str:
    if not value:
        return "—"
    text = str(value).replace("\n", " ").strip()
    return text if len(text) <= length else text[: length - 1] + "…"


def query_with(params: dict[str, Any], **overrides: Any) -> str:
    """Rebuild the current query string with some keys replaced — for paging links."""
    merged = {k: v for k, v in {**params, **overrides}.items() if v not in (None, "")}
    return "?" + urlencode(merged) if merged else ""


templates.env.filters.update(
    {
        "label": label,
        "fmt_date": fmt_date,
        "fmt_datetime": fmt_datetime,
        "date_input": date_input,
        "join_lines": join_lines,
        "truncate": truncate,
    }
)
templates.env.globals.update({"enums": ENUMS, "query_with": query_with})


def render(
    request: Request,
    template: str,
    context: dict[str, Any] | None = None,
    *,
    partial: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render `template`, or `partial` when HTMX asked for a fragment.

    One route can therefore serve both a full page load and an in-place table
    swap: the filter form targets the table, HTMX sets HX-Request, and only
    the rows come back.
    """
    ctx = dict(context or {})
    ctx["request"] = request
    ctx.setdefault("user", getattr(request.state, "web_user", None))
    # Templates compare due dates against it, so it must be per-request.
    ctx.setdefault("today", date.today())

    chosen = partial if (partial and request.headers.get("HX-Request")) else template
    return templates.TemplateResponse(request, chosen, ctx, status_code=status_code)


def redirect(url: str) -> RedirectResponse:
    """POST-redirect-GET. 303 so the browser re-issues as a GET."""
    return RedirectResponse(url, status_code=303)
