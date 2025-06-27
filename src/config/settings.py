"""
Enhanced Bot Configuration Settings - Production Ready
"""
import os
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        # Detect environment
        self.IS_PRODUCTION = bool(os.getenv('RENDER') or os.getenv('RAILWAY_ENVIRONMENT'))
        self.IS_DEVELOPMENT = not self.IS_PRODUCTION

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
        self.admin_ids = self.ADMIN_IDS
        self.prefix = self.BOT_PREFIX

        # Logging configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if self.IS_PRODUCTION else "DEBUG")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true" and self.IS_DEVELOPMENT

        # Paths (production-safe)
        self.PROJECT_ROOT = Path(__file__).parent.parent.parent
        self.LOGS_DIR = self.PROJECT_ROOT / "logs"
        self.DATA_DIR = self.PROJECT_ROOT / "data"

        # Web configuration
        self.WEB_SECRET_KEY = os.getenv("WEB_SECRET_KEY", self._generate_secret_key())
        self.DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
        self.DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")

        # Dynamic redirect URI based on environment
        if self.IS_PRODUCTION:
            # Try to get from environment first
            self.DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
            if not self.DISCORD_REDIRECT_URI:
                # Try to construct from Render environment
                if os.getenv('RENDER_EXTERNAL_URL'):
                    self.DISCORD_REDIRECT_URI = f"{os.getenv('RENDER_EXTERNAL_URL')}/callback"
                elif os.getenv('RENDER_SERVICE_NAME'):
                    service_name = os.getenv('RENDER_SERVICE_NAME')
                    self.DISCORD_REDIRECT_URI = f"https://{service_name}.onrender.com/callback"
                else:
                    # Fallback
                    self.DISCORD_REDIRECT_URI = "https://your-app.onrender.com/callback"
        else:
            self.DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8080/callback")

        # API keys
        self.OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

        # Production optimizations
        if self.IS_PRODUCTION:
            # Disable debug features in production
            self.DEBUG = False

        self.validate()

    def _generate_secret_key(self):
        """Generate a secret key if none provided"""
        if self.IS_PRODUCTION:
            logger.warning("WEB_SECRET_KEY not set in production! Using generated key.")

        import secrets
        return secrets.token_hex(32)

    def validate(self):
        """Validate critical configuration"""
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")

        if self.IS_PRODUCTION and not self.DISCORD_CLIENT_SECRET:
            logger.warning("DISCORD_CLIENT_SECRET not set - web dashboard OAuth won't work")

        # Create directories (handle permission errors in production)
        try:
            self.LOGS_DIR.mkdir(exist_ok=True)
            self.DATA_DIR.mkdir(exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not create directories: {e}")

        logger.info(f"✅ Settings loaded - Environment: {'PRODUCTION' if self.IS_PRODUCTION else 'DEVELOPMENT'}")
        logger.info(f"✅ Prefix: {self.BOT_PREFIX}, Admin IDs: {len(self.ADMIN_IDS)}")
        logger.info(f"✅ Redirect URI: {self.DISCORD_REDIRECT_URI}")

# Global settings instance
settings = Settings()