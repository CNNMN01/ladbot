#!/usr/bin/env python3
"""
Ladbot Enhanced - Main Entry Point
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

# Also add the project root to path for imports
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def setup_logging():
    """Setup logging configuration"""
    try:
        from config.settings import settings

        settings.LOGS_DIR.mkdir(exist_ok=True)

        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        handlers = [
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(settings.LOGS_DIR / "bot.log")
        ]

        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format=log_format,
            handlers=handlers
        )

        logging.getLogger('discord').setLevel(logging.WARNING)
    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        raise


def get_port():
    """Get port from environment (for Render compatibility)"""
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

        # Load environment
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

        # Log port information for debugging
        port = get_port()
        host = get_host()
        logger.info(f"🌐 Web server will run on {host}:{port}")

        # Import and start bot
        from bot.ladbot import LadBot

        logger.info("🤖 Starting Discord bot...")
        bot = LadBot()

        # Update bot's web server configuration for Render
        if hasattr(bot, 'web_port'):
            bot.web_port = port
        if hasattr(bot, 'web_host'):
            bot.web_host = host

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