#!/usr/bin/env python3
"""
LADBOT ENHANCED - MAIN ENTRY POINT
Production-ready Discord bot with integrated web dashboard
Optimized for Railway, Render, and local deployment
"""

import asyncio
import logging
import sys
import os
import threading
import signal
import atexit
from pathlib import Path
from datetime import datetime
from typing import Optional

# ===== PATH CONFIGURATION =====
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "src"

# Add paths to Python path for clean imports
for path in [str(PROJECT_ROOT), str(SRC_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)


# ===== LOGGING SETUP =====
def setup_logging():
    """Setup comprehensive logging system"""
    try:
        # Import settings after path is configured
        from config.settings import settings

        # Create logs directory
        logs_dir = PROJECT_ROOT / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Configure logging format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        # Setup handlers
        handlers = [logging.StreamHandler(sys.stdout)]

        # Add file handler if possible
        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                logs_dir / "bot.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(logging.Formatter(log_format))
            handlers.append(file_handler)
        except Exception as e:
            print(f"⚠️  Could not setup file logging: {e}")

        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format=log_format,
            handlers=handlers,
            force=True
        )

        # Reduce noise from external libraries
        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

        # Set specific loggers for our app
        logging.getLogger('ladbot').setLevel(logging.INFO)
        logging.getLogger('web').setLevel(logging.INFO)

        logger = logging.getLogger(__name__)
        logger.info("✅ Logging system configured")
        logger.info(f"📁 Log files: {logs_dir}")
        logger.info(f"📊 Log level: {settings.LOG_LEVEL}")

        return True

    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        return False


# ===== ENVIRONMENT DETECTION =====
def detect_platform() -> str:
    """Detect deployment platform"""
    if os.getenv('RENDER'):
        return 'render'
    elif os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID'):
        return 'railway'
    elif os.getenv('HEROKU_APP_NAME'):
        return 'heroku'
    elif os.getenv('VERCEL'):
        return 'vercel'
    else:
        return 'local'


def get_port() -> int:
    """Get port from environment"""
    return int(os.environ.get('PORT', 8080))


def get_host() -> str:
    """Get host for web server"""
    return '0.0.0.0' if detect_platform() != 'local' else '127.0.0.1'


