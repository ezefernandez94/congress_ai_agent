from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import WorkspaceRole
from app.models.workspace import Workspace, WorkspaceMember
from app.repositories.base import BaseRepository

# The workspace that held all data before multi-workspace support (created by migration
# 684fe7d36677). Env-seeded owners land here until EZE-52 makes them platform admins.
DEFAULT_WORKSPACE_NAME = "Default"


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, db: AsyncSession):
        super().__init__(Workspace, db)

    async def get_membership(self, user_id: str) -> WorkspaceMember | None:
        result = await self.db.execute(
            select(WorkspaceMember).where(WorkspaceMember.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_member(
        self, workspace_id: str, user_id: str, role: WorkspaceRole = WorkspaceRole.member
    ) -> WorkspaceMember:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self.db.add(member)
        await self.db.flush()
        return member

    async def get_or_create_default(self) -> Workspace:
        result = await self.db.execute(
            select(Workspace)
            .where(Workspace.name == DEFAULT_WORKSPACE_NAME)
            .order_by(Workspace.created_at)
            .limit(1)
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            workspace = await self.create({"name": DEFAULT_WORKSPACE_NAME})
        return workspace
