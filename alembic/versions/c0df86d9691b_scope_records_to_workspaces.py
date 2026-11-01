"""scope records to workspaces

Revision ID: c0df86d9691b
Revises: 684fe7d36677
Create Date: 2026-11-01 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c0df86d9691b'
down_revision: str | None = '684fe7d36677'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every table that holds an organization's data (ADR-013, REQ-024).
SCOPED_TABLES = (
    'people',
    'companies',
    'interactions',
    'meetings',
    'notes',
    'tasks',
    'opportunities',
    'conferences',
    'conversation_messages',
)


def upgrade() -> None:
    for table in SCOPED_TABLES:
        op.add_column(table, sa.Column('workspace_id', sa.UUID(as_uuid=False), nullable=True))
        op.add_column(table, sa.Column('created_by_user_id', sa.UUID(as_uuid=False), nullable=True))

    # Existing rows belong to the one organization that used the product before workspaces: the
    # "Default" workspace from 684fe7d36677. A database with records but no users never got one, so
    # create it here when any scoped table has rows. Creators are unknown, so they stay NULL (REQ-027).
    has_rows = ' OR '.join(f'EXISTS (SELECT 1 FROM {t})' for t in SCOPED_TABLES)
    op.execute(
        "INSERT INTO workspaces (id, name) SELECT gen_random_uuid(), 'Default' "
        f"WHERE NOT EXISTS (SELECT 1 FROM workspaces WHERE name = 'Default') AND ({has_rows})"
    )
    for table in SCOPED_TABLES:
        op.execute(
            f"UPDATE {table} SET workspace_id = "
            "(SELECT id FROM workspaces WHERE name = 'Default' ORDER BY created_at LIMIT 1)"
        )

    for table in SCOPED_TABLES:
        op.alter_column(table, 'workspace_id', nullable=False)
        op.create_index(op.f(f'ix_{table}_workspace_id'), table, ['workspace_id'], unique=False)
        op.create_foreign_key(
            op.f(f'{table}_workspace_id_fkey'), table, 'workspaces',
            ['workspace_id'], ['id'], ondelete='RESTRICT',
        )
        op.create_foreign_key(
            op.f(f'{table}_created_by_user_id_fkey'), table, 'bot_users',
            ['created_by_user_id'], ['id'], ondelete='SET NULL',
        )

    # The same LinkedIn profile can be a contact in two organizations.
    op.drop_constraint('people_linkedin_url_key', 'people', type_='unique')
    op.create_unique_constraint(
        'uq_people_workspace_linkedin_url', 'people', ['workspace_id', 'linkedin_url']
    )


def downgrade() -> None:
    # Fails if two workspaces hold the same LinkedIn URL, which is the point: going back to a global
    # unique constraint would silently merge two organizations' contacts.
    op.drop_constraint('uq_people_workspace_linkedin_url', 'people', type_='unique')
    op.create_unique_constraint('people_linkedin_url_key', 'people', ['linkedin_url'])

    for table in SCOPED_TABLES:
        op.drop_constraint(op.f(f'{table}_created_by_user_id_fkey'), table, type_='foreignkey')
        op.drop_constraint(op.f(f'{table}_workspace_id_fkey'), table, type_='foreignkey')
        op.drop_index(op.f(f'ix_{table}_workspace_id'), table_name=table)
        op.drop_column(table, 'created_by_user_id')
        op.drop_column(table, 'workspace_id')