# ===== WEB SERVER MANAGEMENT =====
class WebServerManager:
    """Manages the web server lifecycle"""

    def __init__(self):
        self.web_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.platform = detect_platform()
        self.port = get_port()
        self.host = get_host()
        self.logger = logging.getLogger(__name__)

    async def start_web_server(self, bot) -> bool:
        """Start web server in background thread"""
        try:
            self.logger.info(f"🌐 Starting web server on {self.platform}")
            self.logger.info(f"📍 Address: http://{self.host}:{self.port}")

            def run_web_server():
                """Web server thread function"""
                try:
                    # Import after paths are set
                    from web.app import run_web_server

                    self.logger.info("🚀 Web server thread starting...")

                    # Run the web server
                    run_web_server(
                        bot=bot,
                        host=self.host,
                        port=self.port,
                        debug=False  # Never debug in threaded mode
                    )

                except Exception as e:
                    self.logger.error(f"❌ Web server thread error: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                finally:
                    self.is_running = False
                    self.logger.info("🛑 Web server thread stopped")

            # Create and start web server thread
            self.web_thread = threading.Thread(
                target=run_web_server,
                name="WebServerThread",
                daemon=True
            )

            self.web_thread.start()
            self.is_running = True

            # Give web server time to start
            await asyncio.sleep(3)

            # Verify web server started
            if self.web_thread.is_alive():
                self.logger.info("✅ Web server started successfully")

                # Log platform-specific URLs
                if self.platform == 'render':
                    render_url = os.getenv('RENDER_EXTERNAL_URL')
                    if render_url:
                        self.logger.info(f"🔗 Render URL: {render_url}")
                elif self.platform == 'railway':
                    self.logger.info("🚂 Railway deployment detected")
                elif self.platform == 'local':
                    self.logger.info(f"💻 Local dashboard: http://localhost:{self.port}")

                return True
            else:
                self.logger.error("❌ Web server failed to start")
                return False

        except Exception as e:
            self.logger.error(f"❌ Failed to start web server: {e}")
            return False

    def stop_web_server(self):
        """Stop web server gracefully"""
        try:
            if self.web_thread and self.web_thread.is_alive():
                self.logger.info("🛑 Stopping web server...")
                self.is_running = False

                # Wait for thread to finish (with timeout)
                self.web_thread.join(timeout=5)

                if self.web_thread.is_alive():
                    self.logger.warning("⚠️  Web server thread did not stop gracefully")
                else:
                    self.logger.info("✅ Web server stopped")

        except Exception as e:
            self.logger.error(f"Error stopping web server: {e}")


# ===== BOT MANAGEMENT =====
class BotManager:
    """Manages the Discord bot lifecycle"""

    def __init__(self):
        self.bot = None
        self.web_manager = WebServerManager()
        self.logger = logging.getLogger(__name__)
        self.shutdown_requested = False

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""

        def signal_handler(signum, frame):
            self.logger.info(f"📡 Received signal {signum}")
            self.shutdown_requested = True

            # Trigger graceful shutdown
            if hasattr(self, 'shutdown_event'):
                self.shutdown_event.set()

        # Register signal handlers
        if sys.platform != 'win32':
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        else:
            signal.signal(signal.SIGINT, signal_handler)

        # Register cleanup function
        atexit.register(self.cleanup)

    async def initialize_bot(self) -> bool:
        """Initialize the Discord bot"""
        try:
            self.logger.info("🤖 Initializing Discord bot...")

            # Import bot class
            from bot.ladbot import LadBot

            # Create bot instance
            self.bot = LadBot()

            # Configure bot for web integration
            self.bot.web_port = self.web_manager.port
            self.bot.web_host = self.web_manager.host

            self.logger.info("✅ Bot initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize bot: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    async def start_services(self) -> bool:
        """Start all services (bot and web server)"""
        try:
            # Start web server if on deployment platform
            if self.web_manager.platform in ['render', 'railway', 'heroku']:
                self.logger.info("🌐 Starting web server for platform deployment...")
                web_started = await self.web_manager.start_web_server(self.bot)

                if not web_started:
                    self.logger.warning("⚠️  Web server failed to start, continuing with bot only")
            else:
                self.logger.info("💻 Local development mode - web server optional")
                # In local mode, you can still start web server
                await self.web_manager.start_web_server(self.bot)

            return True

        except Exception as e:
            self.logger.error(f"❌ Failed to start services: {e}")
            return False

    async def run_bot(self):
        """Run the Discord bot with proper error handling"""
        try:
            # Import settings
            from config.settings import settings

            self.logger.info("🚀 Starting Discord bot...")
            self.logger.info(f"📝 Prefix: {settings.BOT_PREFIX}")
            self.logger.info(f"👥 Admins: {len(settings.ADMIN_IDS)} configured")

            # Create shutdown event
            self.shutdown_event = asyncio.Event()

            # Start the bot
            async with self.bot:
                # Start bot task
                bot_task = asyncio.create_task(self.bot.start(settings.BOT_TOKEN))

                # Wait for shutdown signal
                shutdown_task = asyncio.create_task(self.shutdown_event.wait())

                # Wait for either bot to finish or shutdown signal
                done, pending = await asyncio.wait(
                    [bot_task, shutdown_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Check if bot task completed with error
                if bot_task in done:
                    try:
                        await bot_task
                    except Exception as e:
                        self.logger.error(f"❌ Bot task failed: {e}")
                        raise

                self.logger.info("🛑 Bot shutdown initiated")

        except Exception as e:
            self.logger.error(f"❌ Bot run error: {e}")
            raise

    def cleanup(self):
        """Cleanup resources"""
        try:
            self.logger.info("🧹 Cleaning up resources...")

            # Stop web server
            self.web_manager.stop_web_server()

            # Additional cleanup can be added here

            self.logger.info("✅ Cleanup completed")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


# ===== MAIN APPLICATION =====
async def main():
    """Main application entry point with comprehensive error handling"""
    start_time = datetime.now()
    logger = None

    try:
        # ===== INITIALIZATION =====
        print("🚀 Starting Ladbot Enhanced...")
        print(f"📅 Started at: {start_time}")
        print(f"🐍 Python: {sys.version}")
        print(f"📁 Working directory: {PROJECT_ROOT}")

        # Setup logging first
        logging_ok = setup_logging()
        logger = logging.getLogger(__name__)

        if not logging_ok:
            logger.warning("⚠️  Logging setup had issues, continuing with basic logging")

        # ===== ENVIRONMENT VALIDATION =====
        logger.info("🔍 Validating environment...")

        # Load environment variables
        try:
            from dotenv import load_dotenv
            if (PROJECT_ROOT / ".env").exists():
                load_dotenv(PROJECT_ROOT / ".env")
                logger.info("✅ Environment variables loaded from .env")
            else:
                logger.info("ℹ️  No .env file found, using system environment")
        except ImportError:
            logger.info("ℹ️  python-dotenv not installed, using system environment")

        # Validate configuration
        try:
            from config.settings import settings
            logger.info("✅ Configuration validated")
            logger.info(f"🌍 Environment: {'PRODUCTION' if settings.IS_PRODUCTION else 'DEVELOPMENT'}")
            logger.info(f"🔧 Debug mode: {settings.DEBUG}")
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return 1

        # ===== PLATFORM DETECTION =====
        platform = detect_platform()
        port = get_port()
        host = get_host()

        logger.info(f"🏗️  Platform: {platform.title()}")
        logger.info(f"🌐 Web server: {host}:{port}")

        # Platform-specific logging
        if platform == 'render':
            render_url = os.getenv('RENDER_EXTERNAL_URL')
            logger.info(f"🔗 Render URL: {render_url or 'Not set'}")
        elif platform == 'railway':
            logger.info("🚂 Railway deployment detected")
        elif platform == 'heroku':
            app_name = os.getenv('HEROKU_APP_NAME')
            logger.info(f"🟣 Heroku app: {app_name or 'Unknown'}")

        # ===== BOT STARTUP =====
        logger.info("🤖 Starting bot services...")

        bot_manager = BotManager()

        # Initialize bot
        if not await bot_manager.initialize_bot():
            logger.error("❌ Bot initialization failed")
            return 1

        # Start additional services
        if not await bot_manager.start_services():
            logger.error("❌ Service startup failed")
            return 1

        # ===== MAIN BOT EXECUTION =====
        logger.info("🎮 Starting main bot execution...")

        startup_time = datetime.now() - start_time
        logger.info(f"⚡ Startup completed in {startup_time.total_seconds():.2f} seconds")

        # Run the bot (this blocks until shutdown)
        await bot_manager.run_bot()

        # ===== GRACEFUL SHUTDOWN =====
        logger.info("👋 Bot shutdown completed")
        return 0

    except KeyboardInterrupt:
        if logger:
            logger.info("⌨️  Keyboard interrupt received")
        else:
            print("\n⌨️  Keyboard interrupt received")
        return 0

    except Exception as e:
        if logger:
            logger.error(f"❌ Fatal error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        else:
            print(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        return 1

    finally:
        runtime = datetime.now() - start_time
        if logger:
            logger.info(f"⏱️  Total runtime: {runtime}")
            logger.info("👋 Goodbye!")
        else:
            print(f"⏱️  Total runtime: {runtime}")
            print("👋 Goodbye!")


# ===== UTILITY FUNCTIONS =====

def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        'discord',
        'flask',
        'flask_cors',
        'requests',
        'psutil'
    ]

    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)

    if missing:
        print(f"❌ Missing required dependencies: {', '.join(missing)}")
        print("📦 Install with: pip install -r requirements.txt")
        return False

    return True


def create_required_directories():
    """Create required directories"""
    directories = [
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data" / "analytics",
        PROJECT_ROOT / "data" / "guild_settings"
    ]

    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"⚠️  Could not create directory {directory}: {e}")


def validate_environment():
    """Validate required environment variables"""
    required_vars = ['BOT_TOKEN']
    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("📝 Create a .env file with required variables")
        return False

    return True


# ===== DEVELOPMENT HELPERS =====

def development_mode():
    """Run in development mode with additional features"""
    import asyncio

    async def dev_main():
        # Create directories
        create_required_directories()

        # Validate environment
        if not validate_environment():
            return 1

        # Check dependencies
        if not check_dependencies():
            return 1

        # Run main application
        return await main()

    return asyncio.run(dev_main())


# ===== ENTRY POINT =====

if __name__ == "__main__":
    try:
        # Check for development mode
        if len(sys.argv) > 1 and sys.argv[1] == "dev":
            exit_code = development_mode()
        else:
            # Create required directories
            create_required_directories()

            # Run main application
            exit_code = asyncio.run(main())

        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Critical startup error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)