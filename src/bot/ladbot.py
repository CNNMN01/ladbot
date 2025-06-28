"""
Enhanced Ladbot Discord Bot Class with Comprehensive Settings Management
Fully Production-Ready with Error Prevention
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

                except (PermissionError, OSError) as e:
                    logger.warning(f"Could not create data directories: {e}")

                logger.info(f"📂 Data manager initialized - Data: {self.data_dir}, Logs: {self.logs_dir}")

            def get_guild_setting(self, guild_id, setting_name, default=True):
                """Get a guild-specific setting with multiple fallback methods"""
                try:
                    # Method 1: Check cache first for performance
                    if guild_id in self.bot.settings_cache:
                        if setting_name in self.bot.settings_cache[guild_id]:
                            return self.bot.settings_cache[guild_id][setting_name]

                    # Method 2: Load from individual guild file
                    settings_file = self.data_dir / f"guild_settings_{guild_id}.json"
                    if settings_file.exists():
                        with open(settings_file, 'r') as f:
                            settings_data = json.load(f)

                        # Update cache
                        if guild_id not in self.bot.settings_cache:
                            self.bot.settings_cache[guild_id] = {}
                        self.bot.settings_cache[guild_id].update(settings_data)

                        return settings_data.get(setting_name, default)

                    # Method 3: Check default options file
                    options_file = self.data_dir / "json" / "options.json"
                    if options_file.exists():
                        try:
                            with open(options_file, 'r') as f:
                                options = json.load(f)
                            if setting_name in options:
                                return options[setting_name].get('default', default)
                        except Exception as e:
                            logger.debug(f"Error loading options file: {e}")

                    # Method 4: Return default
                    return default

                except Exception as e:
                    logger.error(f"Error loading guild setting {setting_name} for guild {guild_id}: {e}")
                    return default

            def set_guild_setting(self, guild_id, setting_name, value):
                """Set a guild-specific setting with comprehensive error handling"""
                try:
                    # Update cache immediately
                    if guild_id not in self.bot.settings_cache:
                        self.bot.settings_cache[guild_id] = {}
                    self.bot.settings_cache[guild_id][setting_name] = value

                    # Load existing settings from file
                    settings_file = self.data_dir / f"guild_settings_{guild_id}.json"
                    settings_data = {}

                    if settings_file.exists():
                        try:
                            with open(settings_file, 'r') as f:
                                settings_data = json.load(f)
                        except json.JSONDecodeError:
                            logger.warning(f"Corrupted settings file for guild {guild_id}, starting fresh")
                            settings_data = {}

                    # Update setting
                    settings_data[setting_name] = value
                    settings_data['last_updated'] = datetime.now().isoformat()
                    settings_data['updated_by'] = 'bot_system'

                    # Save to file with atomic write
                    temp_file = settings_file.with_suffix('.tmp')
                    try:
                        with open(temp_file, 'w') as f:
                            json.dump(settings_data, f, indent=2)

                        # Atomic move
                        temp_file.replace(settings_file)

                        logger.info(f"✅ Updated setting {setting_name} = {value} for guild {guild_id}")
                        return True

                    except Exception as e:
                        logger.error(f"Error writing settings file: {e}")
                        # Clean up temp file
                        if temp_file.exists():
                            temp_file.unlink()
                        return False

                except Exception as e:
                    logger.error(f"Error saving guild setting {setting_name} for guild {guild_id}: {e}")
                    return False

            def get_autoresponses(self, guild_id):
                """Get autoresponses for a guild"""
                try:
                    responses_file = self.data_dir / f"autoresponses_{guild_id}.json"
                    if responses_file.exists():
                        with open(responses_file, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    return []
                except Exception as e:
                    logger.error(f"Error loading autoresponses for guild {guild_id}: {e}")
                    return []

            def save_autoresponses(self, guild_id, responses):
                """Save autoresponses for a guild"""
                try:
                    responses_file = self.data_dir / f"autoresponses_{guild_id}.json"
                    with open(responses_file, 'w', encoding='utf-8') as f:
                        json.dump(responses, f, indent=2, ensure_ascii=False)
                    return True
                except Exception as e:
                    logger.error(f"Error saving autoresponses for guild {guild_id}: {e}")
                    return False

            def clear_cache(self, guild_id=None):
                """Clear settings cache for a guild or all guilds"""
                if guild_id:
                    self.bot.settings_cache.pop(guild_id, None)
                    logger.info(f"🗑️ Cleared cache for guild {guild_id}")
                else:
                    self.bot.settings_cache.clear()
                    logger.info("🗑️ Cleared all settings cache")

            def backup_settings(self):
                """Create a backup of all settings"""
                try:
                    backup_dir = self.data_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_dir.mkdir(parents=True, exist_ok=True)

                    # Copy all guild settings
                    for settings_file in self.data_dir.glob("guild_settings_*.json"):
                        backup_file = backup_dir / settings_file.name
                        backup_file.write_text(settings_file.read_text())

                    logger.info(f"📦 Settings backup created: {backup_dir}")
                    return str(backup_dir)
                except Exception as e:
                    logger.error(f"Error creating settings backup: {e}")
                    return None

        return EnhancedDataManager(self.settings, self)

    # 🔧 CRITICAL FIX 4: Add all compatibility methods that cogs expect
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

        # Initialize settings cache for all guilds
        await self._initialize_guild_settings()

    async def _initialize_guild_settings(self):
        """Initialize settings cache for all connected guilds"""
        try:
            for guild in self.guilds:
                # Pre-load settings for each guild to cache
                self.get_setting(guild.id, "autoresponses", False)
                logger.debug(f"Initialized settings for guild {guild.name} ({guild.id})")

            logger.info(f"📋 Settings cache initialized for {len(self.guilds)} guilds")
        except Exception as e:
            logger.error(f"Error initializing guild settings: {e}")

    async def load_command_stats(self):
        """Load command statistics from persistent storage with enhanced error handling"""
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

            # Load existing stats with error recovery
            try:
                with open(stats_file, 'r') as f:
                    stats_data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Command stats file corrupted, starting fresh")
                self.command_usage = {}
                self.commands_used_today = 0
                self.total_commands_used = 0
                self.session_commands = 0
                self.error_count = 0
                self.last_reset_date = date.today().isoformat()
                await self.save_command_stats()
                return

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
        """Save command statistics to persistent storage with atomic writes"""
        try:
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)

            stats_data = {
                'command_usage': self.command_usage,
                'commands_used_today': self.commands_used_today,
                'total_commands_used': self.total_commands_used,
                'error_count': self.error_count,
                'last_reset_date': self.last_reset_date,
                'last_saved': datetime.now().isoformat(),
                'unique_commands_used': len(self.command_usage),
                'session_commands': self.session_commands
            }

            stats_file = data_dir / "command_stats.json"
            temp_file = stats_file.with_suffix('.tmp')

            # Atomic write
            with open(temp_file, 'w') as f:
                json.dump(stats_data, f, indent=2)
            temp_file.replace(stats_file)

        except Exception as e:
            logger.error(f"Error saving command stats: {e}")

    async def on_command_completion(self, ctx):
        """Called when a command completes successfully - Enhanced tracking"""
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
            self.unique_commands_used = len(self.command_usage)
            self.total_tracked_commands = self.total_commands_used

            # Update latency tracking
            current_latency = round(self.latency * 1000)
            self.latency_history.append(current_latency)
            if len(self.latency_history) > 10:
                self.latency_history.pop(0)
            self.average_latency = sum(self.latency_history) // len(self.latency_history)

            # Save stats periodically (every 10 commands)
            if self.total_commands_used % 10 == 0:
                await self.save_command_stats()

            logger.debug(f"📊 Command tracked: {command_name} (total: {self.total_commands_used})")

        except Exception as e:
            logger.error(f"Error tracking command completion: {e}")

    async def on_command_error(self, ctx, error):
        """Called when a command encounters an error - Enhanced tracking"""
        try:
            self.error_count += 1

            # Don't log these as errors
            if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
                return

            logger.debug(f"❌ Command error tracked: {type(error).__name__}: {error}")
        except Exception as e:
            logger.error(f"Error tracking command error: {e}")

    async def on_guild_join(self, guild):
        """Called when bot joins a new guild - Initialize settings"""
        try:
            logger.info(f"🎉 Joined new guild: {guild.name} ({guild.id})")

            # Initialize default settings for new guild
            self.get_setting(guild.id, "autoresponses", False)
            self.get_setting(guild.id, "minesweeper", True)
            self.get_setting(guild.id, "jokes", True)

            # Update activity status
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
            )
            await self.change_presence(activity=activity)

        except Exception as e:
            logger.error(f"Error handling guild join: {e}")

    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild - Clean up"""
        try:
            logger.info(f"👋 Left guild: {guild.name} ({guild.id})")

            # Clear cache for removed guild
            self.data_manager.clear_cache(guild.id)

            # Update activity status
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
            )
            await self.change_presence(activity=activity)

        except Exception as e:
            logger.error(f"Error handling guild remove: {e}")

    def get_bot_stats(self):
        """Get comprehensive bot statistics for web dashboard"""
        try:
            uptime = datetime.now() - self.start_time if self.start_time else datetime.now() - datetime.now()
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds

            return {
                'guilds': len(self.guilds),
                'users': len(self.users),
                'commands': len(self.commands),
                'loaded_cogs': len(self.cogs),
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