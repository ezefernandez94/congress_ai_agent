import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, WorkspaceRole


class Workspace(Base, TimestampMixin):
    """One organization. Every record will belong to exactly one workspace (ADR-013)."""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)


class WorkspaceMember(Base, TimestampMixin):
    """A bot user's membership in a workspace.

    user_id is unique: a user belongs to exactly one workspace (REQ-024), so
    resolving someone's workspace never has to choose between several.
    """

    __tablename__ = "workspace_members"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bot_users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    role: Mapped[WorkspaceRole] = mapped_column(default=WorkspaceRole.member, nullable=False)
