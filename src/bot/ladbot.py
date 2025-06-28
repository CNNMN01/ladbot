"""
Enhanced Ladbot with Complete Compatibility Layer - Background Worker Ready
"""

import discord
from discord.ext import commands
import logging
import os
import asyncio
import threading
from datetime import datetime
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class SimpleDataManager:
    """Simple data manager for compatibility"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir.mkdir(exist_ok=True)

        # Compatibility attributes that cogs expect
        self.embed_color = 0x00ff00
        self.logs_dir = Path(__file__).parent.parent.parent / "logs"
        self.logs_dir.mkdir(exist_ok=True)

    def get_data(self, filename):
        """Get data from JSON file"""
        try:
            file_path = self.data_dir / f"{filename}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading data from {filename}: {e}")
            return {}

    def get_json(self, filename):
        """Alias for get_data for backward compatibility"""
        return self.get_data(filename)

    def save_data(self, filename, data):
        """Save data to JSON file"""
        try:
            file_path = self.data_dir / f"{filename}.json"
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {e}")
            return False


class SimpleCogLoader:
    """Simple cog loader for compatibility with proper tracking"""

    def __init__(self, bot):
        self.bot = bot
        self.loaded_cogs = set()

    async def reload_cog(self, cog_name):
        """Reload a specific cog"""
        try:
            await self.bot.reload_extension(cog_name)
            logger.info(f"✅ Reloaded: {cog_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to reload {cog_name}: {e}")
            return False

    def update_loaded_cogs(self):
        """Update the loaded_cogs set with currently loaded extensions"""
        self.loaded_cogs = set(self.bot.extensions.keys())
        logger.debug(f"Updated loaded_cogs: {len(self.loaded_cogs)} cogs tracked")


# Default settings for various features
DEFAULT_SETTINGS = {
    'ping': {'default': True, 'type': 'bool', 'descr': 'Ping command'},
    'help': {'default': True, 'type': 'bool', 'descr': 'Help command'},
    'info': {'default': True, 'type': 'bool', 'descr': 'Bot info command'},
    'say': {'default': True, 'type': 'bool', 'descr': 'Say command'},
    'weather': {'default': True, 'type': 'bool', 'descr': 'Weather information'},
    'crypto': {'default': True, 'type': 'bool', 'descr': 'Crypto prices'},
    'reddit': {'default': True, 'type': 'bool', 'descr': 'Reddit posts'},
    'eightball': {'default': True, 'type': 'bool', 'descr': '8-ball responses'},
    'cmd_8ball': {'default': True, 'type': 'bool', 'descr': '8-ball responses'},
    'jokes': {'default': True, 'type': 'bool', 'descr': 'Joke commands'},
    'ascii_art': {'default': True, 'type': 'bool', 'descr': 'ASCII art generation'},
    'games': {'default': True, 'type': 'bool', 'descr': 'Various games'},
    'dinosaurs': {'default': True, 'type': 'bool', 'descr': 'Dinosaur facts'},
    'bible': {'default': True, 'type': 'bool', 'descr': 'Bible verses'},
    'converter': {'default': True, 'type': 'bool', 'descr': 'Unit converter'},
    'roll': {'default': True, 'type': 'bool', 'descr': 'Dice rolling'},
    'feedback': {'default': True, 'type': 'bool', 'descr': 'User feedback'},
    'tools': {'default': True, 'type': 'bool', 'descr': 'Utility tools'},
    'minesweeper': {'default': True, 'type': 'bool', 'descr': 'Minesweeper game'},
    'autoresponses': {'default': False, 'type': 'bool', 'descr': 'Auto responses'},
}


class LadBot(commands.Bot):
    """Enhanced Discord bot optimized for Background Worker deployment"""

    def __init__(self):
        from config.settings import settings

        # Configure intents for Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True

        super().__init__(
            command_prefix=settings.BOT_PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

        self.settings = settings
        self.config = settings  # Backward compatibility

        # Create compatibility components
        self.data_manager = SimpleDataManager()
        self.cog_loader = SimpleCogLoader(self)

        # Add settings cache for compatibility
        self.settings_cache = {}

        # Add uptime tracking
        self.start_time = datetime.now()

        # Add command usage tracking
        self.commands_used_today = 0

        # Add error tracking
        self.error_count = 0

        # Web server configuration (optional)
        self.web_host = '0.0.0.0'
        self.web_port = int(os.environ.get('PORT', 8080))
        self.web_thread = None

        # Set web URL based on environment
        if os.getenv('RENDER_EXTERNAL_URL'):
            self.web_url = os.getenv('RENDER_EXTERNAL_URL')
        elif os.getenv('RENDER_SERVICE_NAME'):
            service_name = os.getenv('RENDER_SERVICE_NAME')
            self.web_url = f"https://{service_name}.onrender.com"
        else:
            self.web_url = f"http://localhost:{self.web_port}"

    def get_setting(self, guild_id, setting_name):
        """Get a setting value (compatibility method)"""
        # Check cache first
        if guild_id in self.settings_cache and setting_name in self.settings_cache[guild_id]:
            return self.settings_cache[guild_id][setting_name]

        # Load from file if exists
        try:
            settings_file = self.data_manager.data_dir / f"guild_settings_{guild_id}.json"
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    guild_settings = json.load(f)
                    if setting_name in guild_settings:
                        # Cache the result
                        if guild_id not in self.settings_cache:
                            self.settings_cache[guild_id] = {}
                        self.settings_cache[guild_id][setting_name] = guild_settings[setting_name]
                        return guild_settings[setting_name]
        except Exception as e:
            logger.debug(f"Error loading guild settings: {e}")

        # Return default values for common settings
        if setting_name in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[setting_name]['default']

        # Default to True for unknown settings to avoid breaking commands
        return True

    def set_setting(self, guild_id, setting_name, value):
        """Set a setting value (compatibility method)"""
        if guild_id not in self.settings_cache:
            self.settings_cache[guild_id] = {}

        self.settings_cache[guild_id][setting_name] = value

        # Save to file for persistence
        try:
            settings_file = self.data_manager.data_dir / f"guild_settings_{guild_id}.json"
            current_settings = {}
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    current_settings = json.load(f)

            current_settings[setting_name] = value

            with open(settings_file, 'w') as f:
                json.dump(current_settings, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving setting {setting_name} for guild {guild_id}: {e}")

    async def setup_hook(self):
        """Setup bot components - Background Worker optimized"""
        logger.info("🔧 Setting up bot components...")

        # Load all cogs
        await self.load_cogs()

        # Only start web dashboard if explicitly enabled
        web_dashboard_enabled = os.getenv('WEB_DASHBOARD', 'false').lower() == 'true'

        if web_dashboard_enabled and not os.getenv('RENDER'):
            try:
                await self.start_web_dashboard()
            except Exception as e:
                logger.warning(f"Web dashboard failed to start: {e}")
        elif web_dashboard_enabled:
            logger.info("🌐 Web dashboard disabled for Background Worker deployment")

        logger.info("✅ Bot setup completed")

    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        loaded = 0
        failed = 0

        cogs_dir = Path("src/cogs")
        if not cogs_dir.exists():
            logger.error("Cogs directory not found!")
            return

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

        # Update the cog loader with currently loaded cogs
        self.cog_loader.update_loaded_cogs()

        logger.info(f"🎮 Cog loading complete: {loaded} loaded, {failed} failed")

    async def start_web_dashboard(self):
        """Start the web dashboard in a separate thread (optional)"""
        try:
            from web.app import create_app

            app = create_app(self)

            def run_app():
                app.run(
                    host=self.web_host,
                    port=self.web_port,
                    debug=False,
                    threaded=True
                )

            self.web_thread = threading.Thread(target=run_app, daemon=True)
            self.web_thread.start()

            logger.info(f"🌐 Web dashboard started at http://{self.web_host}:{self.web_port}")

        except Exception as e:
            logger.error(f"Failed to start web dashboard: {e}")

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")

        # Calculate stats
        total_users = sum(guild.member_count or 0 for guild in self.guilds)
        total_commands = len([cmd for cmd in self.walk_commands()])

        # Set activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

        # Log startup summary
        environment = "BACKGROUND WORKER" if os.getenv('RENDER') else "DEVELOPMENT"
        logger.info(f"📈 Serving {total_users} users with {total_commands} commands")
        logger.info("🎯 Bot Status Summary:")
        logger.info(f"   • Environment: {environment}")
        logger.info(f"   • Cogs: {len(self.cogs)} loaded")
        logger.info(f"   • Commands: {total_commands} available")
        logger.info(f"   • Latency: {round(self.latency * 1000)}ms")

        if os.getenv('WEB_DASHBOARD', 'false').lower() == 'true':
            logger.info(f"   • Web Dashboard: {self.web_url}")
        else:
            logger.info(f"   • Web Dashboard: Disabled (Background Worker mode)")

        logger.info("🚀 Ladbot is fully operational!")

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        self.error_count += 1

        if isinstance(error, commands.CommandNotFound):
            return

        logger.error(f"Unhandled error in {ctx.command}: {error}")

        # Send user-friendly error message
        embed = discord.Embed(
            title="❌ Command Error",
            description="An unexpected error occurred. This has been logged for investigation.",
            color=0xff0000
        )
        try:
            await ctx.send(embed=embed, delete_after=10)
        except:
            pass

    async def on_guild_join(self, guild):
        """Called when bot joins a new guild"""
        logger.info(f"✅ Joined new guild: {guild.name} (ID: {guild.id}) with {guild.member_count} members")

        # Update activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

    async def on_guild_remove(self, guild):
        """Called when bot leaves a guild"""
        logger.info(f"❌ Left guild: {guild.name} (ID: {guild.id})")

        # Update activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
        )
        await self.change_presence(activity=activity)

    async def close(self):
        """Cleanup when bot shuts down"""
        logger.info("🔄 Bot shutting down...")
        await super().close()
        logger.info("👋 Bot shutdown complete")