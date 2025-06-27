"""
Complete Flask routes for Ladbot web dashboard with Discord OAuth
"""
from flask import render_template, session, redirect, url_for, request, jsonify, flash
import logging
from datetime import datetime
import requests

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

    @app.route('/auth/discord')
    def discord_auth():
        """Redirect to Discord OAuth"""
        if not app.config['DISCORD_CLIENT_ID']:
            flash('Discord OAuth not configured', 'error')
            return redirect(url_for('login'))

        discord_auth_url = (
            f"https://discord.com/api/oauth2/authorize?"
            f"client_id={app.config['DISCORD_CLIENT_ID']}&"
            f"redirect_uri={app.config['DISCORD_REDIRECT_URI']}&"
            f"response_type=code&"
            f"scope=identify"
        )
        return redirect(discord_auth_url)

    @app.route('/callback')
    def discord_callback():
        """Handle Discord OAuth callback"""
        code = request.args.get('code')
        if not code:
            flash('Authorization failed', 'error')
            return redirect(url_for('login'))

        try:
            # Exchange code for access token
            token_data = {
                'client_id': app.config['DISCORD_CLIENT_ID'],
                'client_secret': app.config['DISCORD_CLIENT_SECRET'],
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': app.config['DISCORD_REDIRECT_URI']
            }

            # Get access token
            token_response = requests.post(
                'https://discord.com/api/oauth2/token',
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            token_json = token_response.json()

            if 'access_token' not in token_json:
                flash('Failed to get access token', 'error')
                return redirect(url_for('login'))

            # Get user info
            headers = {'Authorization': f"Bearer {token_json['access_token']}"}
            user_response = requests.get('https://discord.com/api/users/@me', headers=headers)
            user_data = user_response.json()

            # Store user in session
            session['user'] = {
                'id': user_data['id'],
                'username': user_data['username'],
                'discriminator': user_data.get('discriminator', '0'),
                'avatar': user_data.get('avatar')
            }
            session['user_id'] = user_data['id']

            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            logger.error(f"OAuth error: {e}")
            flash('Login failed', 'error')
            return redirect(url_for('login'))

    @app.route('/dashboard')
    def dashboard():
        """Main dashboard page"""
        # Check if user is logged in
        if 'user' not in session:
            flash('Please log in to access the dashboard', 'warning')
            return redirect(url_for('login'))

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
        """Analytics page with real data"""
        # Check if user is logged in
        if 'user' not in session:
            flash('Please log in to access analytics', 'warning')
            return redirect(url_for('login'))

        bot = app.bot
        analytics_data = {}

        try:
            if bot and bot.is_ready():
                # Create sample command statistics (will be real data later)
                command_stats = [
                    {'command': 'help', 'count': 45},
                    {'command': 'ping', 'count': 32},
                    {'command': 'info', 'count': 28},
                    {'command': 'weather', 'count': 15},
                    {'command': '8ball', 'count': 12},
                    {'command': 'joke', 'count': 10},
                    {'command': 'crypto', 'count': 8},
                    {'command': 'roll', 'count': 6},
                    {'command': 'say', 'count': 4},
                    {'command': 'settings', 'count': 2}
                ]

                # Get real guild data
                guild_data = []
                for guild in bot.guilds:
                    guild_data.append({
                        'id': guild.id,
                        'name': guild.name,
                        'members': guild.member_count,
                        'commands_used': 0,  # Will be real data when analytics system is implemented
                        'owner': str(guild.owner) if guild.owner else "Unknown"
                    })

                analytics_data = {
                    'total_guilds': len(bot.guilds),
                    'total_users': len(bot.users),
                    'total_commands': len(bot.commands),
                    'bot_latency': round(bot.latency * 1000),
                    'uptime': str(datetime.now() - bot.start_time).split('.')[0],
                    'loaded_cogs': len(bot.cogs),
                    'command_stats': command_stats,
                    'guild_data': guild_data
                }
            else:
                analytics_data = {
                    'total_guilds': 0,
                    'total_users': 0,
                    'total_commands': 0,
                    'bot_latency': 0,
                    'uptime': 'Starting...',
                    'loaded_cogs': 0,
                    'command_stats': [],
                    'guild_data': []
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
                'command_stats': [],
                'guild_data': []
            }

        return render_template('analytics.html',
                             analytics=analytics_data,
                             user=session.get('user'))

    @app.route('/settings')
    def settings():
        """Settings page"""
        # Check if user is logged in
        if 'user' not in session:
            flash('Please log in to access settings', 'warning')
            return redirect(url_for('login'))

        bot = app.bot

        # Get current bot settings
        settings_data = {
            'prefix': getattr(bot.config, 'prefix', 'l.'),
            'admin_count': len(getattr(bot.config, 'admin_ids', [])),
            'debug_mode': getattr(bot.config, 'DEBUG', False),
            'total_commands': len(bot.commands) if bot else 0,
            'loaded_cogs': len(bot.cogs) if bot else 0
        }

        return render_template('settings.html',
                             user=session.get('user'),
                             settings=settings_data)

    @app.route('/about')
    def about():
        """About page"""
        return render_template('about.html', user=session.get('user'))

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

    @app.route('/api/analytics')
    def api_analytics():
        """API endpoint for analytics data"""
        bot = app.bot

        try:
            if bot and bot.is_ready():
                # Sample command usage data
                command_usage = [
                    {'name': 'help', 'count': 45},
                    {'name': 'ping', 'count': 32},
                    {'name': 'info', 'count': 28},
                    {'name': 'weather', 'count': 15},
                    {'name': '8ball', 'count': 12}
                ]

                # Guild data
                guilds = []
                for guild in bot.guilds:
                    guilds.append({
                        'id': guild.id,
                        'name': guild.name,
                        'members': guild.member_count
                    })

                return jsonify({
                    'command_usage': command_usage,
                    'guilds': guilds,
                    'total_commands': sum(cmd['count'] for cmd in command_usage),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                return jsonify({'error': 'Bot not ready'}), 503

        except Exception as e:
            logger.error(f"Error in API analytics: {e}")
            return jsonify({'error': str(e)}), 500

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

    # Error handlers - Use dashboard template as fallback
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found', 'status': 404}), 404
        else:
            # Return dashboard with error message
            fallback_stats = {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': 'Error', 'loaded_cogs': 0, 'commands_today': 0, 'error_count': 0
            }
            return render_template('dashboard.html',
                                 stats=fallback_stats,
                                 bot_stats=fallback_stats,
                                 user=session.get('user'),
                                 error_message="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error', 'status': 500}), 500
        else:
            # Return dashboard with error message
            fallback_stats = {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': 'Error', 'loaded_cogs': 0, 'commands_today': 0, 'error_count': 0
            }
            return render_template('dashboard.html',
                                 stats=fallback_stats,
                                 bot_stats=fallback_stats,
                                 user=session.get('user'),
                                 error_message="Internal server error"), 500