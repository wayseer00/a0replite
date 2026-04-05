"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-04-05

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS "pgcrypto"
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_sessions (
        session_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         TEXT NOT NULL,
        tier            TEXT NOT NULL DEFAULT 'seeker',
        ptca_snapshot   JSONB,
        pcea_sealed_blob BYTEA,
        pcea_wrapped_key BYTEA,
        pcea_epoch      INTEGER NOT NULL DEFAULT 0,
        pcea_key_id     TEXT,
        pcea_gist_id_1  TEXT,
        pcea_gist_id_2  TEXT,
        pcea_nonce      TEXT,
        pcea_aad        TEXT,
        pcea_commitment TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_active_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        expires_at      TIMESTAMPTZ
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        message_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id      UUID NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
        role            TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
        content         TEXT NOT NULL,
        turn_id         TEXT,
        round_id        TEXT,
        edcm_snapshot   JSONB,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS payment_records (
        payment_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id             TEXT NOT NULL,
        tier                TEXT NOT NULL,
        stripe_session_id   TEXT,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payment_records_user ON payment_records(user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS payment_records CASCADE")
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE")
    op.execute("DROP TABLE IF EXISTS chat_sessions CASCADE")
