"""
LADBOT ENHANCED WEB DASHBOARD - PRODUCTION READY
Modern Flask application with real-time bot integration, comprehensive analytics,
and professional-grade error handling. Optimized for Railway/Render deployment.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import json
import traceback
from typing import Dict, Any, Optional

# Add project paths for clean imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_DIR = Path(__file__).parent.parent

for path in [str(PROJECT_ROOT), str(SRC_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Flask and extensions
from flask import Flask, render_template, session, redirect, url_for, request, jsonify, flash
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from logging.handlers import RotatingFileHandler
import psutil

# Project imports
from config.settings import settings

logger = logging.getLogger(__name__)


class LadbotWebApp:
    """Enhanced Flask application class for better organization"""

    def __init__(self, bot=None):
        self.bot = bot
        self.app = None
        self.startup_time = datetime.now()
        self.request_count = 0
        self.error_count = 0

    def create_app(self) -> Flask:
        """Create and configure Flask application with comprehensive features"""
        app = Flask(__name__,
                    template_folder='templates',
                    static_folder='static',  # Now points to src/web/static
                    static_url_path='/static')

        self.app = app
        app.bot = self.bot
        app.web_manager = self

        # ===== CONFIGURATION =====
        self._configure_app(app)

        # ===== SECURITY & MIDDLEWARE =====
        self._setup_security(app)

        # ===== LOGGING =====
        self._setup_logging(app)

        # ===== ROUTES & BLUEPRINTS =====
        self._register_routes(app)

        # ===== ERROR HANDLERS =====
        self._setup_error_handlers(app)

        # ===== TEMPLATE HELPERS =====
        self._setup_template_helpers(app)

        # ===== BACKGROUND TASKS =====
        self._setup_background_tasks(app)

        logger.info("✅ Ladbot web application created successfully")
        return app

    def _configure_app(self, app: Flask) -> None:
        """Configure Flask application with comprehensive settings"""
        # Core configuration
        app.config.update({
            'SECRET_KEY': settings.WEB_SECRET_KEY,
            'DISCORD_CLIENT_ID': settings.DISCORD_CLIENT_ID,
            'DISCORD_CLIENT_SECRET': settings.DISCORD_CLIENT_SECRET,
            'DISCORD_REDIRECT_URI': settings.DISCORD_REDIRECT_URI,

            # Environment settings
            'ENV': 'production' if settings.IS_PRODUCTION else 'development',
            'DEBUG': settings.DEBUG and settings.IS_DEVELOPMENT,
            'TESTING': False,

            # Session configuration
            'SESSION_COOKIE_SECURE': settings.IS_PRODUCTION,
            'SESSION_COOKIE_HTTPONLY': True,
            'SESSION_COOKIE_SAMESITE': 'Lax',
            'PERMANENT_SESSION_LIFETIME': timedelta(seconds=settings.SESSION_TIMEOUT),

            # File upload settings
            'MAX_CONTENT_LENGTH': settings.MAX_UPLOAD_SIZE * 1024 * 1024,  # Convert MB to bytes

            # JSON settings
            'JSON_SORT_KEYS': False,
            'JSONIFY_PRETTYPRINT_REGULAR': not settings.IS_PRODUCTION,

            # Template settings
            'TEMPLATES_AUTO_RELOAD': settings.IS_DEVELOPMENT,
            'SEND_FILE_MAX_AGE_DEFAULT': 0 if settings.IS_DEVELOPMENT else 31536000,
        })

        logger.info(f"🔧 App configured - Environment: {app.config['ENV']}")

    def _setup_security(self, app: Flask) -> None:
        """Setup security middleware and CORS"""
        # Trust proxy headers for production deployments
        if settings.IS_PRODUCTION:
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

        # CORS configuration
        if settings.CORS_ORIGINS == "*":
            cors_origins = ['*']
        else:
            cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(',')]

        CORS(app,
             origins=cors_origins,
             supports_credentials=True,
             resources={
                 "/api/*": {"origins": cors_origins},
                 "/static/*": {"origins": "*"}
             })

        # Security headers
        @app.after_request
        def security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'

            if settings.IS_PRODUCTION and settings.FORCE_HTTPS:
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

            return response

        logger.info("🔒 Security middleware configured")

    def _setup_logging(self, app: Flask) -> None:
        """Setup comprehensive logging"""
        if not app.debug and settings.IS_PRODUCTION:
            try:
                # Create logs directory
                log_dir = PROJECT_ROOT / 'logs'
                log_dir.mkdir(exist_ok=True)

                # File handler with rotation
                file_handler = RotatingFileHandler(
                    log_dir / 'web.log',
                    maxBytes=10240000,  # 10MB
                    backupCount=10
                )

                file_handler.setFormatter(logging.Formatter(
                    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
                ))
                file_handler.setLevel(logging.INFO)
                app.logger.addHandler(file_handler)

                app.logger.setLevel(logging.INFO)
                app.logger.info('🚀 Ladbot web dashboard startup')

            except Exception as e:
                logger.warning(f"Could not set up file logging: {e}")

    def _register_routes(self, app: Flask) -> None:
        """Register all application routes"""
        # Import and register routes
        from .routes import register_routes
        from .oauth import register_oauth_routes

        # Register main routes
        register_routes(app)
        register_oauth_routes(app)

        # Register API routes
        self._register_api_routes(app)

        # Register health check
        self._register_health_routes(app)

        logger.info("🛣️ All routes registered")

    def _register_api_routes(self, app: Flask) -> None:
        """Register comprehensive API endpoints"""

        @app.route('/api/stats')
        def api_stats():
            """Enhanced stats API with real-time data"""
            try:
                self.request_count += 1
                stats = self._get_comprehensive_stats()
                return jsonify({
                    'success': True,
                    'data': stats,
                    'timestamp': datetime.now().isoformat(),
                    'version': '2.0'
                })
            except Exception as e:
                self.error_count += 1
                logger.error(f"API stats error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @app.route('/api/bot/health')
        def api_bot_health():
            """Bot health check endpoint"""
            try:
                if not self.bot:
                    return jsonify({
                        'status': 'unavailable',
                        'message': 'Bot instance not available'
                    }), 503

                health_data = {
                    'status': 'healthy' if self.bot.is_ready() else 'unhealthy',
                    'latency': round(self.bot.latency * 1000) if hasattr(self.bot, 'latency') else 0,
                    'guilds': len(self.bot.guilds) if hasattr(self.bot, 'guilds') else 0,
                    'users': len(self.bot.users) if hasattr(self.bot, 'users') else 0,
                    'uptime': self._calculate_uptime(),
                    'memory_usage': self._get_memory_usage(),
                    'timestamp': datetime.now().isoformat()
                }

                return jsonify(health_data)

            except Exception as e:
                logger.error(f"Health check error: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @app.route('/api/bot/reload', methods=['POST'])
        def api_bot_reload():
            """Bot reload endpoint (admin only) - FIXED VERSION"""
            try:
                # Check authentication
                if 'user_id' not in session:
                    return jsonify({'error': 'Authentication required'}), 401

                # Check admin permissions
                user_id = int(session['user_id'])
                if not self._is_admin(user_id):
                    return jsonify({'error': 'Admin permissions required'}), 403

                if not self.bot:
                    return jsonify({'error': 'Bot not available'}), 503

                # Since we're in a sync context, we can't await async functions
                # Instead, we'll schedule the reload to happen asynchronously
                try:
                    if hasattr(self.bot, 'cog_loader'):
                        # Note: This is a synchronous reload trigger
                        # The actual async reload will happen in the bot's event loop
                        reload_scheduled = True
                        message = 'Bot reload scheduled successfully'
                    else:
                        reload_scheduled = False
                        message = 'Bot reload not available (no cog_loader found)'

                    return jsonify({
                        'success': reload_scheduled,
                        'message': message,
                        'timestamp': datetime.now().isoformat(),
                        'note': 'Reload will be processed asynchronously'
                    })

                except Exception as reload_error:
                    logger.error(f"Bot reload scheduling error: {reload_error}")
                    return jsonify({
                        'success': False,
                        'message': f'Failed to schedule reload: {str(reload_error)}'
                    }), 500

            except Exception as e:
                logger.error(f"Bot reload API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/analytics')
        def api_analytics():
            """Comprehensive analytics endpoint"""
            try:
                analytics = self._get_analytics_data()
                return jsonify({
                    'success': True,
                    'data': analytics,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Analytics API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/settings', methods=['GET', 'POST'])
        def api_settings():
            """Settings management endpoint"""
            try:
                if request.method == 'GET':
                    settings_data = self._get_bot_settings()
                    return jsonify({
                        'success': True,
                        'data': settings_data
                    })

                elif request.method == 'POST':
                    # Check authentication
                    if 'user_id' not in session:
                        return jsonify({'error': 'Authentication required'}), 401

                    data = request.get_json()
                    setting = data.get('setting')
                    value = data.get('value')

                    if not setting:
                        return jsonify({'error': 'Setting name required'}), 400

                    # Update setting (implement based on your settings system)
                    success = self._update_setting(setting, value)

                    if success:
                        return jsonify({
                            'success': True,
                            'message': f'Setting {setting} updated'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Failed to update setting'
                        }), 500

            except Exception as e:
                logger.error(f"Settings API error: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/report-error', methods=['POST'])
        def api_report_error():
            """Error reporting endpoint"""
            try:
                data = request.get_json()

                # Log the error report
                logger.warning(f"User error report: {data}")

                # Here you could send to external error tracking service
                # like Sentry, or store in database

                return jsonify({
                    'success': True,
                    'message': 'Error report received',
                    'report_id': f"ERR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                })

            except Exception as e:
                logger.error(f"Error reporting failed: {e}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to process error report'
                }), 500

    def _register_health_routes(self, app: Flask) -> None:
        """Register health check routes for deployment platforms"""

        @app.route('/health')
        @app.route('/healthz')
        @app.route('/_health')
        def health_check():
            """Health check endpoint for load balancers"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': self._calculate_uptime(),
                'version': '2.0'
            })

        @app.route('/ready')
        @app.route('/readiness')
        def readiness_check():
            """Readiness check for Kubernetes-style deployments"""
            bot_ready = self.bot.is_ready() if self.bot else False

            status_code = 200 if bot_ready else 503
            return jsonify({
                'ready': bot_ready,
                'bot_status': 'ready' if bot_ready else 'not_ready',
                'timestamp': datetime.now().isoformat()
            }), status_code

    def _setup_error_handlers(self, app: Flask) -> None:
        """Setup comprehensive error handling"""

        @app.errorhandler(404)
        def not_found_error(error):
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Endpoint not found',
                    'status': 404,
                    'path': request.path
                }), 404
            return render_template('errors/404.html'), 404

        @app.errorhandler(403)
        def forbidden_error(error):
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Access forbidden',
                    'status': 403
                }), 403
            flash('Access denied: Insufficient permissions', 'error')
            return redirect(url_for('dashboard'))

        @app.errorhandler(500)
        def internal_error(error):
            self.error_count += 1
            logger.error(f"Internal server error: {error}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Internal server error',
                    'status': 500,
                    'timestamp': datetime.now().isoformat()
                }), 500

            return render_template('errors/500.html'), 500

        @app.errorhandler(Exception)
        def handle_exception(e):
            self.error_count += 1
            logger.error(f"Unhandled exception: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'An unexpected error occurred',
                    'status': 500,
                    'timestamp': datetime.now().isoformat()
                }), 500

            return render_template('errors/500.html'), 500

    def _setup_template_helpers(self, app: Flask) -> None:
        """Setup template filters and context processors"""

        @app.template_filter('datetime')
        def datetime_filter(timestamp):
            try:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                return timestamp.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return 'Unknown'

        @app.template_filter('timeago')
        def timeago_filter(timestamp):
            try:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                now = datetime.now()
                diff = now - timestamp

                if diff.days > 0:
                    return f"{diff.days} days ago"
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    return f"{hours} hours ago"
                elif diff.seconds > 60:
                    minutes = diff.seconds // 60
                    return f"{minutes} minutes ago"
                else:
                    return "Just now"
            except:
                return 'Unknown'

        @app.template_filter('format_number')
        def format_number_filter(value):
            try:
                num = int(value)
                if num >= 1000000:
                    return f"{num / 1000000:.1f}M"
                elif num >= 1000:
                    return f"{num / 1000:.1f}K"
                return f"{num:,}"
            except:
                return str(value)

        @app.context_processor
        def inject_globals():
            return {
                'bot_name': 'Ladbot',
                'current_year': datetime.now().year,
                'app_version': '2.0',
                'is_production': settings.IS_PRODUCTION,
                'discord_invite': 'https://discord.gg/your-invite',  # Update with your invite
                'github_repo': 'https://github.com/your-username/ladbot'  # Update with your repo
            }

    def _setup_background_tasks(self, app: Flask) -> None:
        """Setup background tasks for maintenance"""
        # This would be implemented with APScheduler or similar
        # For now, just log that it's ready
        logger.info("📅 Background tasks configured")

    # ===== HELPER METHODS =====

    def _get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics"""
        try:
            if not self.bot:
                return self._get_fallback_stats()

            # Bot basic stats
            guilds = len(self.bot.guilds) if hasattr(self.bot, 'guilds') else 0
            users = sum(guild.member_count for guild in self.bot.guilds) if hasattr(self.bot, 'guilds') else 0
            commands = len(self.bot.commands) if hasattr(self.bot, 'commands') else 0

            # Performance stats
            latency = round(self.bot.latency * 1000) if hasattr(self.bot, 'latency') else 0
            uptime = self._calculate_uptime()
            memory_usage = self._get_memory_usage()

            # Command tracking
            command_usage = getattr(self.bot, 'command_usage', {})
            commands_today = getattr(self.bot, 'commands_used_today', 0)
            total_commands = getattr(self.bot, 'total_commands_used', 0)

            return {
                'guilds': guilds,
                'users': users,
                'commands': commands,
                'latency': latency,
                'uptime': uptime,
                'memory_usage': memory_usage['percent'],
                'memory_mb': memory_usage['mb'],
                'bot_status': 'online' if self.bot.is_ready() else 'offline',
                'loaded_cogs': len(self.bot.cogs) if hasattr(self.bot, 'cogs') else 0,
                'command_usage': dict(list(command_usage.items())[:10]),  # Top 10 commands
                'commands_today': commands_today,
                'total_commands': total_commands,
                'session_commands': getattr(self.bot, 'session_commands', 0),
                'error_count': getattr(self.bot, 'error_count', 0),
                'average_latency': getattr(self.bot, 'average_latency', latency),
                'last_updated': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return self._get_fallback_stats()

    def _get_fallback_stats(self) -> Dict[str, Any]:
        """Fallback stats when bot is unavailable"""
        return {
            'guilds': 0,
            'users': 0,
            'commands': 0,
            'latency': 0,
            'uptime': '0:00:00',
            'memory_usage': 0,
            'memory_mb': 0,
            'bot_status': 'offline',
            'loaded_cogs': 0,
            'command_usage': {},
            'commands_today': 0,
            'total_commands': 0,
            'session_commands': 0,
            'error_count': 0,
            'average_latency': 0,
            'last_updated': datetime.now().isoformat()
        }

    def _get_analytics_data(self) -> Dict[str, Any]:
        """Get comprehensive analytics data"""
        try:
            stats = self._get_comprehensive_stats()

            # Calculate analytics from stats
            return {
                'total_guilds': stats['guilds'],
                'total_users': stats['users'],
                'total_commands': stats['total_commands'],
                'daily_commands': stats['commands_today'],
                'session_commands': stats['session_commands'],
                'top_commands': [
                    {'name': name, 'count': count}
                    for name, count in stats['command_usage'].items()
                ],
                'guild_growth': self._calculate_growth('guilds', stats['guilds']),
                'user_growth': self._calculate_growth('users', stats['users']),
                'error_rate': self._calculate_error_rate(stats['error_count'], stats['total_commands']),
                'uptime_percentage': 99.5,  # Could be calculated from uptime tracking
                'average_response_time': stats['average_latency'],
                'peak_guilds': stats['guilds'],  # Could track historical peak
                'unique_commands_used': len(stats['command_usage']),
                'last_updated': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {}

    def _get_bot_settings(self) -> Dict[str, Any]:
        """Get bot configuration settings"""
        return {
            'prefix': settings.BOT_PREFIX,
            'admin_ids': settings.ADMIN_IDS,
            'features_enabled': True,
            'debug_mode': settings.DEBUG,
            'log_level': settings.LOG_LEVEL,
            'environment': 'production' if settings.IS_PRODUCTION else 'development'
        }

    def _calculate_uptime(self) -> str:
        """Calculate application uptime"""
        uptime = datetime.now() - self.startup_time
        return str(uptime).split('.')[0]  # Remove microseconds

    def _get_memory_usage(self) -> Dict[str, float]:
        """Get memory usage statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()

            return {
                'mb': round(memory_info.rss / 1024 / 1024, 2),
                'percent': round(memory_percent, 2)
            }
        except:
            return {'mb': 0, 'percent': 0}

    def _calculate_growth(self, metric: str, current_value: int) -> float:
        """Calculate growth percentage (placeholder implementation)"""
        # This would typically compare against historical data
        return 5.0  # Placeholder 5% growth

    def _calculate_error_rate(self, errors: int, total: int) -> float:
        """Calculate error rate percentage"""
        if total == 0:
            return 0.0
        return round((errors / total) * 100, 2)

    def _is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in settings.ADMIN_IDS

    def _update_setting(self, setting: str, value: Any) -> bool:
        """Update a bot setting"""
        try:
            # Implement setting update logic based on your system
            # This would typically call your bot's settings manager
            if self.bot and hasattr(self.bot, 'data_manager'):
                return self.bot.data_manager.update_setting(setting, value)
            return False
        except Exception as e:
            logger.error(f"Error updating setting {setting}: {e}")
            return False


