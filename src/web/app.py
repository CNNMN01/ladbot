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
        self.commands_today = 0
        self.total_commands = 0

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
                    'commands_loaded': len(self.bot.commands) if hasattr(self.bot, 'commands') else 0,
                    'cogs_loaded': len(self.bot.cogs) if hasattr(self.bot, 'cogs') else 0
                }

                return jsonify(health_data)

            except Exception as e:
                logger.error(f"Bot health check error: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e)
                }), 500

        @app.route('/api/refresh', methods=['POST'])
        def api_refresh_data():
            """Refresh dashboard data"""
            try:
                stats = self._get_comprehensive_stats()
                return jsonify({
                    'success': True,
                    'data': stats,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/logs')
        def api_get_logs():
            """Get recent logs via API"""
            try:
                log_file = PROJECT_ROOT / 'logs' / 'bot.log'
                if not log_file.exists():
                    return jsonify({'error': 'Log file not found'}), 404

                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Get last 50 lines
                recent_lines = lines[-50:] if len(lines) > 50 else lines

                # Filter sensitive information
                filtered_lines = []
                for line in recent_lines:
                    if any(sensitive in line.lower() for sensitive in ['token', 'secret', 'password']):
                        parts = line.split(' - ')
                        if len(parts) >= 3:
                            filtered_lines.append(f"{parts[0]} - {parts[1]} - [SENSITIVE DATA FILTERED]\n")
                    else:
                        filtered_lines.append(line)

                return jsonify({
                    'logs': filtered_lines,
                    'total_lines': len(lines),
                    'timestamp': datetime.now().isoformat()
                })

            except Exception as e:
                logger.error(f"API logs error: {e}")
                return jsonify({'error': str(e)}), 500

        @app.route('/api/report_error', methods=['POST'])
        def api_report_error():
            """Error reporting endpoint"""
            try:
                error_data = request.get_json()
                logger.error(f"Client error report: {error_data}")

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

        @app.template_filter('format_uptime')
        def format_uptime_filter(seconds):
            try:
                seconds = int(float(seconds))
                days = seconds // 86400
                hours = (seconds % 86400) // 3600
                minutes = (seconds % 3600) // 60

                if days > 0:
                    return f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    return f"{hours}h {minutes}m"
                else:
                    return f"{minutes}m"
            except:
                return 'Unknown'

        # Template global functions
        @app.template_global()
        def now():
            """Current datetime for templates"""
            return datetime.now()

        @app.template_global()
        def utcnow():
            """Current UTC datetime for templates"""
            return datetime.utcnow()

        @app.template_global()
        def moment():
            """Compatibility function for moment.js-like functionality"""

            class MomentLike:
                def __init__(self):
                    self.dt = datetime.now()

                def utc(self):
                    self.dt = datetime.utcnow()
                    return self

                def format(self, fmt):
                    # Convert moment.js format to Python strftime format
                    fmt_map = {
                        'YYYY-MM-DD HH:mm:ss UTC': '%Y-%m-%d %H:%M:%S UTC',
                        'YYYY-MM-DD': '%Y-%m-%d',
                        'YYYY': '%Y',
                        'MM': '%m',
                        'DD': '%d',
                        'HH': '%H',
                        'mm': '%M',
                        'ss': '%S'
                    }
                    python_fmt = fmt_map.get(fmt, fmt)
                    return self.dt.strftime(python_fmt)

            return MomentLike()

        @app.context_processor
        def inject_globals():
            return {
                'bot_name': 'Ladbot',
                'current_year': datetime.now().year,
                'app_version': '2.0',
                'current_time': datetime.now(),
                'current_time_utc': datetime.utcnow(),
                'is_production': settings.IS_PRODUCTION,
                'environment': 'production' if settings.IS_PRODUCTION else 'development',
                'debug_mode': settings.DEBUG,
                'uptime': self._calculate_uptime()
            }

        logger.info("🎨 Template helpers configured")

    def _setup_background_tasks(self, app: Flask) -> None:
        """Setup background tasks and scheduled jobs"""
        # Future: Setup periodic tasks like cache cleanup, analytics aggregation
        logger.info("⚙️ Background tasks configured")

    # ===== DATA MANAGEMENT METHODS =====

    def _get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive bot and system statistics"""
        try:
            stats = {
                'timestamp': datetime.now().isoformat(),
                'uptime': self._calculate_uptime(),
                'version': '2.0',
                'environment': 'production' if settings.IS_PRODUCTION else 'development'
            }

            # Bot statistics
            if self.bot:
                try:
                    stats.update({
                        'bot_status': 'online' if self.bot.is_ready() else 'offline',
                        'guilds': len(self.bot.guilds) if hasattr(self.bot, 'guilds') else 0,
                        'users': len(self.bot.users) if hasattr(self.bot, 'users') else 0,
                        'commands': len(self.bot.commands) if hasattr(self.bot, 'commands') else 0,
                        'latency': round(self.bot.latency * 1000) if hasattr(self.bot, 'latency') else 0,
                        'loaded_cogs': len(self.bot.cogs) if hasattr(self.bot, 'cogs') else 0,
                        'admin_ids': getattr(settings, 'ADMIN_IDS', [])
                    })

                    # Cog status
                    if hasattr(self.bot, 'cogs'):
                        cog_status = {}
                        for cog_name in self.bot.cogs.keys():
                            category = cog_name.lower()
                            if 'admin' in category:
                                cog_status.setdefault('admin', []).append(cog_name)
                            elif any(cat in category for cat in ['entertainment', 'game', 'fun']):
                                cog_status.setdefault('entertainment', []).append(cog_name)
                            elif any(cat in category for cat in ['utility', 'tool']):
                                cog_status.setdefault('utility', []).append(cog_name)
                            elif any(cat in category for cat in ['info', 'information']):
                                cog_status.setdefault('information', []).append(cog_name)
                            else:
                                cog_status.setdefault('other', []).append(cog_name)

                        stats['cog_status'] = cog_status

                except Exception as e:
                    logger.warning(f"Error getting bot stats: {e}")
                    stats['bot_status'] = 'error'
            else:
                stats.update({
                    'bot_status': 'unavailable',
                    'guilds': 0,
                    'users': 0,
                    'commands': 0,
                    'latency': 0,
                    'loaded_cogs': 0
                })

            # System statistics
            try:
                memory = psutil.virtual_memory()
                stats.update({
                    'system': {
                        'cpu_percent': psutil.cpu_percent(),
                        'memory_percent': memory.percent,
                        'memory_used': memory.used,
                        'memory_total': memory.total,
                        'disk_usage': psutil.disk_usage('/').percent
                    },
                    'memory_usage': memory.percent,  # Backwards compatibility
                    'average_latency': stats.get('latency', 0)
                })
            except ImportError:
                stats['system'] = {'error': 'psutil not available'}
                stats['memory_usage'] = 0
                stats['average_latency'] = 0
            except Exception as e:
                logger.warning(f"Error getting system stats: {e}")
                stats['system'] = {'error': str(e)}
                stats['memory_usage'] = 0
                stats['average_latency'] = 0

            # Web statistics
            stats.update({
                'web': {
                    'requests_count': self.request_count,
                    'error_count': self.error_count,
                    'startup_time': self.startup_time.isoformat()
                },
                'error_count': self.error_count,
                'total_commands': self.total_commands,
                'commands_today': self.commands_today
            })

            return stats

        except Exception as e:
            logger.error(f"Error getting comprehensive stats: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'uptime': self._calculate_uptime(),
                'bot_status': 'error',
                'guilds': 0,
                'users': 0,
                'commands': 0,
                'latency': 0,
                'loaded_cogs': 0,
                'memory_usage': 0,
                'error_count': self.error_count,
                'total_commands': 0,
                'commands_today': 0
            }

    def _get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data for dashboard"""
        try:
            # Mock analytics data - replace with actual data tracking
            analytics = {
                'top_commands': [
                    {'name': 'help', 'count': 45},
                    {'name': 'ping', 'count': 32},
                    {'name': 'weather', 'count': 28},
                    {'name': '8ball', 'count': 21},
                    {'name': 'crypto', 'count': 18}
                ],
                'daily_commands': 150,
                'weekly_commands': 980,
                'monthly_commands': 4200,
                'error_rate': 2.1,
                'peak_usage_hour': 20,  # 8 PM
                'most_active_guild': 'Main Server',
                'commands_today': getattr(self, 'commands_today', 0),
                'total_commands': getattr(self, 'total_commands', 0),
                'uptime': self._calculate_uptime(),
                'last_updated': datetime.now().isoformat()
            }

            # Add real data if bot is available
            if self.bot:
                try:
                    analytics.update({
                        'loaded_cogs': len(self.bot.cogs),
                        'total_guilds': len(self.bot.guilds),
                        'total_users': len(self.bot.users),
                        'bot_latency': round(self.bot.latency * 1000) if hasattr(self.bot, 'latency') else 0
                    })
                except:
                    pass

            return analytics

        except Exception as e:
            logger.error(f"Error getting analytics data: {e}")
            return {
                'error': str(e),
                'top_commands': [],
                'daily_commands': 0,
                'weekly_commands': 0,
                'monthly_commands': 0,
                'error_rate': 0,
                'uptime': self._calculate_uptime(),
                'last_updated': datetime.now().isoformat()
            }

    def _get_fallback_stats(self) -> Dict[str, Any]:
        """Get fallback stats when main stats fail"""
        return {
            'bot_status': 'unknown',
            'guilds': 0,
            'users': 0,
            'commands': 0,
            'latency': 0,
            'loaded_cogs': 0,
            'uptime': self._calculate_uptime(),
            'memory_usage': 0,
            'error_count': 0,
            'total_commands': 0,
            'commands_today': 0,
            'average_latency': 0,
            'admin_ids': getattr(settings, 'ADMIN_IDS', []),
            'system': {
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_used': 0,
                'memory_total': 0,
                'disk_usage': 0
            },
            'web': {
                'requests_count': self.request_count,
                'error_count': self.error_count,
                'startup_time': self.startup_time.isoformat()
            },
            'timestamp': datetime.now().isoformat(),
            'version': '2.0',
            'environment': 'production' if settings.IS_PRODUCTION else 'development'
        }

    def _calculate_error_rate(self, error_count: int, total_count: int) -> float:
        """Calculate error rate percentage"""
        try:
            if total_count == 0:
                return 0.0
            return round((error_count / total_count) * 100, 2)
        except:
            return 0.0

    def _calculate_uptime(self) -> str:
        """Calculate uptime string"""
        try:
            uptime_delta = datetime.now() - self.startup_time
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except:
            return "Unknown"

    def _is_admin(self, user_id: int) -> bool:
        """Check if user is an admin"""
        try:
            return user_id in settings.ADMIN_IDS
        except:
            return False

    def _get_bot_settings(self) -> Dict[str, Any]:
        """Get bot settings for display"""
        try:
            if hasattr(self.bot, 'settings'):
                return {
                    'prefix': getattr(settings, 'BOT_PREFIX', 'l.'),
                    'admin_ids': getattr(settings, 'ADMIN_IDS', []),
                    'debug_mode': getattr(settings, 'DEBUG', False),
                    'environment': 'production' if settings.IS_PRODUCTION else 'development'
                }
            return {
                'prefix': settings.BOT_PREFIX,
                'admin_ids': settings.ADMIN_IDS,
                'debug_mode': settings.DEBUG,
                'environment': 'production' if settings.IS_PRODUCTION else 'development'
            }
        except Exception as e:
            logger.error(f"Error getting bot settings: {e}")
            return {}


# ===== PRODUCTION SERVER RUNNER =====

def run_web_server(bot=None, host='0.0.0.0', port=8080, debug=False):
    """Production-ready web server runner"""
    try:
        logger.info("🚀 Ladbot web dashboard startup")

        # Create web application
        web_manager = LadbotWebApp(bot)
        app = web_manager.create_app()

        if settings.IS_PRODUCTION:
            logger.info("🏭 Running in production mode")
            # Use Werkzeug's built-in server with threading
            app.run(
                host=host,
                port=port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
        else:
            logger.info("🔧 Running in development mode")
            app.run(
                host=host,
                port=port,
                debug=debug,
                use_reloader=False  # Disable reloader in bot context
            )

    except Exception as e:
        logger.error(f"❌ Web server failed to start: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def create_app(bot=None):
    """Flask application factory"""
    web_manager = LadbotWebApp(bot)
    return web_manager.create_app()


if __name__ == '__main__':
    # Standalone mode for testing
    print("🚀 Starting Ladbot Web Dashboard in standalone mode...")
    run_web_server(debug=True)