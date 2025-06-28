#!/usr/bin/env python3
"""
Ladbot Enhanced - Main Entry Point (Render Compatible)
"""
import asyncio
import logging
import sys
import os
import threading
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


async def start_render_web_server(bot):
    """Start web server for Render port detection and health checks"""
    try:
        port = get_port()
        host = get_host()

        logger = logging.getLogger(__name__)
        logger.info(f"🌐 Starting web server for Render on {host}:{port}")

        try:
            # Try to import full web dashboard
            from web.app import create_app
            app = create_app(bot)
            logger.info("✅ Full web dashboard loaded")
        except ImportError:
            # Fallback to simple Flask app for port detection
            logger.warning("⚠️ Full web dashboard not available, using simple health server")
            from flask import Flask, jsonify
            app = Flask(__name__)

            @app.route('/')
            def health_check():
                return "Ladbot is running!", 200

            @app.route('/health')
            def health():
                return jsonify({
                    "status": "healthy",
                    "bot_name": "Ladbot",
                    "guilds": len(bot.guilds) if hasattr(bot, 'guilds') else 0,
                    "timestamp": datetime.now().isoformat()
                }), 200

        def run_flask():
            """Run Flask in background thread"""
            try:
                logger.info(f"🌐 Web server binding to {host}:{port}")
                app.run(
                    host=host,
                    port=port,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except Exception as e:
                logger.error(f"❌ Flask server error: {e}")

        # Start Flask in daemon thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Give server time to bind to port
        await asyncio.sleep(2)

        logger.info(f"✅ Web server should be accessible on port {port}")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Failed to start web server: {e}")

        # Create minimal fallback server for Render port detection
        try:
            import http.server
            import socketserver

            class HealthHandler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"Ladbot Health Check OK")

                def log_message(self, format, *args):
                    pass  # Suppress logs

            def run_fallback():
                port = get_port()
                with socketserver.TCPServer(("", port), HealthHandler) as httpd:
                    logger.info(f"🔧 Fallback health server on port {port}")
                    httpd.serve_forever()

            fallback_thread = threading.Thread(target=run_fallback, daemon=True)
            fallback_thread.start()
            await asyncio.sleep(1)

        except Exception as fallback_error:
            logger.error(f"❌ Even fallback server failed: {fallback_error}")


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

        # CRITICAL FOR RENDER: Start web server FIRST for port detection
        if os.getenv('RENDER'):
            logger.info("🔧 Starting web server for Render port detection...")
            asyncio.create_task(start_render_web_server(bot))
            await asyncio.sleep(3)  # Give web server time to bind to port
            logger.info("✅ Web server should be running for Render health checks")

        # Start the Discord bot
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