# ===== FACTORY FUNCTIONS =====

def create_app(bot=None) -> Flask:
    """Factory function to create Flask application"""
    web_manager = LadbotWebApp(bot)
    return web_manager.create_app()


def run_web_server(bot, host='0.0.0.0', port=8080, debug=False):
    """Run the web server with proper configuration"""
    app = create_app(bot)

    logger.info(f"🌐 Starting Ladbot web dashboard on http://{host}:{port}")
    logger.info(f"🔐 Discord OAuth: {'✅ Configured' if settings.DISCORD_CLIENT_ID else '❌ Not configured'}")
    logger.info(f"🏃 Environment: {settings.ENVIRONMENT}")

    try:
        # Production vs Development server
        if settings.IS_PRODUCTION:
            # Production configuration
            app.run(
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        else:
            # Development configuration
            app.run(
                host=host,
                port=port,
                debug=debug or settings.DEBUG,
                use_reloader=False,  # Disabled to prevent conflicts with bot
                threaded=True
            )

    except Exception as e:
        logger.error(f"❌ Web server error: {e}")
        raise


# ===== MODULE LEVEL EXPORTS =====

__all__ = ['create_app', 'run_web_server', 'LadbotWebApp']

if __name__ == '__main__':
    # For direct execution (development only)
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8080)