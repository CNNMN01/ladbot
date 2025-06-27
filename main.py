#!/usr/bin/env python3
"""
Ladbot Enhanced - Main Entry Point
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

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
    # Import after path is set
    try:
        from config.settings import settings
    except ImportError:
        # Fallback import method
        import importlib.util
        config_path = Path(__file__).parent / "src" / "config" / "settings.py"
        spec = importlib.util.spec_from_file_location("settings", config_path)
        settings_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings_module)
        settings = settings_module.settings

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


async def main():
    """Main application entry point"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("🚀 Starting Ladbot Enhanced...")

        # Load environment
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✅ Environment loaded")
        except ImportError:
            logger.warning("python-dotenv not installed, using system environment")

        setup_logging()

        # Validate configuration
        try:
            from config.settings import settings
        except ImportError:
            # Fallback import method
            import importlib.util
            config_path = Path(__file__).parent / "src" / "config" / "settings.py"
            spec = importlib.util.spec_from_file_location("settings", config_path)
            settings_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(settings_module)
            settings = settings_module.settings

        settings.validate()
        logger.info("✅ Configuration validated")

        # Create and start bot
        try:
            from bot.ladbot import LadBot
        except ImportError:
            # Fallback import method
            import importlib.util
            bot_path = Path(__file__).parent / "src" / "bot" / "ladbot.py"
            spec = importlib.util.spec_from_file_location("ladbot", bot_path)
            ladbot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ladbot_module)
            LadBot = ladbot_module.LadBot

        bot = LadBot()

        logger.info("🤖 Starting Discord bot...")
        await bot.start(settings.BOT_TOKEN)

    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)