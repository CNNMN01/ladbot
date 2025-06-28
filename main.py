#!/usr/bin/env python3
"""
Ladbot Enhanced - Universal Entry Point (Render & Railway Compatible)
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
    """Setup logging configuration for cloud platforms"""
    try:
        from config.settings import settings

        # Create logs directory if it doesn't exist
        try:
            settings.LOGS_DIR.mkdir(exist_ok=True)
        except (PermissionError, OSError):
            # Cloud platforms might not allow file creation
            pass

        # Configure logging
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        # Always log to stdout for cloud platforms
        handlers = [logging.StreamHandler(sys.stdout)]

        # Try to add file logging if possible
        try:
            if settings.LOGS_DIR.exists():
                handlers.append(logging.FileHandler(settings.LOGS_DIR / "bot.log"))
        except (PermissionError, OSError):
            # File logging not available, just use stdout
            pass

        logging.basicConfig(
            level=getattr(logging, settings.LOG_LEVEL),
            format=log_format,
            handlers=handlers
        )

        # Reduce Discord.py noise
        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)

    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def get_port():
    """Get port from environment (works for both Render and Railway)"""
    return int(os.environ.get('PORT', 8080))


def get_host():
    """Get host for web server"""
    return '0.0.0.0'


def detect_platform():
    """Detect which platform we're running on"""
    if os.getenv('RENDER'):
        return 'render'
    elif os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID'):
        return 'railway'
    else:
        return 'local'


async def start_web_server(bot):
    """Start web server compatible with Render and Railway"""
    port = get_port()
    host = get_host()
    platform = detect_platform()

    logger = logging.getLogger(__name__)
    logger.info(f"🌐 Starting web server on {platform} - {host}:{port}")

    try:
        # Try to import full web dashboard first
        try:
            from web.app import create_app
            app = create_app(bot)
            logger.info("✅ Full web dashboard loaded")
            use_full_app = True
        except ImportError as e:
            logger.warning(f"⚠️ Full web dashboard not available: {e}")
            use_full_app = False

        # Create Flask app (full or fallback)
        if use_full_app:
            # Use the full web dashboard - don't add duplicate routes
            logger.info("🎯 Using existing web dashboard routes")
        else:
            # Create minimal Flask app for platform requirements
            from flask import Flask, jsonify, render_template_string
            app = Flask(__name__)

            @app.route('/')
            def home():
                return render_template_string("""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Ladbot Dashboard</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                        .container { max-width: 600px; margin: 0 auto; }
                        .status { color: #28a745; font-size: 24px; margin: 20px 0; }
                        .info { background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🤖 Ladbot Dashboard</h1>
                        <div class="status">✅ Bot is Online!</div>
                        <div class="info">
                            <h3>Bot Statistics</h3>
                            <p><strong>Guilds:</strong> {{ guilds }}</p>
                            <p><strong>Users:</strong> {{ users }}</p>
                            <p><strong>Commands:</strong> {{ commands }}</p>
                            <p><strong>Platform:</strong> {{ platform }}</p>
                        </div>
                        <div class="info">
                            <h3>Available Commands</h3>
                            <p>Try <code>l.help</code> in Discord to see all commands!</p>
                        </div>
                    </div>
                </body>
                </html>
                """,
                                              guilds=len(bot.guilds) if hasattr(bot, 'guilds') else 0,
                                              users=len(bot.users) if hasattr(bot, 'users') else 0,
                                              commands=len(bot.commands) if hasattr(bot, 'commands') else 0,
                                              platform=platform.title()
                                              )

            @app.route('/health')
            def health():
                """Health check endpoint for platform monitoring"""
                return jsonify({
                    "status": "healthy",
                    "bot_name": "Ladbot",
                    "platform": platform,
                    "guilds": len(bot.guilds) if hasattr(bot, 'guilds') else 0,
                    "users": len(bot.users) if hasattr(bot, 'users') else 0,
                    "commands": len(bot.commands) if hasattr(bot, 'commands') else 0,
                    "timestamp": datetime.now().isoformat(),
                    "bot_online": hasattr(bot, 'is_ready') and bot.is_ready()
                }), 200

            @app.route('/ping')
            def ping():
                """Simple ping endpoint"""
                return "pong", 200

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
        await asyncio.sleep(3)

        logger.info(f"✅ Web server accessible on port {port}")
        logger.info(f"🔗 Platform: {platform}")

        if platform == 'render':
            logger.info(f"🌍 Render URL: https://{os.getenv('RENDER_EXTERNAL_URL', 'your-app.onrender.com')}")
        elif platform == 'railway':
            logger.info(f"🚂 Railway URL: https://web-production-701c.up.railway.app")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Failed to start web server: {e}")
        logger.exception("Full traceback:")

        # Create absolute minimal fallback server
        try:
            import http.server
            import socketserver

            class MinimalHandler(http.server.SimpleHTTPRequestHandler):
                def do_GET(self):
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(b"Ladbot Health Check OK")

                def log_message(self, format, *args):
                    pass  # Suppress logs

            def run_fallback():
                with socketserver.TCPServer(("", port), MinimalHandler) as httpd:
                    logger.info(f"🔧 Fallback server on port {port}")
                    httpd.serve_forever()

            fallback_thread = threading.Thread(target=run_fallback, daemon=True)
            fallback_thread.start()
            await asyncio.sleep(1)

        except Exception as fallback_error:
            logger.error(f"❌ Even fallback server failed: {fallback_error}")


async def main():
    """Main application entry point"""
    logger = logging.getLogger(__name__)
    platform = detect_platform()

    try:
        logger.info("🚀 Starting Ladbot Enhanced...")
        logger.info(f"📅 Started at: {datetime.now()}")
        logger.info(f"🌍 Platform: {platform.title()}")

        # Load environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv()
            logger.info("✅ Environment loaded")
        except ImportError:
            logger.info("python-dotenv not installed, using system environment")

        setup_logging()

        # Validate configuration
        from config.settings import settings
        logger.info("✅ Configuration validated")

        # Log deployment info
        port = get_port()
        host = get_host()
        logger.info(f"🌐 Web server will run on {host}:{port}")

        # Platform-specific logging
        if platform == 'render':
            logger.info(f"🔗 Render deployment detected")
            if os.getenv('RENDER_EXTERNAL_URL'):
                logger.info(f"🌍 Public URL: {os.getenv('RENDER_EXTERNAL_URL')}")
        elif platform == 'railway':
            logger.info(f"🚂 Railway deployment detected")
            logger.info(f"🌍 Public URL: https://web-production-701c.up.railway.app")

        # Import and start bot
        from bot.ladbot import LadBot

        logger.info("🤖 Starting Discord bot...")
        bot = LadBot()

        # Configure for platform
        bot.web_port = port
        bot.web_host = host

        # Set production URL based on platform
        if platform == 'render' and os.getenv('RENDER_EXTERNAL_URL'):
            bot.web_url = os.getenv('RENDER_EXTERNAL_URL')
        elif platform == 'railway':
            bot.web_url = "https://web-production-701c.up.railway.app"

        # Start web server for platform requirements
        if platform in ['render', 'railway']:
            logger.info("🔧 Starting web server for platform health checks...")
            asyncio.create_task(start_web_server(bot))
            await asyncio.sleep(4)  # Give web server time to bind
            logger.info("✅ Web server should be running for platform health checks")

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