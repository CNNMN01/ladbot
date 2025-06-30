"""
Enhanced Ladbot Discord Bot Class with Comprehensive Settings Management
Fully Production-Ready with Error Prevention and Cog Loader Support
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
    """Enhanced Ladbot with comprehensive settings management and error prevention"""

    def __init__(self):
        """Initialize the bot with enhanced tracking and robust configuration"""
        # Get settings
        from config.settings import settings
        self.settings = settings

        # 🔧 CRITICAL FIX 1: Add config attribute that cogs expect
        self.config = settings  # This is what all cogs expect to find

        # 🔧 CRITICAL FIX 2: Add data_manager for all commands
        self.data_manager = self._create_data_manager()

        # 🔧 CRITICAL FIX 3: Add settings cache for performance
        self.settings_cache = {}  # Guild settings cache
        self.guild_settings = {}  # Compatibility alias

        # 🔧 CRITICAL FIX 4: Add cog_loader for reload command
        self.cog_loader = self._create_cog_loader()

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

        # Memory tracking
        self.memory_usage = 0
        self.cpu_usage = 0

        # Additional compatibility attributes
        self.loaded_cogs = 0
        self.unique_commands_used = 0
        self.total_tracked_commands = 0
        self.average_latency = 0

        logger.info("🔧 Setting up bot components with enhanced error prevention...")

    def _create_cog_loader(self):
        """Create a cog loader for reload command compatibility - FIXED VERSION"""
        class CogLoader:
            def __init__(self, bot):
                self.bot = bot
                self._loaded_cogs_cache = set()

            @property
            def loaded_cogs(self):
                """Get loaded cog names as a set (what reload command expects)"""
                return set(self.bot.extensions.keys())

            @loaded_cogs.setter
            def loaded_cogs(self, value):
                """Setter for compatibility"""
                self._loaded_cogs_cache = set(value) if value else set()

            def get_loaded_cogs(self):
                """Get list of loaded cog names"""
                return list(self.bot.extensions.keys())

            def get_failed_cogs(self):
                """Get list of failed cog names (placeholder)"""
                return []

            async def reload_cog(self, cog_name):
                """Reload a specific cog"""
                try:
                    await self.bot.reload_extension(cog_name)
                    return True
                except Exception as e:
                    logger.error(f"Error in cog loader reload: {e}")
                    return False

            def get_cog_status(self):
                """Get overall cog status"""
                return {
                    'loaded': len(self.bot.extensions),
                    'failed': 0,
                    'total': len(self.bot.extensions)
                }

        return CogLoader(self)

    def _create_data_manager(self):
        """Create a comprehensive data manager with full functionality"""
        class EnhancedDataManager:
            def __init__(self, settings, bot_instance):
                self.settings = settings
                self.bot = bot_instance
                self.logs_dir = settings.LOGS_DIR
                self.data_dir = settings.DATA_DIR

                # Create all necessary directories
                try:
                    self.data_dir.mkdir(parents=True, exist_ok=True)
                    self.logs_dir.mkdir(parents=True, exist_ok=True)

                    # Create subdirectories for organization
                    (self.data_dir / "guild_settings").mkdir(exist_ok=True)
                    (self.data_dir / "autoresponses").mkdir(exist_ok=True)
                    (self.data_dir / "analytics").mkdir(exist_ok=True)
                    (self.data_dir / "backups").mkdir(exist_ok=True)
                    (self.data_dir / "cache").mkdir(exist_ok=True)
                except Exception as e:
                    logger.warning(f"Could not create data directories: {e}")

                # Initialize cache system
                self.guild_cache = {}
                self.autoresponse_cache = {}
                self.last_cache_clear = datetime.now()

            def get_guild_setting(self, guild_id, setting_name, default=True):
                """Get a guild-specific setting with caching"""
                try:
                    # Check cache first
                    cache_key = f"{guild_id}_{setting_name}"
                    if cache_key in self.guild_cache:
                        return self.guild_cache[cache_key]

                    guild_settings_file = self.data_dir / "guild_settings" / f"{guild_id}.json"
                    if guild_settings_file.exists():
                        with open(guild_settings_file, 'r') as f:
                            settings = json.load(f)
                            value = settings.get(setting_name, default)
                            # Cache the result
                            self.guild_cache[cache_key] = value
                            return value

                    # Cache the default
                    self.guild_cache[cache_key] = default
                    return default
                except Exception as e:
                    logger.error(f"Error getting guild setting: {e}")
                    return default

            def set_guild_setting(self, guild_id, setting_name, value):
                """Set a guild-specific setting with caching"""
                try:
                    guild_settings_file = self.data_dir / "guild_settings" / f"{guild_id}.json"
                    settings = {}

                    if guild_settings_file.exists():
                        with open(guild_settings_file, 'r') as f:
                            settings = json.load(f)

                    settings[setting_name] = value
                    settings['last_updated'] = datetime.now().isoformat()

                    with open(guild_settings_file, 'w') as f:
                        json.dump(settings, f, indent=2)

                    # Update cache
                    cache_key = f"{guild_id}_{setting_name}"
                    self.guild_cache[cache_key] = value

                    return True
                except Exception as e:
                    logger.error(f"Error setting guild setting: {e}")
                    return False

            def load_autoresponses(self, guild_id):
                """Load autoresponses for a guild with caching"""
                try:
                    # Check cache first
                    if guild_id in self.autoresponse_cache:
                        return self.autoresponse_cache[guild_id]

                    autoresponses_file = self.data_dir / "autoresponses" / f"{guild_id}.json"
                    if autoresponses_file.exists():
                        with open(autoresponses_file, 'r') as f:
                            responses = json.load(f)
                            # Cache the result
                            self.autoresponse_cache[guild_id] = responses
                            return responses

                    # Cache empty result
                    self.autoresponse_cache[guild_id] = {}
                    return {}
                except Exception as e:
                    logger.error(f"Error loading autoresponses: {e}")
                    return {}

            def save_autoresponses(self, guild_id, autoresponses):
                """Save autoresponses for a guild with caching"""
                try:
                    autoresponses_file = self.data_dir / "autoresponses" / f"{guild_id}.json"
                    autoresponses['last_updated'] = datetime.now().isoformat()

                    with open(autoresponses_file, 'w') as f:
                        json.dump(autoresponses, f, indent=2)

                    # Update cache
                    self.autoresponse_cache[guild_id] = autoresponses
                    return True
                except Exception as e:
                    logger.error(f"Error saving autoresponses: {e}")
                    return False

            def clear_cache(self):
                """Clear all caches"""
                self.guild_cache.clear()
                self.autoresponse_cache.clear()
                self.last_cache_clear = datetime.now()
                logger.info("🗑️ Data manager cache cleared")

            def backup_settings(self):
                """Create a backup of all settings"""
                try:
                    backup_dir = self.data_dir / "backups"
                    backup_file = backup_dir / f"settings_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

                    backup_data = {
                        'timestamp': datetime.now().isoformat(),
                        'guild_settings': {},
                        'autoresponses': {}
                    }

                    # Backup guild settings
                    guild_settings_dir = self.data_dir / "guild_settings"
                    if guild_settings_dir.exists():
                        for file in guild_settings_dir.glob("*.json"):
                            guild_id = file.stem
                            with open(file, 'r') as f:
                                backup_data['guild_settings'][guild_id] = json.load(f)

                    # Backup autoresponses
                    autoresponses_dir = self.data_dir / "autoresponses"
                    if autoresponses_dir.exists():
                        for file in autoresponses_dir.glob("*.json"):
                            guild_id = file.stem
                            with open(file, 'r') as f:
                                backup_data['autoresponses'][guild_id] = json.load(f)

                    with open(backup_file, 'w') as f:
                        json.dump(backup_data, f, indent=2)

                    logger.info(f"📦 Settings backup created: {backup_file}")
                    return backup_file
                except Exception as e:
                    logger.error(f"Error creating settings backup: {e}")
                    return None

            def get_analytics_data(self):
                """Get analytics data for web dashboard"""
                try:
                    analytics_file = self.data_dir / "analytics" / "bot_analytics.json"
                    if analytics_file.exists():
                        with open(analytics_file, 'r') as f:
                            return json.load(f)
                    return {}
                except Exception as e:
                    logger.error(f"Error loading analytics: {e}")
                    return {}

            def save_analytics_data(self, data):
                """Save analytics data"""
                try:
                    analytics_file = self.data_dir / "analytics" / "bot_analytics.json"
                    data['last_updated'] = datetime.now().isoformat()

                    with open(analytics_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    return True
                except Exception as e:
                    logger.error(f"Error saving analytics: {e}")
                    return False

        return EnhancedDataManager(self.settings, self)

    # 🔧 CRITICAL FIX 5: Add all compatibility methods that cogs expect
    def get_setting(self, guild_id, setting_name, default=True):
        """Get a guild-specific setting (primary compatibility method)"""
        return self.data_manager.get_guild_setting(guild_id, setting_name, default)

    def set_setting(self, guild_id, setting_name, value):
        """Set a guild-specific setting (primary compatibility method)"""
        success = self.data_manager.set_guild_setting(guild_id, setting_name, value)
        if success:
            # Fire event for any listeners
            self.dispatch('setting_updated', guild_id, setting_name, value)
        return success

    def get_guild_setting(self, guild_id, setting_name, default=True):
        """Alternative method name for compatibility"""
        return self.get_setting(guild_id, setting_name, default)

    def set_guild_setting(self, guild_id, setting_name, value):
        """Alternative method name for compatibility"""
        return self.set_setting(guild_id, setting_name, value)

    # 🔧 CRITICAL FIX 6: Add prefix property for autoresponses.py
    @property
    def prefix(self):
        """Bot prefix for compatibility with autoresponses.py"""
        return self.command_prefix

    # 🔧 CRITICAL FIX 7: Add helper method for decorators
    def _get_setting_safe(self, guild_id, setting_name, default=True):
        """Helper method for decorators to safely get settings"""
        try:
            return self.get_setting(guild_id, setting_name, default)
        except Exception as e:
            logger.debug(f"Error in _get_setting_safe for {setting_name}: {e}")
            return default

    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            await self.load_cogs()
            logger.info("🎮 All cogs loaded successfully")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")

    async def load_cogs(self):
        """Load all cogs from the cogs directory with enhanced error handling"""
        cogs_dir = Path("src/cogs")
        if not cogs_dir.exists():
            cogs_dir = Path("cogs")

        if not cogs_dir.exists():
            logger.warning("No cogs directory found")
            return

        loaded = 0
        failed = 0
        failed_cogs = []

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
                            failed_cogs.append((cog_name, str(e)))

        self.loaded_cogs = loaded
        logger.info(f"🎮 Cog loading complete: {loaded} loaded, {failed} failed")

        if failed_cogs:
            logger.warning(f"Failed cogs: {', '.join([name for name, _ in failed_cogs])}")

    async def on_ready(self):
        """Called when the bot is ready - Enhanced with comprehensive tracking"""
        # Set start time for uptime calculation
        self.start_time = datetime.now()

        # Load command statistics from persistent storage
        await self.load_command_stats()

        # Initialize latency tracking
        self.latency_history = [round(self.latency * 1000)]
        self.average_latency = round(self.latency * 1000)

        # Update tracking variables
        self.unique_commands_used = len(self.command_usage)
        self.total_tracked_commands = self.total_commands_used

        # Log comprehensive startup info
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")
        logger.info(f"📈 Serving {sum(guild.member_count for guild in self.guilds)} users with {len(self.commands)} commands")

        # Start background tasks
        self.loop.create_task(self.update_stats_task())
        self.loop.create_task(self.cleanup_task())

    async def load_command_stats(self):
        """Load command statistics from file"""
        try:
            stats_file = self.data_manager.data_dir / "analytics" / "command_stats.json"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                    self.command_usage = data.get('command_usage', {})
                    self.total_commands_used = data.get('total_commands_used', 0)
                    self.commands_used_today = data.get('commands_used_today', 0)
                    self.last_reset_date = data.get('last_reset_date', date.today().isoformat())
        except Exception as e:
            logger.error(f"Error loading command stats: {e}")

    async def save_command_stats(self):
        """Save command statistics to file"""
        try:
            stats_file = self.data_manager.data_dir / "analytics" / "command_stats.json"
            data = {
                'command_usage': self.command_usage,
                'total_commands_used': self.total_commands_used,
                'commands_used_today': self.commands_used_today,
                'last_reset_date': self.last_reset_date,
                'last_updated': datetime.now().isoformat()
            }
            with open(stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving command stats: {e}")

    async def on_command_completion(self, ctx):
        """Track command usage"""
        command_name = ctx.command.name

        # Update command usage
        self.command_usage[command_name] = self.command_usage.get(command_name, 0) + 1
        self.total_commands_used += 1
        self.commands_used_today += 1
        self.session_commands += 1

        # Check if we need to reset daily stats
        today = date.today().isoformat()
        if self.last_reset_date != today:
            self.commands_used_today = 1
            self.last_reset_date = today

        # Save stats periodically
        if self.session_commands % 10 == 0:
            await self.save_command_stats()

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        self.error_count += 1

        # Log the error
        logger.error(f"Command error in {ctx.command}: {error}")

        # Send user-friendly error message
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument provided")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f}s")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command")
        else:
            await ctx.send("❌ An unexpected error occurred")

    async def update_stats_task(self):
        """Background task to update bot statistics"""
        await self.wait_until_ready()

        while not self.is_closed():
            try:
                # Update latency history
                current_latency = round(self.latency * 1000)
                self.latency_history.append(current_latency)

                # Keep only last 60 measurements (15 minutes worth)
                if len(self.latency_history) > 60:
                    self.latency_history = self.latency_history[-60:]

                # Calculate average latency
                self.average_latency = sum(self.latency_history) // len(self.latency_history)

                # Update other stats
                self.unique_commands_used = len(self.command_usage)

                # Save stats
                await self.save_command_stats()

            except Exception as e:
                logger.error(f"Error in stats update task: {e}")

            await asyncio.sleep(15)  # Update every 15 seconds

    async def cleanup_task(self):
        """Background task for periodic cleanup"""
        await self.wait_until_ready()

        while not self.is_closed():
            try:
                # Clear cache every hour
                if (datetime.now() - self.data_manager.last_cache_clear).seconds > 3600:
                    self.data_manager.clear_cache()

                # Create backup every 6 hours
                if self.session_commands > 0 and self.session_commands % 100 == 0:
                    self.data_manager.backup_settings()

            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

            await asyncio.sleep(3600)

    def get_stats(self):
        """Get comprehensive bot statistics for web dashboard"""
        try:
            uptime = datetime.now() - self.start_time if self.start_time else datetime.timedelta(0)
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds

            return {
                'guilds': len(self.guilds),
                'users': sum(guild.member_count for guild in self.guilds),
                'commands': len(self.commands),
                'loaded_cogs': len(self.extensions),
                'latency': round(self.latency * 1000),
                'uptime': uptime_str,
                'commands_today': self.commands_used_today,
                'total_commands': self.total_commands_used,
                'session_commands': self.session_commands,
                'error_count': self.error_count,
                'unique_commands_used': len(self.command_usage),
                'bot_status': 'online' if self.is_ready() else 'offline',
                'memory_usage': self.memory_usage,
                'cpu_usage': self.cpu_usage,
                'average_latency': self.average_latency,
                'total_tracked_commands': self.total_commands_used,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return {
                'guilds': 0, 'users': 0, 'commands': 0, 'loaded_cogs': 0,
                'latency': 0, 'uptime': 'Unknown', 'commands_today': 0,
                'total_commands': 0, 'session_commands': 0, 'error_count': 0,
                'unique_commands_used': 0, 'bot_status': 'error'
            }

    async def close(self):
        """Clean shutdown with comprehensive cleanup"""
        try:
            logger.info("🔄 Starting bot shutdown...")

            # Save command stats
            await self.save_command_stats()
            logger.info("💾 Command stats saved")

            # Backup settings
            backup_path = self.data_manager.backup_settings()
            if backup_path:
                logger.info(f"📦 Settings backup created: {backup_path}")

            # Clear cache
            self.data_manager.clear_cache()
            logger.info("🗑️ Cache cleared")

            logger.info("✅ Bot shutdown cleanup complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        await super().close()