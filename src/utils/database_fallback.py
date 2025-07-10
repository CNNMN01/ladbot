"""
Database with SQLite fallback for Railway issues
"""
import os
import json
import logging
import aiosqlite
from pathlib import Path
from typing import Any, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class SimpleDatabaseManager:
    """Simplified database manager with SQLite fallback"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.use_sqlite = False
        self.db_path = Path("/app/data/settings.db")

    async def initialize(self):
        """Initialize database - try PostgreSQL, fallback to SQLite"""
        try:
            if self.database_url:
                # Try PostgreSQL first
                import asyncpg
                conn = await asyncpg.connect(self.database_url, timeout=5)
                await conn.execute('SELECT 1')
                await conn.close()

                # If we get here, PostgreSQL works
                await self._init_postgres()
                logger.info("✅ PostgreSQL database initialized")
                return True

        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL failed: {e}")

        # Fallback to SQLite
        try:
            await self._init_sqlite()
            logger.info("✅ SQLite fallback initialized")
            return True
        except Exception as e:
            logger.error(f"❌ All database options failed: {e}")
            return False

    async def _init_postgres(self):
        """Initialize PostgreSQL"""
        import asyncpg
        self.pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)

        # Create table
        async with self.pool.acquire() as conn:
            await conn.execute("""
                               CREATE TABLE IF NOT EXISTS guild_settings
                               (
                                   guild_id
                                   BIGINT
                                   PRIMARY
                                   KEY,
                                   settings
                                   JSONB
                                   NOT
                                   NULL
                                   DEFAULT
                                   '{}',
                                   updated_at
                                   TIMESTAMP
                                   DEFAULT
                                   CURRENT_TIMESTAMP
                               )
                               """)

    async def _init_sqlite(self):
        """Initialize SQLite fallback"""
        self.use_sqlite = True
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                             CREATE TABLE IF NOT EXISTS guild_settings
                             (
                                 guild_id
                                 INTEGER
                                 PRIMARY
                                 KEY,
                                 settings
                                 TEXT
                                 NOT
                                 NULL
                                 DEFAULT
                                 '{}',
                                 updated_at
                                 TEXT
                                 DEFAULT
                                 CURRENT_TIMESTAMP
                             )
                             """)
            await db.commit()

    async def get_guild_setting(self, guild_id: int, setting_name: str, default: Any = True) -> Any:
        """Get setting - works with both PostgreSQL and SQLite"""
        try:
            if self.use_sqlite:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT settings FROM guild_settings WHERE guild_id = ?",
                        (guild_id,)
                    )
                    row = await cursor.fetchone()
                    if row:
                        settings = json.loads(row[0])
                        return settings.get(setting_name, default)
            else:
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT settings FROM guild_settings WHERE guild_id = $1",
                        guild_id
                    )
                    if row:
                        settings = dict(row['settings'])
                        return settings.get(setting_name, default)

            return default

        except Exception as e:
            logger.error(f"Error getting setting: {e}")
            return default

    async def set_guild_setting(self, guild_id: int, setting_name: str, value: Any) -> bool:
        """Set setting - works with both PostgreSQL and SQLite"""
        try:
            if self.use_sqlite:
                async with aiosqlite.connect(self.db_path) as db:
                    # Get existing settings
                    cursor = await db.execute(
                        "SELECT settings FROM guild_settings WHERE guild_id = ?",
                        (guild_id,)
                    )
                    row = await cursor.fetchone()

                    if row:
                        settings = json.loads(row[0])
                    else:
                        settings = {}

                    settings[setting_name] = value

                    # Upsert
                    await db.execute("""
                        INSERT OR REPLACE INTO guild_settings (guild_id, settings, updated_at)
                        VALUES (?, ?, ?)
                    """, (guild_id, json.dumps(settings), datetime.now().isoformat()))
                    await db.commit()
            else:
                async with self.pool.acquire() as conn:
                    # Get existing
                    row = await conn.fetchrow(
                        "SELECT settings FROM guild_settings WHERE guild_id = $1",
                        guild_id
                    )

                    if row:
                        settings = dict(row['settings'])
                    else:
                        settings = {}

                    settings[setting_name] = value

                    # Upsert
                    await conn.execute("""
                                       INSERT INTO guild_settings (guild_id, settings, updated_at)
                                       VALUES ($1, $2, CURRENT_TIMESTAMP) ON CONFLICT (guild_id) 
                        DO
                                       UPDATE SET settings = $2, updated_at = CURRENT_TIMESTAMP
                                       """, guild_id, json.dumps(settings))

            logger.info(f"✅ Set {setting_name}={value} for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting {setting_name}: {e}")
            return False

    async def set_all_guild_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """Set all settings for a guild"""
        try:
            settings['last_updated'] = datetime.now().isoformat()

            if self.use_sqlite:
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute("""
                        INSERT OR REPLACE INTO guild_settings (guild_id, settings, updated_at)
                        VALUES (?, ?, ?)
                    """, (guild_id, json.dumps(settings), datetime.now().isoformat()))
                    await db.commit()
            else:
                async with self.pool.acquire() as conn:
                    await conn.execute("""
                                       INSERT INTO guild_settings (guild_id, settings, updated_at)
                                       VALUES ($1, $2, CURRENT_TIMESTAMP) ON CONFLICT (guild_id) 
                        DO
                                       UPDATE SET settings = $2, updated_at = CURRENT_TIMESTAMP
                                       """, guild_id, json.dumps(settings))

            logger.info(f"✅ Set all settings for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error setting all settings: {e}")
            return False

    async def get_all_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get all settings for a guild"""
        try:
            if self.use_sqlite:
                async with aiosqlite.connect(self.db_path) as db:
                    cursor = await db.execute(
                        "SELECT settings FROM guild_settings WHERE guild_id = ?",
                        (guild_id,)
                    )
                    row = await cursor.fetchone()
                    if row:
                        return json.loads(row[0])
            else:
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT settings FROM guild_settings WHERE guild_id = $1",
                        guild_id
                    )
                    if row:
                        return dict(row['settings'])

            return {}

        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            return {}

    async def close(self):
        """Close database connections"""
        if not self.use_sqlite and hasattr(self, 'pool'):
            await self.pool.close()


# Global instance
db_manager = SimpleDatabaseManager()