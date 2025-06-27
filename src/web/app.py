"""
Flask Web Dashboard for Ladbot - Production Ready
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
    """Create Flask application"""
    app = Flask(__name__,
                template_folder='templates',
                static_folder='../../static')

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
    else:
        app.config['ENV'] = 'development'
        app.config['DEBUG'] = settings.DEBUG
        app.config['DEVELOPMENT'] = True

    # Enable CORS for API endpoints
    CORS(app, origins=['*'] if settings.IS_DEVELOPMENT else [settings.DISCORD_REDIRECT_URI.split('/callback')[0]])

    # Store bot reference
    app.bot = bot

    # Register routes
    from .routes import register_routes
    register_routes(app)

    # Add error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html',
                             error_code=404,
                             error_message="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html',
                             error_code=500,
                             error_message="Internal server error"), 500

    return app


def run_web_server(bot, host='0.0.0.0', port=8080):
    """Run the web server"""
    app = create_app(bot)

    logger.info(f"🌐 Starting web dashboard on http://{host}:{port}")

    # Log OAuth configuration
    if app.config['DISCORD_CLIENT_ID']:
        logger.info(f"🔐 Discord OAuth configured - Redirect: {app.config['DISCORD_REDIRECT_URI']}")
    else:
        logger.warning("⚠️ Discord OAuth not configured - web features limited")

    try:
        # Use appropriate server for environment
        if os.getenv('RENDER'):
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