"""
Fixed Flask routes for Ladbot web dashboard
"""
from flask import render_template, session, redirect, url_for, request, jsonify, flash
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all routes with the Flask app"""

    @app.route('/')
    def index():
        """Home page - redirect to dashboard or login"""
        if 'user' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login')
    def login():
        """Login page"""
        return render_template('login.html')

    @app.route('/dashboard')
    def dashboard():
        """Main dashboard page"""
        # Get bot stats safely
        bot = app.bot
        stats = {}

        try:
            if bot and bot.is_ready():
                stats = {
                    'guilds': len(bot.guilds),
                    'users': len(bot.users),
                    'commands': len(bot.commands),
                    'latency': round(bot.latency * 1000),
                    'uptime': str(datetime.now() - bot.start_time).split('.')[0],
                    'loaded_cogs': len(bot.cogs),
                    'commands_today': getattr(bot, 'commands_used_today', 0),
                    'error_count': getattr(bot, 'error_count', 0)
                }
            else:
                # Default stats if bot not ready
                stats = {
                    'guilds': 0,
                    'users': 0,
                    'commands': 0,
                    'latency': 0,
                    'uptime': 'Starting...',
                    'loaded_cogs': 0,
                    'commands_today': 0,
                    'error_count': 0
                }
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            stats = {
                'guilds': 0,
                'users': 0,
                'commands': 0,
                'latency': 0,
                'uptime': 'Error',
                'loaded_cogs': 0,
                'commands_today': 0,
                'error_count': 0
            }

        return render_template('dashboard.html',
                               stats=stats,
                               bot_stats=stats,  # Alias for template compatibility
                               user=session.get('user'))

    @app.route('/analytics')
    def analytics():
        """Analytics page"""
        bot = app.bot
        analytics_data = {}

        try:
            if bot and bot.is_ready():
                analytics_data = {
                    'total_guilds': len(bot.guilds),
                    'total_users': len(bot.users),
                    'total_commands': len(bot.commands),
                    'bot_latency': round(bot.latency * 1000),
                    'uptime': str(datetime.now() - bot.start_time).split('.')[0],
                    'loaded_cogs': len(bot.cogs),
                    'command_stats': {},
                    'guild_data': [],
                    'usage_trends': []
                }
            else:
                analytics_data = {
                    'total_guilds': 0,
                    'total_users': 0,
                    'total_commands': 0,
                    'bot_latency': 0,
                    'uptime': 'Starting...',
                    'loaded_cogs': 0,
                    'command_stats': {},
                    'guild_data': [],
                    'usage_trends': []
                }
        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            analytics_data = {
                'total_guilds': 0,
                'total_users': 0,
                'total_commands': 0,
                'bot_latency': 0,
                'uptime': 'Error',
                'loaded_cogs': 0,
                'command_stats': {},
                'guild_data': [],
                'usage_trends': []
            }

        return render_template('analytics.html',
                               analytics=analytics_data,
                               user=session.get('user'))

    @app.route('/api/stats')
    def api_stats():
        """API endpoint for real-time stats"""
        bot = app.bot

        try:
            if bot and bot.is_ready():
                stats = {
                    'guilds': len(bot.guilds),
                    'users': len(bot.users),
                    'commands': len(bot.commands),
                    'latency': round(bot.latency * 1000),
                    'uptime': str(datetime.now() - bot.start_time).split('.')[0],
                    'loaded_cogs': len(bot.cogs),
                    'status': 'online'
                }
            else:
                stats = {
                    'guilds': 0,
                    'users': 0,
                    'commands': 0,
                    'latency': 0,
                    'uptime': 'Starting...',
                    'loaded_cogs': 0,
                    'status': 'starting'
                }
        except Exception as e:
            logger.error(f"Error in API stats: {e}")
            stats = {
                'error': str(e),
                'status': 'error'
            }

        return jsonify(stats)

    @app.route('/health')
    def health():
        """Health check endpoint for Render"""
        bot = app.bot

        try:
            if bot and bot.is_ready():
                return jsonify({
                    'status': 'healthy',
                    'bot_status': 'online',
                    'guilds': len(bot.guilds),
                    'timestamp': datetime.now().isoformat(),
                    'version': '2.0.0'
                })
            else:
                return jsonify({
                    'status': 'starting',
                    'bot_status': 'connecting',
                    'timestamp': datetime.now().isoformat(),
                    'version': '2.0.0'
                }), 503
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/demo-login')
    def demo_login():
        """Demo login for testing (development only)"""
        if app.debug or app.config.get('DEVELOPMENT'):
            session['user'] = {
                'id': '123456789',
                'username': 'Demo User',
                'discriminator': '0001',
                'avatar': None
            }
            session['user_id'] = '123456789'
            flash('Demo login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            return "Demo login disabled in production", 403

    @app.route('/logout')
    def logout():
        """Logout and clear session"""
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return jsonify({
            'error': 'Page not found',
            'status': 404
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        return jsonify({
            'error': 'Internal server error',
            'status': 500
        }), 500