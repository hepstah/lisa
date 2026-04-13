import aiosqlite
from lisa.config import settings


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.db_path)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA busy_timeout=5000")
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS command_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                source TEXT NOT NULL,
                raw_input TEXT,
                device_id TEXT,
                action TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                error_stage TEXT,
                duration_ms INTEGER,
                llm_debug TEXT
            );

            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                alias TEXT NOT NULL,
                device_type TEXT,
                host TEXT,
                added_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                last_seen TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
        """)
        await db.commit()

        # Idempotent migration for existing dev DBs that were created before
        # the llm_debug column existed. Swallows OperationalError when the
        # column is already present. Single-home SQLite DB; acceptable per spec.
        try:
            await db.execute("ALTER TABLE command_log ADD COLUMN llm_debug TEXT")
            await db.commit()
        except aiosqlite.OperationalError:
            pass  # column already exists
    finally:
        await db.close()
