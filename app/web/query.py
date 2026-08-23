"""Query-string parsing (filters, sorting, paging) and form-body normalisation."""

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from sqlalchemy.sql.elements import ColumnElement
from starlette.datastructures import FormData, QueryParams

DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 200


@dataclass
class Page:
    """Pagination state, shared by every list route and the paging partial."""

    number: int
    per_page: int
    total: int = 0

    @property
    def skip(self) -> int:
        return (self.number - 1) * self.per_page

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.per_page))  # ceil division

    @property
    def has_prev(self) -> bool:
        return self.number > 1

    @property
    def has_next(self) -> bool:
        return self.number < self.pages

    @property
    def first_index(self) -> int:
        return 0 if self.total == 0 else self.skip + 1

    @property
    def last_index(self) -> int:
        return min(self.skip + self.per_page, self.total)


def parse_page(params: QueryParams) -> Page:
    try:
        number = max(1, int(params.get("page", 1)))
    except ValueError:
        number = 1
    try:
        per_page = min(MAX_PER_PAGE, max(1, int(params.get("per_page", DEFAULT_PER_PAGE))))
    except ValueError:
        per_page = DEFAULT_PER_PAGE
    return Page(number=number, per_page=per_page)


def active_filters(params: QueryParams, keys: Iterable[str]) -> dict[str, str]:
    """The filter values actually set, for re-populating the form and paging links."""
    out: dict[str, str] = {}
    for key in keys:
        value = (params.get(key) or "").strip()
        if value:
            out[key] = value
    return out


def equality_filters(
    values: dict[str, str],
    column_map: dict[str, Any],
) -> list[ColumnElement[bool]]:
    """`?contact_type=investor` -> `Person.contact_type == 'investor'`.

    Only keys present in column_map are honoured, so an unknown query
    parameter can never reach the query builder.
    """
    return [column_map[key] == value for key, value in values.items() if key in column_map]


# --- form bodies -----------------------------------------------------------
#
# HTML forms only ever send strings, and an untouched input sends "". Pydantic
# coerces the types from there, but "" has to become None first or every
# optional column would be written as an empty string instead of NULL.


def parse_form(
    form: FormData,
    *,
    fields: Sequence[str],
    arrays: Sequence[str] = (),
    booleans: Sequence[str] = (),
    multi: Sequence[str] = (),
) -> dict[str, Any]:
    """Normalise a submitted form into a dict ready for a Pydantic schema.

    - `booleans` are checkboxes: absent means False, not "unset".
    - `arrays` are textareas backing ARRAY(String) columns, one item per line.
    - `multi` are multi-selects, returned as a list of the selected values.
    - everything else: "" collapses to None so the column is nulled.

    Only keys in `fields` (plus arrays/booleans/multi) are read, so a crafted
    form cannot set a column the page never meant to expose.
    """
    data: dict[str, Any] = {}

    for name in booleans:
        data[name] = form.get(name) is not None

    for name in arrays:
        raw = (form.get(name) or "").strip()
        data[name] = [line.strip() for line in raw.splitlines() if line.strip()] or None

    for name in multi:
        data[name] = [v for v in form.getlist(name) if v]

    for name in fields:
        if name in data:
            continue
        if name not in form:
            continue
        value = form.get(name)
        value = value.strip() if isinstance(value, str) else value
        data[name] = value or None

    return data
