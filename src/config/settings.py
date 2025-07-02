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

        # ===== ENHANCED WEB DASHBOARD SETTINGS =====

        # Environment settings
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

        # Security settings
        self.FORCE_HTTPS = os.getenv("FORCE_HTTPS", "false").lower() == "true"
        self.CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
        self.CSP_ENABLED = os.getenv("CSP_ENABLED", "true").lower() == "true"
        self.SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").lower() == "true"

        # Session settings
        self.SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "604800"))  # 7 days default
        self.MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "16"))  # MB

        # Rate limiting
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

        # Cache settings
        self.CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
        self.CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default

        # Feature flags
        self.WEATHER_ENABLED = os.getenv("WEATHER_ENABLED", "true").lower() == "true"
        self.CRYPTO_ENABLED = os.getenv("CRYPTO_ENABLED", "true").lower() == "true"
        self.GAMES_ENABLED = os.getenv("GAMES_ENABLED", "true").lower() == "true"
        self.REDDIT_ENABLED = os.getenv("REDDIT_ENABLED", "false").lower() == "true"
        self.AI_FEATURES_ENABLED = os.getenv("AI_FEATURES_ENABLED", "false").lower() == "true"

        # Monitoring and analytics
        self.PERFORMANCE_MONITORING = os.getenv("PERFORMANCE_MONITORING", "true").lower() == "true"
        self.ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "false").lower() == "true"
        self.REQUEST_LOGGING = os.getenv("REQUEST_LOGGING", "true").lower() == "true"

        # Backup settings
        self.AUTO_BACKUP_ENABLED = os.getenv("AUTO_BACKUP_ENABLED", "true").lower() == "true"
        self.BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
        self.BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

        # Maintenance mode
        self.MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
        self.MAINTENANCE_MESSAGE = os.getenv("MAINTENANCE_MESSAGE",
                                             "Ladbot is currently under maintenance. Please check back soon!")

        # Development settings (only in development)
        if self.IS_DEVELOPMENT:
            self.FLASK_DEBUG_TOOLBAR = os.getenv("FLASK_DEBUG_TOOLBAR", "false").lower() == "true"
            self.SQL_DEBUG = os.getenv("SQL_DEBUG", "false").lower() == "true"
            self.HOT_RELOAD = os.getenv("HOT_RELOAD", "true").lower() == "true"
        else:
            self.FLASK_DEBUG_TOOLBAR = False
            self.SQL_DEBUG = False
            self.HOT_RELOAD = False

        # External service APIs (optional)
        self.GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
        self.SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self.YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
        self.REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
        self.REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
        self.REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "Ladbot/2.0")

        # Database configuration (future-ready)
        self.DATABASE_URL = os.getenv("DATABASE_URL", "")
        self.MONGODB_URI = os.getenv("MONGODB_URI", "")

        # Error reporting and monitoring
        self.SENTRY_DSN = os.getenv("SENTRY_DSN", "")
        self.GOOGLE_ANALYTICS_ID = os.getenv("GOOGLE_ANALYTICS_ID", "")

        # Production optimizations
        if self.IS_PRODUCTION:
            # Disable debug features in production
            self.DEBUG = False
            # Enable security features in production
            if not self.FORCE_HTTPS:
                self.FORCE_HTTPS = True  # Force HTTPS in production unless explicitly disabled
            if self.CORS_ORIGINS == "*":
                logger.warning("CORS_ORIGINS is set to '*' in production - consider restricting this")

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

        # Validate session timeout
        if self.SESSION_TIMEOUT < 3600:  # Less than 1 hour
            logger.warning("SESSION_TIMEOUT is very short, consider increasing it")

        # Validate upload size
        if self.MAX_UPLOAD_SIZE > 100:  # More than 100MB
            logger.warning("MAX_UPLOAD_SIZE is very large, consider reducing it")

        # Validate backup settings
        if self.AUTO_BACKUP_ENABLED and self.BACKUP_INTERVAL_HOURS < 1:
            logger.warning("BACKUP_INTERVAL_HOURS is too frequent, setting to 1 hour minimum")
            self.BACKUP_INTERVAL_HOURS = 1

        # Create directories (handle permission errors in production)
        try:
            self.LOGS_DIR.mkdir(exist_ok=True)
            self.DATA_DIR.mkdir(exist_ok=True)

            # Create subdirectories for better organization
            (self.DATA_DIR / "analytics").mkdir(exist_ok=True)
            (self.DATA_DIR / "guild_settings").mkdir(exist_ok=True)
            (self.DATA_DIR / "backups").mkdir(exist_ok=True)
            (self.DATA_DIR / "cache").mkdir(exist_ok=True)

        except (PermissionError, OSError) as e:
            logger.warning(f"Could not create directories: {e}")

        # Log configuration summary
        logger.info(f"✅ Settings loaded - Environment: {'PRODUCTION' if self.IS_PRODUCTION else 'DEVELOPMENT'}")
        logger.info(f"✅ Prefix: {self.BOT_PREFIX}, Admin IDs: {len(self.ADMIN_IDS)}")
        logger.info(f"✅ Redirect URI: {self.DISCORD_REDIRECT_URI}")
        logger.info(
            f"✅ Features enabled: Weather({self.WEATHER_ENABLED}), Crypto({self.CRYPTO_ENABLED}), Games({self.GAMES_ENABLED})")

        if self.MAINTENANCE_MODE:
            logger.warning("⚠️  MAINTENANCE MODE ENABLED - Bot functionality may be limited")

    def get_database_url(self):
        """Get the appropriate database URL based on environment"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        elif self.MONGODB_URI:
            return self.MONGODB_URI
        else:
            # Default to SQLite for local development
            return f"sqlite:///{self.DATA_DIR}/ladbot.db"

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled"""
        feature_map = {
            'weather': self.WEATHER_ENABLED,
            'crypto': self.CRYPTO_ENABLED,
            'games': self.GAMES_ENABLED,
            'reddit': self.REDDIT_ENABLED,
            'ai': self.AI_FEATURES_ENABLED,
            'analytics': self.ANALYTICS_ENABLED,
            'monitoring': self.PERFORMANCE_MONITORING,
            'backup': self.AUTO_BACKUP_ENABLED,
        }
        return feature_map.get(feature_name.lower(), False)

    def get_api_key(self, service: str) -> str:
        """Get API key for external services"""
        api_keys = {
            'openweather': self.OPENWEATHER_API_KEY,
            'github': self.GITHUB_TOKEN,
            'spotify_client_id': self.SPOTIFY_CLIENT_ID,
            'spotify_client_secret': self.SPOTIFY_CLIENT_SECRET,
            'youtube': self.YOUTUBE_API_KEY,
            'reddit_client_id': self.REDDIT_CLIENT_ID,
            'reddit_client_secret': self.REDDIT_CLIENT_SECRET,
        }
        return api_keys.get(service.lower(), "")

    def __repr__(self):
        """String representation of settings (without sensitive data)"""
        return (f"Settings(environment={self.ENVIRONMENT}, "
                f"prefix='{self.BOT_PREFIX}', "
                f"admin_count={len(self.ADMIN_IDS)}, "
                f"features_enabled={sum([self.WEATHER_ENABLED, self.CRYPTO_ENABLED, self.GAMES_ENABLED])})")


# Global settings instance
settings = Settings()