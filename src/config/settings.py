"""
Enhanced Bot Configuration Settings - Environment Variables with Compatibility
"""
import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        # Primary configuration
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", "")
        self.BOT_PREFIX = os.getenv("BOT_PREFIX", "l.")

        # Parse admin IDs with error handling
        self.ADMIN_IDS = []
        admin_str = os.getenv("ADMIN_IDS", "")
        if admin_str:
            try:
                self.ADMIN_IDS = [int(x.strip()) for x in admin_str.split(",") if x.strip()]
            except ValueError as e:
                logger.warning(f"Invalid ADMIN_IDS format: {e}")

        # Compatibility attributes - CRITICAL FIX
        self.admin_ids = self.ADMIN_IDS  # Lowercase for backward compatibility
        self.prefix = self.BOT_PREFIX    # prefix attribute for autoresponses

        # Other configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"

        # Paths
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"
        self.DATA_DIR = self.PROJECT_ROOT / "data"

        # Web configuration
        self.WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", "dev-secret-key-change-me")
        self.DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
        self.DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
        self.DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")

        # API keys
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

        self.validate()

    def validate(self):
        """Validate critical configuration"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")

        # Create directories
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.DATA_DIR.mkdir(exist_ok=True)

        logger.info(f"✅ Settings loaded - Prefix: {self.BOT_PREFIX}, Admin IDs: {len(self.ADMIN_IDS)}")

# Global settings instance
settings = Settings()