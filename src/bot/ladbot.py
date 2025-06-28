"""
Enhanced Ladbot Discord Bot Class with Real Command Tracking
"""
import asyncio
import logging
import threading
from pathlib import Path
from datetime import datetime, date
import json
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class LadBot(commands.Bot):
    """Enhanced Ladbot with real command tracking and web dashboard integration"""

    def __init__(self):
        """Initialize the bot with enhanced tracking"""
        # Get settings
        from config.settings import settings
        self.settings = settings

        # 🔧 FIX 1: Add config attribute that cogs expect
        self.config = settings  # This is what was missing!

        # 🔧 FIX 2: Add data_manager for admin commands
        self.data_manager = self._create_data_manager()

        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        # Initialize bot
        super().__init__(
            command_prefix=settings.BOT_PREFIX,
            intents=intents,
            help_command=None
        )

        # Web server configuration
        self.web_port = 8080
        self.web_host = '0.0.0.0'
        self.web_url = None
        self.web_thread = None

        # Real command tracking initialization
        self.command_usage = {}  # {command_name: usage_count}
        self.commands_used_today = 0
        self.total_commands_used = 0
        self.session_commands = 0
        self.error_count = 0
        self.last_reset_date = date.today().isoformat()

        # Performance tracking
        self.start_time = None  # Will be set in on_ready
        self.last_latency_check = datetime.now()
        self.latency_history = []

        # 🔧 FIX 3: Add settings manager for guild-specific settings
        self.guild_settings = {}  # Store per-guild settings

        logger.info("🔧 Setting up bot components...")

    def _create_data_manager(self):
        """Create a simple data manager object"""
        class DataManager:
            def __init__(self, settings):
                self.settings = settings
                self.logs_dir = settings.LOGS_DIR
                self.data_dir = settings.DATA_DIR

            def get_guild_setting(self, guild_id, setting_name, default=True):
                """Get a guild-specific setting"""
                return default  # For now, return default values

            def set_guild_setting(self, guild_id, setting_name, value):
                """Set a guild-specific setting"""
                pass  # For now, do nothing

        return DataManager(self.settings)

    def get_setting(self, guild_id, setting_name, default=True):
        """Get a guild-specific setting (compatibility method)"""
        return self.data_manager.get_guild_setting(guild_id, setting_name, default)

    def set_setting(self, guild_id, setting_name, value):
        """Set a guild-specific setting (compatibility method)"""
        return self.data_manager.set_guild_setting(guild_id, setting_name, value)

    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            await self.load_cogs()
            logger.info("🎮 All cogs loaded successfully")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")

    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        cogs_dir = Path("src/cogs")
        if not cogs_dir.exists():
            cogs_dir = Path("cogs")

        if not cogs_dir.exists():
            logger.warning("No cogs directory found")
            return

        loaded = 0
        failed = 0

        # Discover and load cogs
        for category_dir in cogs_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("_"):
                for cog_file in category_dir.glob("*.py"):
                    if cog_file.name != "__init__.py":
                        cog_name = f"cogs.{category_dir.name}.{cog_file.stem}"
                        try:
                            await self.load_extension(cog_name)
                            logger.info(f"✅ Loaded: {cog_name}")
                            loaded += 1
                        except Exception as e:
                            logger.error(f"❌ Failed to load {cog_name}: {e}")
                            failed += 1

        logger.info(f"🎮 Cog loading complete: {loaded} loaded, {failed} failed")

    async def on_ready(self):
        """Called when the bot is ready - Enhanced with real command tracking"""
        # Set start time for uptime calculation
        self.start_time = datetime.now()

        # Load command statistics from persistent storage
        await self.load_command_stats()

        # Initialize latency tracking
        self.latency_history = [round(self.latency * 1000)]

        # Log comprehensive startup info
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"👥 Serving {len(self.users)} users")
        logger.info(f"🎮 Loaded {len(self.cogs)} cogs")
        logger.info(f"🔧 {len(self.commands)} commands available")
        logger.info(f"📈 Command stats: {self.total_commands_used} total, {self.commands_used_today} today")
        logger.info(f"📊 Unique commands used: {len(self.command_usage)}")
        logger.info(f"🕐 Start time recorded: {self.start_time}")
        logger.info(f"📡 Initial latency: {round(self.latency * 1000)}ms")

        # Set activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

    async def load_command_stats(self):
        """Load command statistics from persistent storage"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            stats_file = data_dir / "command_stats.json"

            if not stats_file.exists():
                # Initialize empty stats
                self.command_usage = {}
                self.commands_used_today = 0
                self.total_commands_used = 0
                self.session_commands = 0
                self.error_count = 0
                self.last_reset_date = date.today().isoformat()
                logger.info("📊 No existing command stats found, starting fresh")
                await self.save_command_stats()  # Create initial file
                return

            # Load existing stats
            with open(stats_file, 'r') as f:
                stats_data = json.load(f)

            self.command_usage = stats_data.get('command_usage', {})
            self.commands_used_today = stats_data.get('commands_used_today', 0)
            self.total_commands_used = stats_data.get('total_commands_used', 0)
            self.session_commands = 0  # Always reset session commands
            self.error_count = stats_data.get('error_count', 0)
            self.last_reset_date = stats_data.get('last_reset_date', date.today().isoformat())

            # Check if we need to reset daily count
            if self.last_reset_date != date.today().isoformat():
                logger.info("📅 New day detected - resetting daily command count")
                self.commands_used_today = 0
                self.last_reset_date = date.today().isoformat()
                await self.save_command_stats()

            logger.info(f"📊 Command stats loaded: {self.total_commands_used} total, {self.commands_used_today} today")

        except Exception as e:
            logger.error(f"Error loading command stats: {e}")
            # Initialize with defaults on error
            self.command_usage = {}
            self.commands_used_today = 0
            self.total_commands_used = 0
            self.session_commands = 0
            self.error_count = 0
            self.last_reset_date = date.today().isoformat()

    async def save_command_stats(self):
        """Save command statistics to persistent storage"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            stats_data = {
                'command_usage': self.command_usage,
                'commands_used_today': self.commands_used_today,
                'total_commands_used': self.total_commands_used,
                'error_count': self.error_count,
                'last_reset_date': self.last_reset_date,
                'last_saved': datetime.now().isoformat()
            }

            stats_file = data_dir / "command_stats.json"
            with open(stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving command stats: {e}")

    async def on_command_completion(self, ctx):
        """Called when a command completes successfully - REAL tracking"""
        try:
            command_name = ctx.command.name if ctx.command else 'unknown'

            # Update command usage statistics
            if command_name not in self.command_usage:
                self.command_usage[command_name] = 0
            self.command_usage[command_name] += 1

            # Update counters
            self.commands_used_today += 1
            self.total_commands_used += 1
            self.session_commands += 1

            # Save stats periodically (every 10 commands)
            if self.total_commands_used % 10 == 0:
                await self.save_command_stats()

            logger.debug(f"📊 Command tracked: {command_name} (total: {self.total_commands_used})")

        except Exception as e:
            logger.error(f"Error tracking command completion: {e}")

    async def on_command_error(self, ctx, error):
        """Called when a command encounters an error"""
        try:
            self.error_count += 1
            logger.debug(f"❌ Command error tracked: {error}")
        except Exception as e:
            logger.error(f"Error tracking command error: {e}")

    async def close(self):
        """Clean shutdown with stat saving"""
        try:
            await self.save_command_stats()
            logger.info("💾 Command stats saved on shutdown")
        except Exception as e:
            logger.error(f"Error saving stats on shutdown: {e}")

        await super().close()