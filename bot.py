#!/usr/bin/env python3
"""
Ladbot - Background Worker Entry Point for Render
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


def setup_logging():
    """Setup logging for Background Worker"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    # Reduce Discord.py noise
    logging.getLogger('discord').setLevel(logging.WARNING)


async def main():
    """Background Worker main function"""
    logger = logging.getLogger(__name__)

    try:
        logger.info("🚀 Starting Ladbot Background Worker...")

        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            logger.info("Using system environment variables")

        setup_logging()

        # Import and start bot
        from bot.ladbot import LadBot
        from config.settings import settings

        logger.info("🤖 Starting Discord bot...")
        bot = LadBot()

        # Start the Discord bot (Background Worker - no web server needed)
        async with bot:
            await bot.start(settings.BOT_TOKEN)

    except KeyboardInterrupt:
        logger.info("👋 Bot shutdown requested")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())