"""Workspace scoping on the database session (ADR-018).

A session opened for a caller carries their workspace and user in `session.info`. Two hooks then make
every ORM statement and every insert respect it, so repositories, services and web routes never filter
by workspace themselves:

- `do_orm_execute` adds `workspace_id = <session's>` to every SELECT, UPDATE and DELETE on a
  WorkspaceScoped model, relationship loads included. On a session with no workspace, a statement that
  touches a scoped table raises instead of reading every organization's rows.
- `before_flush` stamps `workspace_id` and `created_by_user_id` on new rows, and refuses a row that
  belongs to, or is moved to, another workspace.

Not covered: `text()` SQL and Core statements on bare Table objects. Domain tables are read only
through the ORM models; Postgres RLS (ADR-013, EZE-51) is the backstop for anything that slips past.
"""

from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlalchemy.sql.util import find_tables

from app.models.base import Base, WorkspaceScoped

WORKSPACE_KEY = "workspace_id"
USER_KEY = "user_id"


class UnscopedQueryError(RuntimeError):
    """A workspace-scoped table was used on a session that has no workspace."""


class CrossWorkspaceWriteError(RuntimeError):
    """A write would put a row into a workspace other than the session's."""


def scope_session(
    session: AsyncSession | Session, workspace_id: str, user_id: str | None = None
) -> None:
    """Bind a session to one workspace, and to the user whose writes it records (REQ-027)."""
    session.info[WORKSPACE_KEY] = workspace_id
    session.info[USER_KEY] = user_id


def session_workspace(session: AsyncSession | Session) -> str | None:
    return session.info.get(WORKSPACE_KEY)


_scoped_tables: frozenset[Any] | None = None


def _scoped_table_set() -> frozenset[Any]:
    # Built lazily: every model module has to be imported before the registry is complete.
    global _scoped_tables
    if _scoped_tables is None:
        _scoped_tables = frozenset(
            mapper.local_table
            for mapper in Base.registry.mappers
            if issubclass(mapper.class_, WorkspaceScoped)
        )
    return _scoped_tables


def _touches_scoped_table(statement: Any) -> bool:
    tables = find_tables(
        statement,
        check_columns=True,
        include_aliases=True,
        include_joins=True,
        include_selects=True,
        include_crud=True,
    )
    scoped = _scoped_table_set()
    return any(getattr(t, "element", t) in scoped for t in tables)


@event.listens_for(Session, "do_orm_execute")
def _scope_statement(state: ORMExecuteState) -> None:
    if not (state.is_select or state.is_update or state.is_delete):
        return

    workspace_id = state.session.info.get(WORKSPACE_KEY)
    if workspace_id is None:
        if _touches_scoped_table(state.statement):
            raise UnscopedQueryError(
                "Query on a workspace-scoped table from a session with no workspace; "
                "open it with scope_session() first."
            )
        return

    # Added to every statement, not only the ones that name a scoped model at the top level: the
    # criteria also reach joins, subqueries, aggregates and relationship loads, and it is a no-op
    # for statements that touch no scoped table.
    state.statement = state.statement.options(
        with_loader_criteria(
            WorkspaceScoped,
            lambda cls: cls.workspace_id == workspace_id,
            include_aliases=True,
        )
    )


@event.listens_for(Session, "before_flush")
def _stamp_and_guard(session: Session, flush_context: Any, instances: Any) -> None:
    workspace_id = session.info.get(WORKSPACE_KEY)
    user_id = session.info.get(USER_KEY)

    for obj in session.new:
        if not isinstance(obj, WorkspaceScoped):
            continue
        if workspace_id is None:
            raise UnscopedQueryError(
                f"Insert into {type(obj).__tablename__} from a session with no workspace."
            )
        if obj.workspace_id is None:
            obj.workspace_id = workspace_id
        elif obj.workspace_id != workspace_id:
            raise CrossWorkspaceWriteError(
                f"Insert into {type(obj).__tablename__} for another workspace."
            )
        if obj.created_by_user_id is None and user_id is not None:
            obj.created_by_user_id = user_id

    for obj in session.dirty:
        if not isinstance(obj, WorkspaceScoped):
            continue
        history = inspect(obj).attrs.workspace_id.history
        if history.has_changes():
            raise CrossWorkspaceWriteError(
                f"Moving a {type(obj).__tablename__} row to another workspace is not allowed."
            )
