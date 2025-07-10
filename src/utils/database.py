"""
Enhanced Database Manager for Ladbot Settings Storage
Supports PostgreSQL with SQLite fallback, singleton pattern, and comprehensive error handling
"""

import os
import logging
import asyncio
import json
import aiosqlite
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime
import asyncpg

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Singleton Database Manager for Ladbot
    Handles PostgreSQL with SQLite fallback for settings storage
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.database_url = os.getenv('DATABASE_URL')
        self.pool = None
        self.use_sqlite = False
        self.connection_healthy = False

        # SQLite fallback path - production safe
        if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RENDER'):
            self.sqlite_path = Path("/app/data/ladbot.db")
        else:
            self.sqlite_path = Path("data/ladbot.db")

        # Ensure data directory exists
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialized = True
        logger.info(
            f"🗄️ Database manager initialized - PostgreSQL URL: {'Present' if self.database_url else 'Missing'}")

    async def initialize(self) -> bool:
        """
        Initialize database connection with retry logic and fallback
        Returns True if successful, False otherwise
        """
        if self.connection_healthy:
            return True

        # Try PostgreSQL first if URL is available
        if self.database_url:
            postgres_success = await self._init_postgresql()
            if postgres_success:
                logger.info("✅ PostgreSQL database initialized successfully")
                return True
            else:
                logger.warning("⚠️ PostgreSQL failed, falling back to SQLite")
        else:
            logger.info("ℹ️ No DATABASE_URL found, using SQLite")

        # Fallback to SQLite
        sqlite_success = await self._init_sqlite()
        if sqlite_success:
            logger.info("✅ SQLite database initialized successfully")
            return True
        else:
            logger.error("❌ All database initialization methods failed")
            return False

    async def _init_postgresql(self) -> bool:
        """Initialize PostgreSQL connection with retry logic"""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 PostgreSQL connection attempt {attempt + 1}/{max_retries}")

                # Test connection first
                test_conn = await asyncpg.connect(
                    self.database_url,
                    timeout=10,
                    server_settings={
                        'application_name': 'ladbot',
                        'jit': 'off'
                    }
                )
                await test_conn.execute('SELECT 1')
                await test_conn.close()

                # Create connection pool
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=1,
                    max_size=5,
                    timeout=30,
                    command_timeout=30,
                    server_settings={
                        'application_name': 'ladbot',
                        'jit': 'off'
                    }
                )

                # Create tables
                await self._create_postgresql_tables()

                self.use_sqlite = False
                self.connection_healthy = True
                logger.info("✅ PostgreSQL pool created successfully")
                return True

            except Exception as e:
                logger.error(f"❌ PostgreSQL attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))

        return False

    async def _init_sqlite(self) -> bool:
        """Initialize SQLite fallback"""
        try:
            self.use_sqlite = True

            # Test SQLite connection
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute('SELECT 1')

            # Create tables
            await self._create_sqlite_tables()

            self.connection_healthy = True
            logger.info(f"✅ SQLite initialized at {self.sqlite_path}")
            return True

        except Exception as e:
            logger.error(f"❌ SQLite initialization failed: {e}")
            return False

    async def _create_postgresql_tables(self):
        """Create PostgreSQL tables"""
        create_sql = """
                     CREATE TABLE IF NOT EXISTS guild_settings \
                     ( \
                         guild_id \
                         BIGINT \
                         PRIMARY \
                         KEY, \
                         settings \
                         JSONB \
                         NOT \
                         NULL \
                         DEFAULT \
                         '{}', \
                         created_at \
                         TIMESTAMP \
                         DEFAULT \
                         CURRENT_TIMESTAMP, \
                         updated_at \
                         TIMESTAMP \
                         DEFAULT \
                         CURRENT_TIMESTAMP
                     );

                     CREATE INDEX IF NOT EXISTS idx_guild_settings_updated
                         ON guild_settings(updated_at);

                     CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id
                         ON guild_settings(guild_id);

                     -- Trigger to update updated_at automatically
                     CREATE \
                     OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
                     BEGIN
            NEW.updated_at \
                     = CURRENT_TIMESTAMP;
                     RETURN NEW;
                     END;
        $$ \
                     language 'plpgsql';

                     DROP TRIGGER IF EXISTS update_guild_settings_updated_at ON guild_settings;
                     CREATE TRIGGER update_guild_settings_updated_at
                         BEFORE UPDATE \
                         ON guild_settings
                         FOR EACH ROW
                         EXECUTE FUNCTION update_updated_at_column(); \
                     """

        async with self.pool.acquire() as conn:
            await conn.execute(create_sql)
            logger.info("📊 PostgreSQL tables created/verified")

    async def _create_sqlite_tables(self):
        """Create SQLite tables"""
        create_sql = """
                     CREATE TABLE IF NOT EXISTS guild_settings \
                     ( \
                         guild_id \
                         INTEGER \
                         PRIMARY \
                         KEY, \
                         settings \
                         TEXT \
                         NOT \
                         NULL \
                         DEFAULT \
                         '{}', \
                         created_at \
                         TEXT \
                         DEFAULT \
                         CURRENT_TIMESTAMP, \
                         updated_at \
                         TEXT \
                         DEFAULT \
                         CURRENT_TIMESTAMP
                     );

                     CREATE INDEX IF NOT EXISTS idx_guild_settings_updated
                         ON guild_settings(updated_at);

                     CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id
                         ON guild_settings(guild_id); \
                     """

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.executescript(create_sql)
            await db.commit()
            logger.info("📊 SQLite tables created/verified")

    async def get_guild_setting(self, guild_id: int, setting_name: str, default: Any = True) -> Any:
        """
        Get a specific guild setting from database

        Args:
            guild_id: Discord guild ID
            setting_name: Name of the setting
            default: Default value if setting not found

        Returns:
            Setting value or default
        """
        if not self.connection_healthy:
            logger.warning(f"Database not healthy, returning default for {setting_name}")
            return default

        try:
            if self.use_sqlite:
                return await self._get_setting_sqlite(guild_id, setting_name, default)
            else:
                return await self._get_setting_postgresql(guild_id, setting_name, default)

        except Exception as e:
            logger.error(f"❌ Error getting setting {setting_name} for guild {guild_id}: {e}")
            return default

    async def _get_setting_postgresql(self, guild_id: int, setting_name: str, default: Any) -> Any:
        """Get setting from PostgreSQL"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT settings FROM guild_settings WHERE guild_id = $1",
                guild_id
            )

            if row and row['settings']:
                settings = dict(row['settings'])
                value = settings.get(setting_name, default)
                logger.debug(f"🔍 PostgreSQL: Guild {guild_id} setting {setting_name} = {value}")
                return value
            else:
                logger.debug(f"🔍 PostgreSQL: No settings for guild {guild_id}, returning default {default}")
                return default

    async def _get_setting_sqlite(self, guild_id: int, setting_name: str, default: Any) -> Any:
        """Get setting from SQLite"""
        async with aiosqlite.connect(self.sqlite_path) as db:
            cursor = await db.execute(
                "SELECT settings FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

            if row and row[0]:
                settings = json.loads(row[0])
                value = settings.get(setting_name, default)
                logger.debug(f"🔍 SQLite: Guild {guild_id} setting {setting_name} = {value}")
                return value
            else:
                logger.debug(f"🔍 SQLite: No settings for guild {guild_id}, returning default {default}")
                return default

    async def set_guild_setting(self, guild_id: int, setting_name: str, value: Any) -> bool:
        """
        Set a specific guild setting in database

        Args:
            guild_id: Discord guild ID
            setting_name: Name of the setting
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        if not self.connection_healthy:
            logger.warning(f"Database not healthy, cannot set {setting_name}")
            return False

        try:
            if self.use_sqlite:
                return await self._set_setting_sqlite(guild_id, setting_name, value)
            else:
                return await self._set_setting_postgresql(guild_id, setting_name, value)

        except Exception as e:
            logger.error(f"❌ Error setting {setting_name} for guild {guild_id}: {e}")
            return False

    async def _set_setting_postgresql(self, guild_id: int, setting_name: str, value: Any) -> bool:
        """Set setting in PostgreSQL"""
        async with self.pool.acquire() as conn:
            # Get existing settings
            row = await conn.fetchrow(
                "SELECT settings FROM guild_settings WHERE guild_id = $1",
                guild_id
            )

            if row and row['settings']:
                settings = dict(row['settings'])
            else:
                settings = {}

            # Update the specific setting
            settings[setting_name] = value
            settings['last_updated'] = datetime.now().isoformat()
            settings['last_updated_by'] = 'database_manager'

            # Upsert the settings
            await conn.execute("""
                               INSERT INTO guild_settings (guild_id, settings, updated_at)
                               VALUES ($1, $2, CURRENT_TIMESTAMP) ON CONFLICT (guild_id) 
                DO
                               UPDATE SET
                                   settings = $2,
                                   updated_at = CURRENT_TIMESTAMP
                               """, guild_id, json.dumps(settings))

            logger.info(f"✅ PostgreSQL: Set guild {guild_id} setting {setting_name} = {value}")
            return True

    async def _set_setting_sqlite(self, guild_id: int, setting_name: str, value: Any) -> bool:
        """Set setting in SQLite"""
        async with aiosqlite.connect(self.sqlite_path) as db:
            # Get existing settings
            cursor = await db.execute(
                "SELECT settings FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

            if row and row[0]:
                settings = json.loads(row[0])
            else:
                settings = {}

            # Update the specific setting
            settings[setting_name] = value
            settings['last_updated'] = datetime.now().isoformat()
            settings['last_updated_by'] = 'database_manager'

            # Upsert the settings
            await db.execute("""
                INSERT OR REPLACE INTO guild_settings (guild_id, settings, updated_at)
                VALUES (?, ?, ?)
            """, (guild_id, json.dumps(settings), datetime.now().isoformat()))

            await db.commit()

            logger.info(f"✅ SQLite: Set guild {guild_id} setting {setting_name} = {value}")
            return True

    async def get_all_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """
        Get all settings for a guild

        Args:
            guild_id: Discord guild ID

        Returns:
            Dictionary of all settings for the guild
        """
        if not self.connection_healthy:
            logger.warning(f"Database not healthy, returning empty settings for guild {guild_id}")
            return {}

        try:
            if self.use_sqlite:
                return await self._get_all_settings_sqlite(guild_id)
            else:
                return await self._get_all_settings_postgresql(guild_id)

        except Exception as e:
            logger.error(f"❌ Error getting all settings for guild {guild_id}: {e}")
            return {}

    async def _get_all_settings_postgresql(self, guild_id: int) -> Dict[str, Any]:
        """Get all settings from PostgreSQL"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT settings FROM guild_settings WHERE guild_id = $1",
                guild_id
            )

            if row and row['settings']:
                settings = dict(row['settings'])
                logger.debug(f"🔍 PostgreSQL: Got {len(settings)} settings for guild {guild_id}")
                return settings
            else:
                logger.debug(f"🔍 PostgreSQL: No settings found for guild {guild_id}")
                return {}

    async def _get_all_settings_sqlite(self, guild_id: int) -> Dict[str, Any]:
        """Get all settings from SQLite"""
        async with aiosqlite.connect(self.sqlite_path) as db:
            cursor = await db.execute(
                "SELECT settings FROM guild_settings WHERE guild_id = ?",
                (guild_id,)
            )
            row = await cursor.fetchone()

            if row and row[0]:
                settings = json.loads(row[0])
                logger.debug(f"🔍 SQLite: Got {len(settings)} settings for guild {guild_id}")
                return settings
            else:
                logger.debug(f"🔍 SQLite: No settings found for guild {guild_id}")
                return {}

    async def set_all_guild_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """
        Set all settings for a guild (overwrites existing)

        Args:
            guild_id: Discord guild ID
            settings: Dictionary of settings to set

        Returns:
            True if successful, False otherwise
        """
        if not self.connection_healthy:
            logger.warning(f"Database not healthy, cannot set settings for guild {guild_id}")
            return False

        try:
            # Add metadata
            settings['last_updated'] = datetime.now().isoformat()
            settings['last_updated_by'] = 'database_manager'
            settings['guild_id'] = guild_id

            if self.use_sqlite:
                return await self._set_all_settings_sqlite(guild_id, settings)
            else:
                return await self._set_all_settings_postgresql(guild_id, settings)

        except Exception as e:
            logger.error(f"❌ Error setting all settings for guild {guild_id}: {e}")
            return False

    async def _set_all_settings_postgresql(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """Set all settings in PostgreSQL"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                               INSERT INTO guild_settings (guild_id, settings, updated_at)
                               VALUES ($1, $2, CURRENT_TIMESTAMP) ON CONFLICT (guild_id) 
                DO
                               UPDATE SET
                                   settings = $2,
                                   updated_at = CURRENT_TIMESTAMP
                               """, guild_id, json.dumps(settings))

            logger.info(f"✅ PostgreSQL: Set all {len(settings)} settings for guild {guild_id}")
            return True

    async def _set_all_settings_sqlite(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """Set all settings in SQLite"""
        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO guild_settings (guild_id, settings, updated_at)
                VALUES (?, ?, ?)
            """, (guild_id, json.dumps(settings), datetime.now().isoformat()))

            await db.commit()

            logger.info(f"✅ SQLite: Set all {len(settings)} settings for guild {guild_id}")
            return True

    async def delete_guild_settings(self, guild_id: int) -> bool:
        """
        Delete all settings for a guild

        Args:
            guild_id: Discord guild ID

        Returns:
            True if successful, False otherwise
        """
        if not self.connection_healthy:
            logger.warning(f"Database not healthy, cannot delete settings for guild {guild_id}")
            return False

        try:
            if self.use_sqlite:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    await db.execute("DELETE FROM guild_settings WHERE guild_id = ?", (guild_id,))
                    await db.commit()
            else:
                async with self.pool.acquire() as conn:
                    await conn.execute("DELETE FROM guild_settings WHERE guild_id = $1", guild_id)

            logger.info(f"🗑️ Deleted all settings for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Error deleting settings for guild {guild_id}: {e}")
            return False

    async def get_all_guilds_with_settings(self) -> List[int]:
        """
        Get list of all guild IDs that have settings

        Returns:
            List of guild IDs
        """
        if not self.connection_healthy:
            return []

        try:
            if self.use_sqlite:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    cursor = await db.execute("SELECT guild_id FROM guild_settings")
                    rows = await cursor.fetchall()
                    return [row[0] for row in rows]
            else:
                async with self.pool.acquire() as conn:
                    rows = await conn.fetch("SELECT guild_id FROM guild_settings")
                    return [row['guild_id'] for row in rows]

        except Exception as e:
            logger.error(f"❌ Error getting guilds with settings: {e}")
            return []

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of the database

        Returns:
            Dictionary with health check results
        """
        health_info = {
            'healthy': False,
            'database_type': 'sqlite' if self.use_sqlite else 'postgresql',
            'connection_ready': self.connection_healthy,
            'last_check': datetime.now().isoformat(),
            'error': None
        }

        try:
            if self.use_sqlite:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    cursor = await db.execute('SELECT COUNT(*) FROM guild_settings')
                    count = await cursor.fetchone()
                    health_info['guild_count'] = count[0] if count else 0
            else:
                async with self.pool.acquire() as conn:
                    count = await conn.fetchval('SELECT COUNT(*) FROM guild_settings')
                    health_info['guild_count'] = count or 0

            health_info['healthy'] = True
            logger.debug(f"💚 Database health check passed - {health_info['guild_count']} guilds")

        except Exception as e:
            health_info['error'] = str(e)
            health_info['healthy'] = False
            logger.error(f"💔 Database health check failed: {e}")

        return health_info

    async def close(self):
        """Close database connections gracefully"""
        try:
            if self.pool and not self.use_sqlite:
                await self.pool.close()
                logger.info("🔒 PostgreSQL connection pool closed")

            self.connection_healthy = False
            logger.info("🔒 Database manager closed")

        except Exception as e:
            logger.error(f"❌ Error closing database: {e}")

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for debugging"""
        return {
            'database_type': 'sqlite' if self.use_sqlite else 'postgresql',
            'connection_healthy': self.connection_healthy,
            'database_url_present': bool(self.database_url),
            'sqlite_path': str(self.sqlite_path) if self.use_sqlite else None,
            'pool_ready': bool(self.pool) if not self.use_sqlite else None
        }


# Global database manager instance (singleton)
db_manager = DatabaseManager()


# Compatibility functions for backward compatibility
async def get_guild_setting(guild_id: int, setting_name: str, default: Any = True) -> Any:
    """Backward compatibility function"""
    return await db_manager.get_guild_setting(guild_id, setting_name, default)


async def set_guild_setting(guild_id: int, setting_name: str, value: Any) -> bool:
    """Backward compatibility function"""
    return await db_manager.set_guild_setting(guild_id, setting_name, value)


async def get_all_guild_settings(guild_id: int) -> Dict[str, Any]:
    """Backward compatibility function"""
    return await db_manager.get_all_guild_settings(guild_id)


async def set_all_guild_settings(guild_id: int, settings: Dict[str, Any]) -> bool:
    """Backward compatibility function"""
    return await db_manager.set_all_guild_settings(guild_id, settings)


# Initialization function
async def initialize_database() -> bool:
    """Initialize the database manager"""
    return await db_manager.initialize()


# Health check function
async def database_health_check() -> Dict[str, Any]:
    """Perform database health check"""
    return await db_manager.health_check()


if __name__ == "__main__":
    # Test the database manager
    async def test_database():
        print("🧪 Testing database manager...")

        # Initialize
        success = await db_manager.initialize()
        print(f"✅ Initialization: {'Success' if success else 'Failed'}")

        if success:
            # Test operations
            test_guild_id = 123456789

            # Test write
            write_success = await db_manager.set_guild_setting(test_guild_id, 'test_setting', True)
            print(f"✅ Write test: {'Success' if write_success else 'Failed'}")

            # Test read
            read_value = await db_manager.get_guild_setting(test_guild_id, 'test_setting', False)
            print(f"✅ Read test: {read_value} (should be True)")

            # Test health check
            health = await db_manager.health_check()
            print(f"✅ Health check: {health}")

            # Cleanup
            await db_manager.delete_guild_settings(test_guild_id)
            print("✅ Cleanup completed")

        await db_manager.close()
        print("🏁 Test completed")


    asyncio.run(test_database())