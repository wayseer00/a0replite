"""pcea_shares table for vault sentinel tracking

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS pcea_shares (
        share_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id      UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
        sentinel_id     TEXT NOT NULL,
        gist_id         TEXT NOT NULL,
        epoch           INTEGER NOT NULL,
        key_id          TEXT NOT NULL,
        index_in_scheme INTEGER NOT NULL,
        commitment      TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (session_id, sentinel_id, epoch, key_id)
    )
    """)

    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_pcea_shares_session
    ON pcea_shares(session_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pcea_shares")
