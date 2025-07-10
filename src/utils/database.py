"""
Database setup for settings storage
"""
import os
import logging
import asyncpg
import asyncio
import json
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and settings operations"""

    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.pool = None

    async def initialize(self):
        """Initialize database connection pool with retry logic"""
        retry_count = 3
        for attempt in range(retry_count):
            try:
                if not self.database_url:
                    logger.error("❌ DATABASE_URL not found in environment variables")
                    return False

                # Create connection pool with Railway-optimized settings
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=1,  # Start smaller for Railway
                    max_size=5,  # Reasonable limit
                    command_timeout=30,
                    server_settings={
                        'application_name': 'ladbot',
                        'jit': 'off'  # Disable JIT for better Railway compatibility
                    }
                )

                # Create tables if they don't exist
                await self.create_tables()
                logger.info("✅ Database initialized successfully")
                return True

            except Exception as e:
                logger.error(f"❌ Database init attempt {attempt+1} failed: {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        return False

    async def create_tables(self):
        """Create settings table if it doesn't exist"""
        create_sql = """
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id BIGINT PRIMARY KEY,
            settings JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_guild_settings_updated 
        ON guild_settings(updated_at);
        """

        async with self.pool.acquire() as conn:
            await conn.execute(create_sql)
            logger.info("📊 Database tables created/verified")

    async def get_guild_setting(self, guild_id: int, setting_name: str, default: Any = True) -> Any:
        """Get a specific guild setting from database"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT settings FROM guild_settings WHERE guild_id = $1",
                    guild_id
                )

                if row and row['settings']:
                    settings = dict(row['settings'])
                    value = settings.get(setting_name, default)
                    logger.debug(f"DB GET: Guild {guild_id} setting {setting_name} = {value}")
                    return value
                else:
                    logger.debug(f"DB GET: No settings for guild {guild_id}, returning default {default}")
                    return default

        except Exception as e:
            logger.error(f"❌ Error getting setting {setting_name} for guild {guild_id}: {e}")
            return default

    async def set_guild_setting(self, guild_id: int, setting_name: str, value: Any) -> bool:
        """Set a specific guild setting in database"""
        try:
            async with self.pool.acquire() as conn:
                # Get existing settings or create new
                row = await conn.fetchrow(
                    "SELECT settings FROM guild_settings WHERE guild_id = $1",
                    guild_id
                )

                if row:
                    settings = dict(row['settings'])
                else:
                    settings = {}

                # Update the specific setting
                settings[setting_name] = value
                settings['last_updated'] = datetime.now().isoformat()

                # Upsert the settings
                await conn.execute("""
                    INSERT INTO guild_settings (guild_id, settings, updated_at) 
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET 
                        settings = $2,
                        updated_at = CURRENT_TIMESTAMP
                """, guild_id, json.dumps(settings))

                logger.info(f"✅ DB SET: Guild {guild_id} setting {setting_name} = {value}")
                return True

        except Exception as e:
            logger.error(f"❌ Error setting {setting_name} for guild {guild_id}: {e}")
            return False

    async def get_all_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Get all settings for a guild"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT settings FROM guild_settings WHERE guild_id = $1",
                    guild_id
                )

                if row and row['settings']:
                    return dict(row['settings'])
                else:
                    return {}

        except Exception as e:
            logger.error(f"❌ Error getting all settings for guild {guild_id}: {e}")
            return {}

    async def set_all_guild_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """Set all settings for a guild"""
        try:
            settings['last_updated'] = datetime.now().isoformat()

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO guild_settings (guild_id, settings, updated_at) 
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    ON CONFLICT (guild_id) 
                    DO UPDATE SET 
                        settings = $2,
                        updated_at = CURRENT_TIMESTAMP
                """, guild_id, json.dumps(settings))

                logger.info(f"✅ DB SET ALL: Guild {guild_id} - {len(settings)} settings updated")
                return True

        except Exception as e:
            logger.error(f"❌ Error setting all settings for guild {guild_id}: {e}")
            return False

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("📊 Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()