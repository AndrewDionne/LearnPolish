# migrate_points_events.py
import os, sys
from sqlalchemy import create_engine

PG_SQL = """
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename='points_events'
  ) THEN
    CREATE TABLE public.points_events (
      id         BIGSERIAL PRIMARY KEY,
      user_id    INTEGER NOT NULL,
      set_name   TEXT,
      mode       TEXT,
      points     INTEGER NOT NULL DEFAULT 0,
      meta       JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema='public' AND table_name='users') THEN
      ALTER TABLE public.points_events
        ADD CONSTRAINT points_events_user_fk
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
    ELSIF EXISTS (SELECT 1 FROM information_schema.tables
                  WHERE table_schema='public' AND table_name='user') THEN
      ALTER TABLE public.points_events
        ADD CONSTRAINT points_events_user_fk
        FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;
    END IF;

    CREATE INDEX IF NOT EXISTS idx_points_events_user_id     ON public.points_events(user_id);
    CREATE INDEX IF NOT EXISTS idx_points_events_created_at  ON public.points_events(created_at);
  END IF;
END$$;
"""

# For SQLite we must execute each statement separately
SQLITE_STATEMENTS = [
    "PRAGMA foreign_keys = ON",
    """
    CREATE TABLE IF NOT EXISTS points_events (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id    INTEGER NOT NULL,
      set_name   TEXT,
      mode       TEXT,
      points     INTEGER NOT NULL DEFAULT 0,
      meta       TEXT,  -- JSON stored as TEXT in SQLite
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_points_events_user_id    ON points_events(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_points_events_created_at ON points_events(created_at)",
]

url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI")
if not url:
    print("Set DATABASE_URL (or SQLALCHEMY_DATABASE_URI).", file=sys.stderr)
    sys.exit(1)

engine = create_engine(url, future=True)

with engine.begin() as conn:
    if url.startswith("postgres"):
        # Single DO $$...$$ block is fine as one statement
        conn.exec_driver_sql(PG_SQL)
    else:
        # SQLite: run each DDL statement separately
        for stmt in SQLITE_STATEMENTS:
            conn.exec_driver_sql(stmt)

print("points_events migration: OK")
