"""
Enhanced Ladbot with Complete Compatibility Layer - Render Production Ready
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
    """Simple cog loader for compatibility"""

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
    """Enhanced Discord bot with compatibility layers - Production Ready"""

    def __init__(self):
        from config.settings import settings

        # Configure intents
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
        self.config = settings  # Backward compatibility - CRITICAL FIX

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

        # Web server configuration
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

        # Default to True for unknown settings to avoid breaking functionality
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
        """Setup hook called when bot is starting"""
        logger.info("🔧 Setting up bot components...")

        # Load all cogs
        await self.load_cogs()

        # Start web server in background for Render
        if os.getenv('RENDER') or os.getenv('PORT'):
            self.loop.create_task(self.start_web_server())

    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        cogs_dir = Path(__file__).parent.parent / "cogs"

        # Define load order (admin cogs first, then others)
        load_order = [
            "cogs.admin.console",
            "cogs.admin.reload",
            "cogs.admin.settings",
            "cogs.admin.autoresponses",
            "cogs.admin.error_handler",
            "cogs.admin.moderation",
        ]

        # Add other cogs
        for category in ["entertainment", "information", "utility"]:
            category_path = cogs_dir / category
            if category_path.exists():
                for file in category_path.glob("*.py"):
                    if file.name != "__init__.py":
                        load_order.append(f"cogs.{category}.{file.stem}")

        # Load cogs in order
        loaded_count = 0
        failed_count = 0

        for cog_name in load_order:
            try:
                await self.load_extension(cog_name)
                self.cog_loader.loaded_cogs.add(cog_name)
                logger.info(f"✅ Loaded: {cog_name}")
                loaded_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to load {cog_name}: {e}")
                failed_count += 1

        logger.info(f"🎮 Cog loading complete: {loaded_count} loaded, {failed_count} failed")

    async def start_web_server(self):
        """Start the web server in the background - Render Compatible"""
        try:
            logger.info(f"🌐 Initializing web dashboard on {self.web_host}:{self.web_port}")

            # Import Flask components
            from web.app import create_app

            def run_server():
                try:
                    # Create Flask app with bot instance
                    app = create_app(self)

                    # Configure for production
                    if os.getenv('RENDER'):
                        app.config['ENV'] = 'production'
                        app.config['DEBUG'] = False

                    logger.info(f"🌐 Starting Flask server on {self.web_host}:{self.web_port}")

                    # Start the Flask app
                    app.run(
                        host=self.web_host,
                        port=self.web_port,
                        debug=False,
                        use_reloader=False,
                        threaded=True
                    )

                except Exception as e:
                    logger.error(f"❌ Web server error: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            # Start in background thread
            self.web_thread = threading.Thread(target=run_server, daemon=True)
            self.web_thread.start()

            # Give it a moment to start
            await asyncio.sleep(2)

            logger.info(f"🌐 Web dashboard should be available at: {self.web_url}")

        except ImportError as e:
            logger.warning("🌐 Web dashboard disabled - missing Flask dependencies")
            logger.info("Install with: pip install flask flask-cors")
        except Exception as e:
            logger.error(f"❌ Failed to start web server: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🤖 {self.user.name} (ID: {self.user.id}) is online!")
        logger.info(f"📊 Connected to {len(self.guilds)} guilds")

        # Set status
        try:
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{len(self.guilds)} servers | {self.settings.BOT_PREFIX}help"
                )
            )
        except Exception as e:
            logger.warning(f"Could not set presence: {e}")

        # Log web server status
        if self.web_thread and self.web_thread.is_alive():
            logger.info(f"🌐 Web dashboard running at: {self.web_url}")
        else:
            logger.warning("🌐 Web dashboard not running")

    async def on_command(self, ctx):
        """Called when a command is invoked"""
        self.commands_used_today += 1
        logger.debug(f"Command {ctx.command} used by {ctx.author} in {ctx.guild}")

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        self.error_count += 1

        if isinstance(error, commands.CheckFailure):
            # Don't log permission errors, just send user message
            await ctx.send(f"❌ {error}")
        elif isinstance(error, commands.CommandNotFound):
            # Ignore command not found errors
            pass
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
        else:
            # Log other errors
            logger.error(f"Unhandled error in {ctx.command}: {error}")
            try:
                await ctx.send("❌ An unexpected error occurred. Please try again later.")
            except:
                pass  # Don't crash if we can't send the error message

    async def close(self):
        """Cleanup when bot is shutting down"""
        logger.info("🔄 Bot shutting down...")

        # Stop web server thread if running
        if self.web_thread and self.web_thread.is_alive():
            logger.info("🌐 Stopping web server...")
            # Note: daemon threads will stop automatically

        await super().close()
        logger.info("👋 Bot shutdown complete")