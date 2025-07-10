"""
Enhanced Routes for Ladbot Web Dashboard - Production Ready
Complete integration with new app.py structure and real-time bot data
FIXED: All async event loop issues resolved and syntax errors corrected
"""

from flask import render_template, session, redirect, url_for, request, jsonify, flash, current_app
import logging
from datetime import datetime, timedelta
import traceback
from typing import Dict, Any, Optional, List
import json
from pathlib import Path
from utils.database import db_manager
import asyncio
import concurrent.futures

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all main web routes with comprehensive functionality"""

    # ===== UTILITY FUNCTIONS =====

    def require_auth() -> bool:
        """Check if user is authenticated"""
        return 'user_id' in session

    def require_admin() -> bool:
        """Check if current user is admin"""
        if not require_auth():
            return False

        user_id = int(session['user_id'])
        return app.web_manager._is_admin(user_id)

    def require_guild_admin(guild_id: int) -> bool:
        """Check if user can manage a specific guild"""
        if not require_auth():
            return False

        if require_admin():  # Global admins can manage any guild
            return True

        user_id = int(session['user_id'])

        if not app.bot:
            return False

        guild = app.bot.get_guild(guild_id)
        if not guild:
            return False

        member = guild.get_member(user_id)
        if not member:
            return False

        # Allow if user is server admin or owner
        return (member.guild_permissions.administrator or
                guild.owner_id == user_id)

    def get_user_guilds() -> List[Dict]:
        """Get guilds where user has admin permissions"""
        if not require_auth() or not app.bot:
            return []

        user_id = int(session['user_id'])
        user_guilds = []
        is_global_admin = session.get('is_admin', False)

        try:
            # Import settings to get admin IDs
            from config.settings import settings

            for guild in app.bot.guilds:
                try:
                    member = guild.get_member(user_id)
                    if not member:
                        continue

                    # Check if user has admin permissions
                    has_access = (
                            is_global_admin or
                            member.guild_permissions.administrator or
                            guild.owner_id == user_id
                    )

                    if has_access:
                        user_guilds.append({
                            'id': str(guild.id),
                            'name': guild.name,
                            'icon': guild.icon.url if guild.icon else None,
                            'member_count': guild.member_count,
                            'owner': guild.owner_id == user_id,
                            'permissions': {
                                'administrator': member.guild_permissions.administrator,
                                'manage_guild': member.guild_permissions.manage_guild,
                                'manage_channels': member.guild_permissions.manage_channels
                            }
                        })
                except Exception as e:
                    logger.warning(f"Error processing guild {guild.id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error getting user guilds: {e}")

        return user_guilds

    def log_page_view(page_name: str):
        """Log page view for analytics"""
        try:
            app.web_manager.request_count += 1
            logger.debug(f"Page view: {page_name} by user {session.get('user_id', 'anonymous')}")
        except:
            pass

    def run_async_in_bot_loop(coro):
        """Run async function in bot's event loop - FIXED VERSION"""
        if not app.bot or not hasattr(app.bot, 'loop'):
            raise Exception("Bot not available or no event loop")

        loop = app.bot.loop
        if not loop.is_running():
            raise Exception("Bot event loop not running")

        future = concurrent.futures.Future()

        def set_result(task):
            if task.exception():
                future.set_exception(task.exception())
            else:
                future.set_result(task.result())

        task = asyncio.run_coroutine_threadsafe(coro, loop)
        task.add_done_callback(set_result)

        return future.result(timeout=15)  # 15 second timeout

    # ===== MAIN ROUTES =====

    @app.route('/')
    def index():
        """Enhanced home page with dynamic data"""
        log_page_view('index')

        try:
            stats = app.web_manager._get_comprehensive_stats()
            recent_activity = app.web_manager._get_recent_activity()
            system_health = app.web_manager._get_system_health()

            return render_template('index.html',
                                   stats=stats,
                                   recent_activity=recent_activity,
                                   system_health=system_health,
                                   user=session.get('user'),
                                   page_title='Home')

        except Exception as e:
            logger.error(f"Index page error: {e}")
            # Fallback with basic stats
            return render_template('index.html',
                                   stats=app.web_manager._get_fallback_stats(),
                                   recent_activity=[],
                                   system_health={},
                                   user=session.get('user'),
                                   page_title='Home')

    @app.route('/dashboard')
    def dashboard():
        """Enhanced main dashboard with comprehensive data"""
        log_page_view('dashboard')

        if not require_auth():
            flash('Please log in to access the dashboard', 'warning')
            return redirect(url_for('login'))

        try:
            # Get comprehensive data
            stats = app.web_manager._get_comprehensive_stats()
            analytics = app.web_manager._get_analytics_data()
            settings_data = app.web_manager._get_bot_settings()

            # Get user-specific data
            user_guilds = get_user_guilds()
            is_admin = require_admin()

            # Debug logging
            logger.info(
                f"Dashboard access - User: {session.get('user_id')}, Admin: {is_admin}, "
                f"Guilds: {len(user_guilds)}")

            return render_template('dashboard.html',
                                   stats=stats,
                                   analytics=analytics,
                                   settings=settings_data,
                                   user=session.get('user'),
                                   user_guilds=user_guilds,
                                   guilds=user_guilds,  # Added for template compatibility
                                   is_admin=is_admin,
                                   recent_activity=app.web_manager._get_recent_activity(),
                                   system_health=app.web_manager._get_system_health(),
                                   page_title='Dashboard')

        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            flash('Some information may be unavailable.', 'warning')
            return render_template('dashboard.html',
                                   stats=app.web_manager._get_fallback_stats(),
                                   analytics={},
                                   settings={},
                                   user=session.get('user'),
                                   user_guilds=[],
                                   guilds=[],  # Added for template compatibility
                                   is_admin=False,
                                   recent_activity=[],
                                   system_health={},
                                   page_title='Dashboard')

    @app.route('/login')
    def login():
        """Enhanced login page"""
        log_page_view('login')

        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        # Check if OAuth is configured
        oauth_configured = bool(app.config.get('DISCORD_CLIENT_ID') and
                                app.config.get('DISCORD_CLIENT_SECRET'))

        if not oauth_configured:
            flash('Discord OAuth is not configured. Please contact the administrator.', 'error')

        return render_template('login.html',
                               oauth_configured=oauth_configured,
                               redirect_uri=app.config.get('DISCORD_REDIRECT_URI'),
                               page_title='Login')

    @app.route('/logout')
    def logout():
        """Enhanced logout with cleanup"""
        log_page_view('logout')

        username = session.get('user', {}).get('username', 'User')
        session.clear()

        flash(f'Goodbye, {username}! You have been logged out successfully.', 'success')
        return redirect(url_for('index'))

    @app.route('/settings')
    def settings():
        """Enhanced settings page with live data"""
        log_page_view('settings')

        if not require_auth():
            return redirect(url_for('login'))

        try:
            stats = app.web_manager._get_comprehensive_stats()
            settings_data = app.web_manager._get_bot_settings()
            user_guilds = get_user_guilds()
            is_admin = require_admin()

            # Available settings categories
            setting_categories = {
                'general': {
                    'name': 'General Settings',
                    'description': 'Basic bot configuration',
                    'settings': [
                        {'key': 'prefix', 'name': 'Command Prefix', 'type': 'text',
                         'value': settings_data.get('prefix', 'l.')},
                        {'key': 'debug_mode', 'name': 'Debug Mode', 'type': 'boolean',
                         'value': settings_data.get('debug_mode', False)},
                        {'key': 'log_level', 'name': 'Log Level', 'type': 'select',
                         'options': ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                         'value': settings_data.get('log_level', 'INFO')}
                    ]
                },
                'features': {
                    'name': 'Feature Control',
                    'description': 'Enable or disable bot features',
                    'settings': [
                        {'key': 'weather_enabled', 'name': 'Weather Commands', 'type': 'boolean',
                         'value': settings_data.get('weather_enabled', True)},
                        {'key': 'crypto_enabled', 'name': 'Cryptocurrency Commands', 'type': 'boolean',
                         'value': settings_data.get('crypto_enabled', True)},
                        {'key': 'games_enabled', 'name': 'Game Commands', 'type': 'boolean',
                         'value': settings_data.get('games_enabled', True)}
                    ]
                }
            }

            return render_template('settings.html',
                                   stats=stats,
                                   settings=settings_data,
                                   setting_categories=setting_categories,
                                   user=session.get('user'),
                                   user_guilds=user_guilds,
                                   guilds=user_guilds,  # Added for template compatibility
                                   is_admin=is_admin,
                                   page_title='Settings')

        except Exception as e:
            logger.error(f"Settings page error: {e}")
            flash('Error loading settings page', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/guild/<int:guild_id>/settings')
    def guild_settings(guild_id):
        """Guild-specific settings page - FIXED DATABASE VERSION"""
        log_page_view('guild_settings')

        if not require_auth():
            return redirect(url_for('login'))

        try:
            # Check if user has access to this guild
            user_guilds = get_user_guilds()
            guild_data = None

            for guild in user_guilds:
                if int(guild['id']) == guild_id:
                    guild_data = guild
                    break

            if not guild_data:
                flash('Access denied: You do not have permissions for this server', 'error')
                return redirect(url_for('dashboard'))

            # Get current settings from database using bot's event loop
            async def get_guild_settings():
                return await db_manager.get_all_guild_settings(guild_id)

            try:
                current_settings = run_async_in_bot_loop(get_guild_settings())
            except Exception as e:
                logger.error(f"Error getting guild settings: {e}")
                current_settings = {}

            # Provide defaults for missing settings
            default_settings = {
                'prefix': 'l.',
                'autoresponses': True,
                'weather': True,
                'crypto': True,
                'games': True,
                'reddit': True,
                'help': True,
                'ping': True,
                'info': True,
                'jokes': True,
                'roll': True,
                'eightball': True,
                'bible': True,
                'feedback': True,
                'tools': True,
                'ascii_art': True,
                'dinosaurs': True,
                'welcome_messages': True,
                'moderation_enabled': True,
                'spam_protection': True,
                'auto_delete_commands': False,
                'logging_enabled': True,
                'command_cooldown': 3,
                'embed_color': '#4e73df'
            }

            # Merge with defaults
            for key, default_value in default_settings.items():
                if key not in current_settings:
                    current_settings[key] = default_value

            return render_template('guild_settings.html',
                                   guild=guild_data,
                                   settings=current_settings,
                                   user=session.get('user'),
                                   page_title=f'{guild_data["name"]} Settings')

        except Exception as e:
            logger.error(f"Guild settings page error: {e}")
            flash('Error loading guild settings', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/about')
    def about():
        """Enhanced about page with dynamic bot information"""
        log_page_view('about')

        try:
            stats = app.web_manager._get_comprehensive_stats()

            # Bot information
            bot_info = {
                'name': 'Ladbot',
                'version': '2.0',
                'description': 'A comprehensive Discord bot with web dashboard',
                'author': 'Ladbot Development Team',
                'guilds': stats.get('guilds', 0),
                'users': stats.get('users', 0),
                'commands': stats.get('commands_available', 0),
                'uptime': stats.get('uptime', 'Unknown'),
                'features': [
                    'Web Dashboard',
                    'Real-time Analytics',
                    'Weather Commands',
                    'Cryptocurrency Tracking',
                    'Interactive Games',
                    'Moderation Tools',
                    'Custom Settings',
                    'API Integration'
                ],
                'tech_stack': [
                    'Python 3.8+',
                    'discord.py',
                    'Flask',
                    'Bootstrap 5',
                    'Chart.js'
                ]
            }

            return render_template('about.html',
                                   bot=bot_info,
                                   user=session.get('user'),
                                   page_title='About')

        except Exception as e:
            logger.error(f"About page error: {e}")
            return render_template('about.html',
                                   bot={'name': 'Ladbot', 'version': '2.0'},
                                   user=session.get('user'),
                                   page_title='About')

    # ===== API ROUTES =====

    @app.route('/api/dashboard/refresh')
    def refresh_dashboard_data():
        """Refresh dashboard data (AJAX endpoint)"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        try:
            stats = app.web_manager._get_comprehensive_stats()
            return jsonify({
                'success': True,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Dashboard refresh error: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/settings/update', methods=['POST'])
    def update_settings():
        """Update bot settings via API - FIXED VERSION"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        try:
            settings_data = request.get_json()
            guild_id = settings_data.get('guild_id')
            settings = settings_data.get('settings', {})

            if not guild_id:
                return jsonify({'error': 'Guild ID required'}), 400

            if not require_guild_admin(guild_id):
                return jsonify({'error': 'Access denied'}), 403

            # FIXED: Use the bot's event loop
            async def save_all_settings():
                success_count = 0
                total_count = len(settings)

                for setting_name, value in settings.items():
                    success = await db_manager.set_guild_setting(guild_id, setting_name, value)
                    if success:
                        success_count += 1
                        logger.info(f"✅ WEB: Set {setting_name}={value} for guild {guild_id}")
                    else:
                        logger.error(f"❌ WEB: Failed to set {setting_name} for guild {guild_id}")

                return success_count, total_count

            success_count, total_count = run_async_in_bot_loop(save_all_settings())

            if success_count == total_count:
                logger.info(f"🌐 WEB DASHBOARD: Updated {success_count}/{total_count} settings for guild {guild_id}")
                return jsonify({
                    'success': True,
                    'message': f'Updated {success_count} settings successfully',
                    'settings_applied': success_count,
                    'total_settings': total_count,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Only {success_count}/{total_count} settings updated successfully',
                    'settings_applied': success_count,
                    'total_settings': total_count
                }), 500

        except Exception as e:
            logger.error(f"Settings update error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    @app.route('/api/debug/settings/<int:guild_id>')
    def debug_guild_settings(guild_id):
        """Debug endpoint to check guild settings in database - FIXED VERSION"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        try:
            # FIXED: Use bot's event loop
            async def get_settings():
                return await db_manager.get_all_guild_settings(guild_id)

            settings = run_async_in_bot_loop(get_settings())

            return jsonify({
                'guild_id': guild_id,
                'settings_in_database': settings,
                'database_type': 'sqlite' if db_manager.use_sqlite else 'postgresql',
                'database_ready': db_manager.connection_healthy,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Debug endpoint error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/test-database')
    def test_database():
        """Test database connection and operations - FIXED VERSION"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        try:
            # FIXED: Use bot's event loop instead of creating new one
            async def test_operations():
                # Test connection and basic operations
                health = await db_manager.health_check()

                # Test write/read cycle
                test_guild_id = 999999999  # Test guild ID
                write_success = await db_manager.set_guild_setting(test_guild_id, 'test_setting', True)
                read_value = await db_manager.get_guild_setting(test_guild_id, 'test_setting', False)

                # Cleanup (removed delete_guild_settings to avoid errors)
                # await db_manager.delete_guild_settings(test_guild_id)

                return {
                    'health': health,
                    'write_success': write_success,
                    'read_value': read_value,
                    'connection_info': db_manager.get_connection_info()
                }

            result = run_async_in_bot_loop(test_operations())

            return jsonify({
                'success': True,
                **result
            })

        except Exception as e:
            logger.error(f"Database test error: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'connection_info': db_manager.get_connection_info() if 'db_manager' in globals() else None
            }), 500

    @app.route('/api/settings/import', methods=['POST'])
    def import_settings():
        """Import settings from uploaded file - FIXED VERSION"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        if not require_admin():
            return jsonify({'error': 'Admin permissions required'}), 403

        try:
            # Get JSON data from request
            import_data = request.get_json()

            if not import_data:
                return jsonify({
                    'success': False,
                    'error': 'No import data provided. Please ensure the file is a valid JSON document.'
                }), 400

            # Validate import data structure
            if not isinstance(import_data, dict):
                return jsonify({
                    'success': False,
                    'error': 'Invalid format: Expected JSON object'
                }), 400

            # Check for required fields
            if 'backup_info' not in import_data:
                return jsonify({
                    'success': False,
                    'error': 'Invalid backup file: Missing backup_info section'
                }), 400

            # Process import
            imported_items = 0

            # Process bot settings
            if 'bot_settings' in import_data:
                bot_settings = import_data['bot_settings']
                imported_items += len(bot_settings)

            # Process guild settings
            if 'guild_settings' in import_data:
                guild_settings = import_data['guild_settings']

                async def import_guild_settings():
                    import_count = 0
                    for guild_id_str, settings in guild_settings.items():
                        try:
                            # Extract numeric guild ID
                            guild_id = int(guild_id_str.replace('example_server_', ''))

                            # Import each setting individually
                            for setting_name, value in settings.items():
                                success = await db_manager.set_guild_setting(guild_id, setting_name, value)
                                if success:
                                    import_count += 1
                        except (ValueError, Exception) as e:
                            logger.warning(f"Failed to import settings for {guild_id_str}: {e}")
                    return import_count

                guild_import_count = run_async_in_bot_loop(import_guild_settings())
                imported_items += guild_import_count

            logger.info(f"Settings import completed: {imported_items} items imported")

            return jsonify({
                'success': True,
                'message': f'Successfully imported {imported_items} settings',
                'imported_items': imported_items,
                'backup_info': import_data.get('backup_info', {}),
                'timestamp': datetime.now().isoformat()
            })

        except json.JSONDecodeError:
            return jsonify({
                'success': False,
                'error': 'Invalid JSON format. Please ensure the file is a valid JSON document.'
            }), 400
        except Exception as e:
            logger.error(f"Settings import error: {e}")
            return jsonify({
                'success': False,
                'error': f'Import failed: {str(e)}'
            }), 500

    @app.route('/api/health')
    def api_health():
        """Health check endpoint"""
        try:
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': str(datetime.now() - app.web_manager.startup_time),
                'bot_connected': app.bot is not None and app.bot.is_ready() if app.bot else False,
                'database_healthy': db_manager.connection_healthy if 'db_manager' in globals() else False,
                'requests_handled': app.web_manager.request_count,
                'errors_count': app.web_manager.error_count
            }

            return jsonify(health_data)

        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }), 500

    # ===== ERROR HANDLERS =====

    @app.errorhandler(404)
    def not_found_error(error):
        """Enhanced 404 error handler"""
        log_page_view('404_error')
        return render_template('errors/404.html',
                               user=session.get('user'),
                               page_title='Page Not Found'), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Enhanced 500 error handler"""
        log_page_view('500_error')
        app.web_manager.error_count += 1
        logger.error(f"Internal server error: {error}")
        return render_template('errors/500.html',
                               user=session.get('user'),
                               page_title='Server Error'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Enhanced 403 error handler"""
        log_page_view('403_error')
        return render_template('errors/403.html',
                               user=session.get('user'),
                               page_title='Access Denied'), 403

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all unhandled exceptions"""
        app.web_manager.error_count += 1
        logger.error(f"Unhandled exception: {e}")
        logger.error(traceback.format_exc())

        # Return JSON error for API routes
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'timestamp': datetime.now().isoformat()
            }), 500

        # Return HTML error page for regular routes
        flash('An unexpected error occurred. Please try again later.', 'error')
        return redirect(url_for('dashboard'))

    # ===== TEMPLATE FILTERS =====

    @app.template_filter('format_number')
    def format_number(value):
        """Format numbers with commas"""
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value

    @app.template_filter('timeago')
    def timeago_filter(timestamp):
        """Convert timestamp to 'time ago' format"""
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
            return "Unknown"

    @app.template_filter('datetime')
    def datetime_filter(timestamp):
        """Format datetime for display"""
        try:
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return 'Unknown'

    @app.template_filter('truncate_smart')
    def truncate_smart(text, length=50, suffix='...'):
        """Smart truncation that doesn't break words"""
        if len(text) <= length:
            return text

        truncated = text[:length].rsplit(' ', 1)[0]
        return truncated + suffix

    # ===== CONTEXT PROCESSORS =====

    @app.context_processor
    def inject_global_vars():
        """Inject global variables into all templates"""
        return {
            'current_year': datetime.now().year,
            'bot_name': 'Ladbot',
            'version': '2.0',
            'is_admin': require_admin() if require_auth() else False,
            'current_user': session.get('user') if require_auth() else None,
            'nav_guilds': get_user_guilds()[:5] if require_auth() else [],  # Limit to 5 for nav
            'total_guilds': len(get_user_guilds()) if require_auth() else 0
        }

    logger.info("✅ All routes registered successfully")