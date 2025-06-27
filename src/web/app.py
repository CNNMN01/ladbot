"""
Flask Web Dashboard for Ladbot
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
                static_folder='../static')

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('WEB_SECRET_KEY', 'dev-secret-key-change-me')
    app.config['DISCORD_CLIENT_ID'] = os.getenv('DISCORD_CLIENT_ID', '')
    app.config['DISCORD_CLIENT_SECRET'] = os.getenv('DISCORD_CLIENT_SECRET', '')
    app.config['DISCORD_REDIRECT_URI'] = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:8080/callback')

    # Enable CORS for API endpoints
    CORS(app)

    # Store bot reference
    app.bot = bot

    # Register routes
    from .routes import register_routes
    register_routes(app)

    return app


def run_web_server(bot, host='0.0.0.0', port=8080):
    """Run the web server"""
    app = create_app(bot)

    logger.info(f"🌐 Starting web dashboard on http://{host}:{port}")

    try:
        app.run(host=host, port=port, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"❌ Web server error: {e}")