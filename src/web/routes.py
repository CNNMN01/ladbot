"""
Enhanced Routes for Ladbot Web Dashboard - Production Ready
Complete integration with new app.py structure and real-time bot data
"""

from flask import render_template, session, redirect, url_for, request, jsonify, flash, current_app
import logging
from datetime import datetime, timedelta
import traceback
from typing import Dict, Any, Optional, List
import json

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

    def get_user_guilds() -> List[Dict]:
        """Get guilds where user has admin permissions"""
        if not require_auth() or not app.bot:
            return []

        user_id = int(session['user_id'])
        user_guilds = []

        try:
            for guild in app.bot.guilds:
                # Check if user is in guild and has admin perms
                member = guild.get_member(user_id)
                if member and (member.guild_permissions.administrator or user_id in app.bot.settings.ADMIN_IDS):
                    user_guilds.append({
                        'id': str(guild.id),
                        'name': guild.name,
                        'icon': guild.icon.url if guild.icon else None,
                        'member_count': guild.member_count,
                        'owner': guild.owner_id == user_id
                    })
        except Exception as e:
            logger.error(f"Error getting user guilds: {e}")

        return user_guilds

    def log_page_view(page: str):
        """Log page views for analytics"""
        try:
            app.web_manager.request_count += 1
            logger.debug(f"Page view: {page} by user {session.get('user_id', 'anonymous')}")
        except:
            pass

    # ===== MAIN ROUTES =====

    @app.route('/')
    def index():
        """Enhanced home page with dynamic content"""
        log_page_view('index')

        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        try:
            # Get basic stats for public display
            stats = app.web_manager._get_comprehensive_stats()
            bot_info = {
                'name': 'Ladbot',
                'description': 'Your friendly Discord entertainment bot',
                'version': '2.0',
                'online': stats['bot_status'] == 'online',
                'guilds': stats['guilds'],
                'users': stats['users'],
                'commands': stats['commands'],
                'uptime': stats['uptime']
            }

            # Featured commands for display
            featured_commands = [
                {'name': 'help', 'description': 'Get help with bot commands', 'category': 'utility'},
                {'name': 'weather', 'description': 'Get weather information', 'category': 'utility'},
                {'name': '8ball', 'description': 'Ask the magic 8-ball', 'category': 'fun'},
                {'name': 'crypto', 'description': 'Get cryptocurrency prices', 'category': 'info'},
                {'name': 'joke', 'description': 'Get a random joke', 'category': 'fun'},
                {'name': 'roll', 'description': 'Roll dice', 'category': 'utility'}
            ]

            return render_template('index.html',
                                 bot=bot_info,
                                 stats=stats,
                                 featured_commands=featured_commands,
                                 oauth_enabled=bool(app.config.get('DISCORD_CLIENT_ID')))

        except Exception as e:
            logger.error(f"Index page error: {e}")
            # Fallback for index page
            return render_template('index.html',
                                 bot={'name': 'Ladbot', 'online': False},
                                 stats={}, featured_commands=[],
                                 oauth_enabled=False)

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

            # Recent activity (mock data - implement based on your tracking)
            recent_activity = [
                {
                    'action': 'Command executed',
                    'details': f'{stats["commands_today"]} commands used today',
                    'timestamp': datetime.now() - timedelta(minutes=5),
                    'type': 'command'
                },
                {
                    'action': 'Bot status check',
                    'details': f'Latency: {stats["latency"]}ms',
                    'timestamp': datetime.now() - timedelta(minutes=15),
                    'type': 'system'
                }
            ]

            # System health data
            system_health = {
                'memory_usage': stats['memory_usage'],
                'response_time': stats['latency'],
                'error_rate': app.web_manager._calculate_error_rate(
                    stats['error_count'],
                    stats['total_commands']
                ),
                'uptime_percentage': 99.5  # Could be calculated from actual uptime tracking
            }

            return render_template('dashboard.html',
                                 stats=stats,
                                 analytics=analytics,
                                 settings=settings_data,
                                 user=session.get('user'),
                                 user_guilds=user_guilds,
                                 is_admin=is_admin,
                                 recent_activity=recent_activity,
                                 system_health=system_health,
                                 page_title='Dashboard')

        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

            # Graceful fallback
            flash('Error loading dashboard data. Some information may be unavailable.', 'warning')
            return render_template('dashboard.html',
                                 stats=app.web_manager._get_fallback_stats(),
                                 analytics={},
                                 settings={},
                                 user=session.get('user'),
                                 user_guilds=[],
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
                        {'key': 'prefix', 'name': 'Command Prefix', 'type': 'text', 'value': settings_data.get('prefix', 'l.')},
                        {'key': 'auto_responses', 'name': 'Auto Responses', 'type': 'boolean', 'value': True}
                    ]
                },
                'features': {
                    'name': 'Feature Settings',
                    'description': 'Enable or disable bot features',
                    'settings': [
                        {'key': 'weather_enabled', 'name': 'Weather Commands', 'type': 'boolean', 'value': True},
                        {'key': 'crypto_enabled', 'name': 'Crypto Commands', 'type': 'boolean', 'value': True},
                        {'key': 'games_enabled', 'name': 'Game Commands', 'type': 'boolean', 'value': True}
                    ]
                },
                'moderation': {
                    'name': 'Moderation',
                    'description': 'Moderation and admin tools',
                    'settings': [
                        {'key': 'mod_logs', 'name': 'Moderation Logs', 'type': 'boolean', 'value': False},
                        {'key': 'auto_mod', 'name': 'Auto Moderation', 'type': 'boolean', 'value': False}
                    ]
                }
            }

            return render_template('settings.html',
                                 stats=stats,
                                 settings=settings_data,
                                 setting_categories=setting_categories,
                                 user=session.get('user'),
                                 user_guilds=user_guilds,
                                 is_admin=is_admin,
                                 page_title='Settings')

        except Exception as e:
            logger.error(f"Settings page error: {e}")
            flash('Error loading settings page', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/analytics')
    def analytics():
        """Enhanced analytics page with comprehensive data"""
        log_page_view('analytics')

        if not require_auth():
            return redirect(url_for('login'))

        try:
            stats = app.web_manager._get_comprehensive_stats()
            analytics_data = app.web_manager._get_analytics_data()

            # Prepare chart data
            command_chart_data = {
                'labels': [cmd['name'] for cmd in analytics_data.get('top_commands', [])[:10]],
                'data': [cmd['count'] for cmd in analytics_data.get('top_commands', [])[:10]]
            }

            # Growth data (mock - implement based on your tracking)
            growth_data = {
                'guilds': [
                    {'date': '2024-01-01', 'value': max(1, stats['guilds'] - 5)},
                    {'date': '2024-02-01', 'value': max(1, stats['guilds'] - 3)},
                    {'date': '2024-03-01', 'value': stats['guilds']}
                ],
                'users': [
                    {'date': '2024-01-01', 'value': max(10, stats['users'] - 100)},
                    {'date': '2024-02-01', 'value': max(10, stats['users'] - 50)},
                    {'date': '2024-03-01', 'value': stats['users']}
                ]
            }

            # Performance metrics
            performance_metrics = {
                'average_latency': stats.get('average_latency', 0),
                'commands_per_day': analytics_data.get('daily_commands', 0),
                'error_rate': app.web_manager._calculate_error_rate(
                    stats.get('error_count', 0),
                    stats.get('total_commands', 1)
                ),
                'uptime': stats.get('uptime', '0:00:00')
            }

            return render_template('analytics.html',
                                 stats=stats,
                                 analytics=analytics_data,
                                 command_chart_data=command_chart_data,
                                 growth_data=growth_data,
                                 performance_metrics=performance_metrics,
                                 user=session.get('user'),
                                 is_admin=require_admin(),
                                 page_title='Analytics')

        except Exception as e:
            logger.error(f"Analytics page error: {e}")
            flash('Error loading analytics data', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/guild/<int:guild_id>')
    def guild_dashboard(guild_id):
        """Individual guild dashboard"""
        log_page_view(f'guild_{guild_id}')

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
                flash('You do not have access to this server', 'error')
                return redirect(url_for('dashboard'))

            # Get guild-specific data
            if app.bot:
                discord_guild = app.bot.get_guild(guild_id)
                if discord_guild:
                    guild_data.update({
                        'channels': len(discord_guild.channels),
                        'roles': len(discord_guild.roles),
                        'created_at': discord_guild.created_at,
                        'features': discord_guild.features
                    })

            # Get guild settings (implement based on your settings system)
            guild_settings = {}
            if hasattr(app.bot, 'data_manager'):
                guild_settings = app.bot.data_manager.get_all_guild_settings(guild_id)

            return render_template('guild_dashboard.html',
                                 guild=guild_data,
                                 settings=guild_settings,
                                 user=session.get('user'),
                                 page_title=f'{guild_data["name"]} Dashboard')

        except Exception as e:
            logger.error(f"Guild dashboard error: {e}")
            flash('Error loading server dashboard', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/about')
    def about():
        """About page with bot information"""
        log_page_view('about')

        stats = app.web_manager._get_comprehensive_stats()

        bot_info = {
            'name': 'Ladbot',
            'version': '2.0',
            'description': 'A comprehensive Discord entertainment bot with 55+ commands',
            'features': [
                'Entertainment commands and games',
                'Weather and cryptocurrency information',
                'Admin tools and moderation',
                'Real-time web dashboard',
                'Analytics and statistics',
                'Customizable settings per server'
            ],
            'stats': stats,
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

    # ===== API INTEGRATION ROUTES =====

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

    # ===== ERROR HANDLERS =====

    @app.before_request
    def before_request():
        """Execute before each request"""
        # Update request count
        app.web_manager.request_count += 1

        # Log API requests
        if request.path.startswith('/api/'):
            logger.debug(f"API Request: {request.method} {request.path}")

    @app.after_request
    def after_request(response):
        """Execute after each request"""
        # Add custom headers
        response.headers['X-Bot-Version'] = '2.0'
        response.headers['X-Powered-By'] = 'Ladbot'

        return response

    # ===== TEMPLATE HELPERS =====

    @app.template_global()
    def get_bot_status():
        """Template helper to get bot status"""
        try:
            if app.bot and app.bot.is_ready():
                return 'online'
            return 'offline'
        except:
            return 'unknown'

    @app.template_global()
    def format_uptime(uptime_str):
        """Template helper to format uptime"""
        try:
            if isinstance(uptime_str, str) and ':' in uptime_str:
                parts = uptime_str.split(':')
                if len(parts) >= 3:
                    hours = int(parts[0])
                    minutes = int(parts[1])

                    if hours > 24:
                        days = hours // 24
                        hours = hours % 24
                        return f"{days}d {hours}h {minutes}m"
                    else:
                        return f"{hours}h {minutes}m"

            return uptime_str
        except:
            return uptime_str

    @app.template_global()
    def get_command_count():
        """Template helper to get total command count"""
        try:
            stats = app.web_manager._get_comprehensive_stats()
            return stats.get('commands', 0)
        except:
            return 0

    logger.info("✅ All web routes registered successfully")