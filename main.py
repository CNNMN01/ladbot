#!/usr/bin/env python3
"""
Ladbot Enhanced - Main Entry Point (Render Compatible)
"""
import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to Python path
src_path = str(Path(__file__).parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def setup_logging():
    """Setup logging configuration for Render"""
    try:
        from config.settings import settings

        # Create logs directory if it doesn't exist
        settings.LOGS_DIR.mkdir(exist_ok=True)

        # Configure logging
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        # Always log to stdout for Render
        handlers = [logging.StreamHandler(sys.stdout)]

        # Also log to file if possible
        try:
            handlers.append(logging.FileHandler(settings.LOGS_DIR / "bot.log"))
        except (PermissionError, OSError):
            # If file logging fails, just use stdout
            pass

        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format=log_format,
            handlers=handlers
        )

        # Reduce Discord.py noise
        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('discord.http').setLevel(logging.WARNING)

    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def get_port():
    """Get port from environment (Render sets this automatically)"""
    return int(os.environ.get('PORT', 8080))


def get_host():
    """Get host for web server"""
    return '0.0.0.0'


async def main():
    """Main application entry point"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("🚀 Starting Ladbot Enhanced...")
        logger.info(f"📅 Started at: {datetime.now()}")
        logger.info(f"🌍 Environment: {'PRODUCTION' if os.getenv('RENDER') else 'DEVELOPMENT'}")

        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✅ Environment loaded")
        except ImportError:
            logger.warning("python-dotenv not installed, using system environment")

        setup_logging()

        # Validate configuration
        from config.settings import settings
        logger.info("✅ Configuration validated")

        # Log deployment info
        port = get_port()
        host = get_host()
        logger.info(f"🌐 Web server will run on {host}:{port}")

        if os.getenv('RENDER'):
            logger.info(f"🔗 Render deployment detected")
            logger.info(f"🌍 Public URL will be available once deployed")

        # Import and start bot
        from bot.ladbot import LadBot

        logger.info("🤖 Starting Discord bot...")
        bot = LadBot()

        # Configure for Render
        bot.web_port = port
        bot.web_host = host

        # Set production URL if on Render
        if os.getenv('RENDER_EXTERNAL_URL'):
            bot.web_url = os.getenv('RENDER_EXTERNAL_URL')
        elif os.getenv('RENDER_SERVICE_NAME'):
            # Construct Render URL
            service_name = os.getenv('RENDER_SERVICE_NAME')
            bot.web_url = f"https://{service_name}.onrender.com"

        async with bot:
            await bot.start(settings.BOT_TOKEN)

    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)
    finally:
        logger.info("👋 Bot shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)