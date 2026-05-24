"""Tiny dev-only schema migrator for SQLite.

`SQLModel.metadata.create_all()` won't add new columns to a table that already
exists, so when we evolve `db_models.py` the dev DB silently goes out of sync.
This script inspects the live SQLite schema and `ALTER TABLE ... ADD COLUMN`s
anything missing.

Idempotent: run it any time after editing db_models.py.

  python -m scripts.dev_migrate
"""

import sqlite3

from config import settings

# Columns we expect on each table beyond what `create_all` originally laid down.
# All are nullable JSON/TEXT additions — safe to backfill with NULL.
EXPECTED = {
    "story": {
        "initial_state": "TEXT",       # JSON
        "character_sprites": "TEXT",   # JSON
        "backgrounds": "TEXT",         # JSON
    },
    "scene": {
        "state": "TEXT",         # JSON
        "state_changes": "TEXT", # JSON
        "pacing": "TEXT",
        "stage": "TEXT",         # JSON
    },
    "choice": {
        "is_wrong": "BOOLEAN DEFAULT 0 NOT NULL",
        "is_pre_final": "BOOLEAN DEFAULT 0 NOT NULL",
    },
}


def _current_columns(con: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})")}


def migrate(db_path: str = None) -> None:
    db_path = db_path or settings.db_name
    con = sqlite3.connect(db_path)
    try:
        for table, columns in EXPECTED.items():
            present = _current_columns(con, table)
            if not present:
                # Table doesn't exist yet — let create_all handle it.
                print(f"[skip] {table}: table not present")
                continue
            for col, ddl in columns.items():
                if col in present:
                    continue
                sql = f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"
                print(f"[add ] {table}.{col} :: {ddl}")
                con.execute(sql)
        con.commit()
    finally:
        con.close()
    print("dev migrate: done")


if __name__ == "__main__":
    migrate()
