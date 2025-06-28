"""
Enhanced Flask Web Dashboard for Ladbot - Production Ready
"""
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask, render_template, session, redirect, url_for, request, jsonify, flash
from flask_cors import CORS
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


def create_app(bot=None):
    """Create Flask application with comprehensive configuration"""
    app = Flask(__name__,
                template_folder='templates',
                static_folder=str(Path(__file__).parent.parent.parent / 'static'))

    # Configuration
    from config.settings import settings

    app.config['SECRET_KEY'] = settings.WEB_SECRET_KEY
    app.config['DISCORD_CLIENT_ID'] = settings.DISCORD_CLIENT_ID
    app.config['DISCORD_CLIENT_SECRET'] = settings.DISCORD_CLIENT_SECRET
    app.config['DISCORD_REDIRECT_URI'] = settings.DISCORD_REDIRECT_URI

    # Production settings
    if settings.IS_PRODUCTION:
        app.config['ENV'] = 'production'
        app.config['DEBUG'] = False
        app.config['DEVELOPMENT'] = False
        app.config['TESTING'] = False
    else:
        app.config['ENV'] = 'development'
        app.config['DEBUG'] = settings.DEBUG
        app.config['DEVELOPMENT'] = True

    # Security settings
    app.config['SESSION_COOKIE_SECURE'] = settings.IS_PRODUCTION
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Enable CORS for API endpoints
    cors_origins = ['*'] if settings.IS_DEVELOPMENT else [
        settings.DISCORD_REDIRECT_URI.split('/callback')[0]
    ]
    CORS(app, origins=cors_origins, supports_credentials=True)

    # Store bot reference
    app.bot = bot

    # Register routes
    from .routes import register_routes
    register_routes(app)

    # Add template context processors
    @app.context_processor
    def inject_config():
        """Make config and utility functions available in templates"""
        return {
            'config': app.config,
            'now': datetime.now(),
            'bot': app.bot
        }

    @app.context_processor
    def inject_user_info():
        """Inject user information into templates"""
        user_info = {
            'is_authenticated': 'user_id' in session,
            'user': session.get('user', {}),
            'is_admin': False
        }

        # Check if user is admin
        if user_info['is_authenticated']:
            try:
                admin_ids_str = os.getenv('ADMIN_IDS', '')
                if admin_ids_str:
                    admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
                    user_info['is_admin'] = int(session.get('user_id', 0)) in admin_ids
            except Exception:
                pass

        return user_info

    # Add custom Jinja2 filters
    @app.template_filter('format_number')
    def format_number(value):
        """Format numbers with commas"""
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return value

    @app.template_filter('format_percentage')
    def format_percentage(value):
        """Format percentage values"""
        try:
            return f"{float(value):.1f}%"
        except (ValueError, TypeError):
            return f"{value}%"

    @app.template_filter('truncate_text')
    def truncate_text(text, length=50):
        """Truncate text to specified length"""
        try:
            if len(text) <= length:
                return text
            return text[:length] + '...'
        except (TypeError, AttributeError):
            return text

    # Logging configuration
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler

        # Create logs directory if it doesn't exist
        try:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)

            file_handler = RotatingFileHandler(
                'logs/web.log',
                maxBytes=10240000,
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info('Web dashboard startup')
        except Exception as e:
            logger.warning(f"Could not set up file logging: {e}")

    return app


def run_web_server(bot, host='0.0.0.0', port=8080):
    """Run the web server with proper configuration"""
    app = create_app(bot)

    logger.info(f"🌐 Starting web dashboard on http://{host}:{port}")

    # Log OAuth configuration status
    if app.config['DISCORD_CLIENT_ID']:
        logger.info(f"🔐 Discord OAuth configured")
        logger.info(f"📍 Redirect URI: {app.config['DISCORD_REDIRECT_URI']}")
    else:
        logger.warning("⚠️ Discord OAuth not configured - web features limited")

    # Log environment
    logger.info(f"🏃 Environment: {app.config['ENV']}")
    logger.info(f"🔧 Debug mode: {app.config['DEBUG']}")

    try:
        # Use appropriate server for environment
        if os.getenv('RENDER') or os.getenv('RAILWAY_ENVIRONMENT'):
            # Production server
            app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        else:
            # Development server
            app.run(
                host=host,
                port=port,
                debug=app.config['DEBUG'],
                use_reloader=False,
                threaded=True
            )
    except Exception as e:
        logger.error(f"❌ Web server error: {e}")
        raise