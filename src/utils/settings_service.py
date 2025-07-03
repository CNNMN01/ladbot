"""
Unified Settings Service - Single source of truth for all settings
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict
import os

logger = logging.getLogger(__name__)


class SettingsService:
    """Unified settings service used by both web dashboard and bot"""

    def __init__(self):
        # Force absolute path in production
        if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RENDER'):
            self.data_dir = Path("/app/data")
        else:
            self.data_dir = Path("data")

        self.guild_settings_dir = self.data_dir / "guild_settings"
        self.guild_settings_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"🔧 Settings service initialized: {self.data_dir}")

    def get_guild_setting(self, guild_id: int, setting_name: str, default: Any = True) -> Any:
        """Get a guild setting - SINGLE SOURCE OF TRUTH"""
        try:
            settings_file = self.guild_settings_dir / f"{guild_id}.json"

            if not settings_file.exists():
                logger.debug(f"No settings file for guild {guild_id}, returning default: {default}")
                return default

            with open(settings_file, 'r') as f:
                guild_settings = json.load(f)
                value = guild_settings.get(setting_name, default)
                logger.debug(f"Guild {guild_id} setting {setting_name}: {value}")
                return value

        except Exception as e:
            logger.error(f"Error reading setting {setting_name} for guild {guild_id}: {e}")
            return default

    def set_guild_setting(self, guild_id: int, setting_name: str, value: Any) -> bool:
        """Set a guild setting - SINGLE SOURCE OF TRUTH"""
        try:
            settings_file = self.guild_settings_dir / f"{guild_id}.json"

            # Load existing settings
            settings_data = {}
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    settings_data = json.load(f)

            # Update setting
            settings_data[setting_name] = value
            settings_data['last_updated'] = f"{os.getpid()}-{id(self)}"  # Unique identifier
            settings_data['guild_id'] = guild_id

            # Save back to file
            with open(settings_file, 'w') as f:
                json.dump(settings_data, f, indent=2)

            logger.info(f"✅ SETTINGS: Set {setting_name}={value} for guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"❌ SETTINGS: Failed to set {setting_name} for guild {guild_id}: {e}")
            return False


# Global instance
settings_service = SettingsService()