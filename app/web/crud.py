"""Generates the seven standard CRUD routes for an entity.

Every section of the UI — people, companies, tasks, opportunities,
interactions, meetings, notes, conferences — needs the same list / new /
create / detail / edit / update / delete pair of routes over a different
model. The differences are all configuration (which columns to filter on,
which relationships to eager-load, which templates to render), so they live
in a CrudConfig and the route bodies are written once here.
"""

import csv
import io
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Sequence
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement
from starlette.datastructures import FormData, QueryParams

from app.core.database import get_db
from app.models.base import Base
from app.repositories.base import BaseRepository, ilike_any
from app.web.auth import require_web_user
from app.web.query import Page, active_filters, equality_filters, parse_form, parse_page
from app.web.rendering import redirect, render

RepoFactory = Callable[[AsyncSession], BaseRepository]


@dataclass
class CrudConfig:
    slug: str                       # url segment + template directory, e.g. "people"
    title: str                      # plural heading, e.g. "People"
    singular: str                   # e.g. "Person"
    model: type[Base]
    repo: RepoFactory
    create_schema: type[BaseModel]
    update_schema: type[BaseModel]

    # Which form inputs are read, and how each is decoded.
    form_fields: Sequence[str] = ()
    form_arrays: Sequence[str] = ()
    form_booleans: Sequence[str] = ()
    form_multi: Sequence[str] = ()

    # Filtering: query key -> column for exact matches, plus free-text columns.
    filter_columns: dict[str, Any] = field(default_factory=dict)
    search_columns: Sequence[Any] = ()

    order_by: Sequence[Any] = ()
    list_options: Sequence[Any] = ()      # selectinload for the list template
    detail_options: Sequence[Any] = ()    # selectinload for the detail template

    # Filters that are not a plain column equality (date ranges, "overdue only").
    extra_where: Callable[[QueryParams], list[ColumnElement[bool]]] | None = None
    # Dropdown data the form template needs (companies, people, ...).
    form_context: Callable[[AsyncSession], Awaitable[dict[str, Any]]] | None = None
    # Related records the detail template renders.
    detail_context: Callable[[AsyncSession, Any], Awaitable[dict[str, Any]]] | None = None
    # Post-save hook for anything the schema cannot express, e.g. an M2M.
    on_save: Callable[[AsyncSession, Any, FormData], Awaitable[None]] | None = None

    # Schema fields that are not model columns (e.g. Meeting.participant_ids,
    # which the on_save hook writes to the association table instead).
    dump_exclude: Sequence[str] = ()
    # Edit-form values that are not a plain attribute read, e.g. turning
    # Meeting.participants into the list of ids the multi-select expects.
    value_overrides: dict[str, Callable[[Any], Any]] = field(default_factory=dict)

    has_detail: bool = True
    # Extra sentence shown in the delete confirmation dialog.
    delete_warning: str = ""
    # Overrides for the values a blank create form starts with.
    form_defaults: dict[str, Any] = field(default_factory=dict)

    @property
    def all_form_fields(self) -> list[str]:
        return [
            *self.form_fields,
            *self.form_arrays,
            *self.form_booleans,
            *self.form_multi,
        ]

    @property
    def filter_keys(self) -> list[str]:
        keys = list(self.filter_columns)
        if self.search_columns:
            keys.append("q")
        return keys


def csv_columns(model: type[Base]) -> list[str]:
    """Every real column except the vector embeddings, which are not exportable."""
    return [c.name for c in model.__table__.columns if c.name != "embedding"]


def _read_form(config: CrudConfig, form: FormData) -> dict[str, Any]:
    return parse_form(
        form,
        fields=config.form_fields,
        arrays=config.form_arrays,
        booleans=config.form_booleans,
        multi=config.form_multi,
    )


def _blank_values(config: CrudConfig) -> dict[str, Any]:
    """Starting values for a create form, taken from the schema's defaults.

    Without this a required <select> has nothing marked selected and the
    browser silently picks the first option — which would file every new
    contact as an A-tier hot investor instead of the model's
    other/unranked/unknown defaults.
    """
    values: dict[str, Any] = {}
    for name, info in config.create_schema.model_fields.items():
        if name not in config.all_form_fields:
            continue
        if info.default is not PydanticUndefined:
            values[name] = info.default
        elif info.default_factory is not None:
            values[name] = info.default_factory()

    values.update(config.form_defaults)
    return values


def _values_from(obj: Any, config: CrudConfig) -> dict[str, Any]:
    """Current values for the edit form, keyed exactly as the inputs are named."""
    values = {name: getattr(obj, name, None) for name in config.all_form_fields}
    for name, resolve in config.value_overrides.items():
        values[name] = resolve(obj)
    return values


def _error_message(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:4]:
        location = ".".join(str(p) for p in err["loc"]) or "form"
        parts.append(f"{location}: {err['msg']}")
    return "; ".join(parts)


def _build_where(config: CrudConfig, params: QueryParams) -> list[ColumnElement[bool]]:
    values = active_filters(params, config.filter_columns.keys())
    where = equality_filters(values, config.filter_columns)

    term = (params.get("q") or "").strip()
    if term and config.search_columns:
        where.append(ilike_any(term, *config.search_columns))

    if config.extra_where:
        where.extend(config.extra_where(params))

    return where


def build_router(config: CrudConfig) -> APIRouter:
    router = APIRouter(
        prefix=f"/{config.slug}",
        tags=[config.slug],
        dependencies=[Depends(require_web_user)],
    )
    tpl = config.slug

    async def _list_page(request: Request, db: AsyncSession) -> tuple[list[Any], Page, dict]:
        params = request.query_params
        page = parse_page(params)
        where = _build_where(config, params)

        rows, total = await config.repo(db).list_page(
            where=where,
            order_by=config.order_by,
            options=config.list_options,
            skip=page.skip,
            limit=page.per_page,
        )
        page.total = total
        return rows, page, active_filters(params, config.filter_keys)

    @router.get("")
    async def index(request: Request, db: AsyncSession = Depends(get_db)):
        rows, page, filters = await _list_page(request, db)
        ctx = {"rows": rows, "page": page, "filters": filters, "config": config}
        if config.form_context:
            ctx.update(await config.form_context(db))
        # HTMX filter submissions swap only the table body.
        return render(request, f"{tpl}/list.html", ctx, partial=f"{tpl}/_rows.html")

    # Registered before /{id} so "export.csv" is never read as an id.
    @router.get("/export.csv")
    async def export(request: Request, db: AsyncSession = Depends(get_db)):
        """Export the current filter selection, not just the current page."""
        where = _build_where(config, request.query_params)
        rows, _ = await config.repo(db).list_page(
            where=where, order_by=config.order_by, skip=0, limit=10_000
        )
        columns = csv_columns(config.model)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(
                [
                    ("" if (v := getattr(row, c, None)) is None else str(v))
                    for c in columns
                ]
            )
        buffer.seek(0)

        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{config.slug}.csv"'},
        )

    @router.get("/new")
    async def new(request: Request, db: AsyncSession = Depends(get_db)):
        ctx: dict[str, Any] = {"obj": None, "values": _blank_values(config), "config": config}
        if config.form_context:
            ctx.update(await config.form_context(db))
        return render(request, f"{tpl}/form.html", ctx)

    @router.post("")
    async def create(request: Request, db: AsyncSession = Depends(get_db)):
        form = await request.form()
        payload = _read_form(config, form)

        try:
            validated = config.create_schema(**payload)
        except ValidationError as exc:
            ctx: dict[str, Any] = {
                "obj": None,
                "values": payload,
                "error": _error_message(exc),
                "config": config,
            }
            if config.form_context:
                ctx.update(await config.form_context(db))
            return render(request, f"{tpl}/form.html", ctx, status_code=422)

        repo = config.repo(db)
        obj = await repo.create(
            validated.model_dump(exclude=set(config.dump_exclude) or None)
        )
        if config.on_save:
            await config.on_save(db, obj, form)

        target = f"/{config.slug}/{obj.id}" if config.has_detail else f"/{config.slug}"
        return redirect(f"{target}?ok={quote(config.singular + ' created')}")

    if config.has_detail:

        @router.get("/{obj_id}")
        async def detail(obj_id: str, request: Request, db: AsyncSession = Depends(get_db)):
            obj = await config.repo(db).get_with(obj_id, *config.detail_options)
            if obj is None:
                return redirect(f"/{config.slug}?error={quote(config.singular + ' not found')}")

            ctx: dict[str, Any] = {"obj": obj, "config": config}
            if config.detail_context:
                ctx.update(await config.detail_context(db, obj))
            return render(request, f"{tpl}/detail.html", ctx)

    @router.get("/{obj_id}/edit")
    async def edit(obj_id: str, request: Request, db: AsyncSession = Depends(get_db)):
        obj = await config.repo(db).get_with(obj_id, *config.detail_options)
        if obj is None:
            return redirect(f"/{config.slug}?error={quote(config.singular + ' not found')}")

        ctx: dict[str, Any] = {
            "obj": obj,
            "values": _values_from(obj, config),
            "config": config,
        }
        if config.form_context:
            ctx.update(await config.form_context(db))
        return render(request, f"{tpl}/form.html", ctx)

    @router.post("/{obj_id}")
    async def update(obj_id: str, request: Request, db: AsyncSession = Depends(get_db)):
        repo = config.repo(db)
        obj = await repo.get_with(obj_id, *config.detail_options)
        if obj is None:
            return redirect(f"/{config.slug}?error={quote(config.singular + ' not found')}")

        form = await request.form()
        payload = _read_form(config, form)

        try:
            validated = config.update_schema(**payload)
        except ValidationError as exc:
            ctx: dict[str, Any] = {
                "obj": obj,
                "values": payload,
                "error": _error_message(exc),
                "config": config,
            }
            if config.form_context:
                ctx.update(await config.form_context(db))
            return render(request, f"{tpl}/form.html", ctx, status_code=422)

        # exclude_unset keeps this to the fields the form actually submitted,
        # while set_fields (unlike repo.update) still writes the ones the user
        # deliberately cleared.
        await repo.set_fields(
            obj,
            validated.model_dump(
                exclude_unset=True, exclude=set(config.dump_exclude) or None
            ),
        )
        if config.on_save:
            await config.on_save(db, obj, form)

        target = f"/{config.slug}/{obj.id}" if config.has_detail else f"/{config.slug}"
        return redirect(f"{target}?ok={quote('Saved')}")

    @router.post("/{obj_id}/delete")
    async def destroy(obj_id: str, db: AsyncSession = Depends(get_db)):
        try:
            deleted = await config.repo(db).delete(obj_id)
        except IntegrityError:
            # Something still references this row and the FK has no cascade —
            # tell the user rather than returning a 500.
            await db.rollback()
            return redirect(
                f"/{config.slug}?error="
                + quote(
                    f"{config.singular} is still referenced by other records. "
                    "Detach or delete those first."
                )
            )

        message = "deleted" if deleted else "not found"
        return redirect(f"/{config.slug}?ok={quote(config.singular + ' ' + message)}")

    return router
