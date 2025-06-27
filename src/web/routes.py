"""
Updated routes with Discord OAuth and Analytics
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import render_template, session, redirect, url_for, request, jsonify, flash
from web.oauth import oauth
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all routes with OAuth"""

    @app.route('/')
    def index():
        """Home page"""
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login')
    def login():
        """Login page with Discord OAuth"""
        if 'user_id' in session:
            return redirect(url_for('dashboard'))

        # Generate Discord OAuth URL
        discord_login_url = oauth.get_login_url()
        return render_template('login.html', discord_login_url=discord_login_url)

    @app.route('/callback')
    def oauth_callback():
        """Handle Discord OAuth callback"""
        code = request.args.get('code')
        error = request.args.get('error')

        if error:
            flash('Discord authentication failed', 'error')
            return redirect(url_for('login'))

        if not code:
            flash('No authorization code received', 'error')
            return redirect(url_for('login'))

        # Exchange code for token
        token_data = oauth.exchange_code(code)
        if not token_data:
            flash('Failed to get access token', 'error')
            return redirect(url_for('login'))

        # Get user info
        user_info = oauth.get_user_info(token_data['access_token'])
        if not user_info:
            flash('Failed to get user information', 'error')
            return redirect(url_for('login'))

        # Check if user is admin
        user_id = int(user_info['id'])
        is_admin = False

        if app.bot and hasattr(app.bot.config, 'admin_ids'):
            is_admin = user_id in app.bot.config.admin_ids
        elif app.bot and hasattr(app.bot.config, 'ADMIN_IDS'):
            is_admin = user_id in app.bot.config.ADMIN_IDS

        if not is_admin:
            flash('Access denied. Admin permissions required.', 'error')
            return redirect(url_for('login'))

        # Store user session
        session['user_id'] = str(user_id)
        session['user'] = {
            'id': user_info['id'],
            'username': user_info['username'],
            'discriminator': user_info.get('discriminator', '0'),
            'avatar': user_info.get('avatar')
        }

        flash(f'Welcome, {user_info["username"]}!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/dashboard')
    def dashboard():
        """Dashboard page"""
        if 'user_id' not in session:
            return redirect(url_for('login'))

        # Get bot stats with proper variable name for template
        bot_stats = {}
        if app.bot:
            # Calculate uptime properly
            uptime_str = "0s"
            if hasattr(app.bot, 'start_time'):
                uptime_delta = datetime.now() - app.bot.start_time
                days = uptime_delta.days
                hours, remainder = divmod(uptime_delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                if days > 0:
                    uptime_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    uptime_str = f"{hours}h {minutes}m"
                elif minutes > 0:
                    uptime_str = f"{minutes}m {seconds}s"
                else:
                    uptime_str = f"{seconds}s"

            bot_stats = {
                'guilds': len(app.bot.guilds) if hasattr(app.bot, 'guilds') else 0,
                'users': len(app.bot.users) if hasattr(app.bot, 'users') else 0,
                'commands': len(app.bot.commands) if hasattr(app.bot, 'commands') else 0,
                'latency': round(app.bot.latency * 1000) if hasattr(app.bot, 'latency') else 0,
                'uptime': uptime_str,
                'status': 'online' if app.bot.is_ready() else 'offline',
                'loaded_cogs': len(app.bot.cogs) if hasattr(app.bot, 'cogs') else 0,
                'commands_used_today': getattr(app.bot, 'commands_used_today', 0)
            }
        else:
            # Default stats when bot is not available
            bot_stats = {
                'guilds': 0,
                'users': 0,
                'commands': 0,
                'latency': 0,
                'uptime': '0s',
                'status': 'offline',
                'loaded_cogs': 0,
                'commands_used_today': 0
            }

        return render_template('dashboard.html', bot_stats=bot_stats, user=session.get('user'))

    @app.route('/settings')
    def settings():
        """Settings page"""
        if 'user_id' not in session:
            return redirect(url_for('login'))

        # Check admin permissions
        user_id = int(session.get('user_id'))
        is_admin = False

        if app.bot and hasattr(app.bot.config, 'admin_ids'):
            is_admin = user_id in app.bot.config.admin_ids
        elif app.bot and hasattr(app.bot.config, 'ADMIN_IDS'):
            is_admin = user_id in app.bot.config.ADMIN_IDS

        if not is_admin:
            flash('Admin permissions required.', 'error')
            return redirect(url_for('dashboard'))

        # Get guilds where bot is present
        guilds = []
        if app.bot:
            for guild in app.bot.guilds:
                guilds.append({
                    'id': guild.id,
                    'name': guild.name,
                    'member_count': guild.member_count,
                    'icon': str(guild.icon.url) if guild.icon else None
                })

        return render_template('settings.html', guilds=guilds)

    @app.route('/analytics')
    def analytics():
        """Analytics page"""
        if 'user_id' not in session:
            return redirect(url_for('login'))

        # Check admin permissions
        user_id = int(session.get('user_id'))
        is_admin = False

        if app.bot and hasattr(app.bot.config, 'admin_ids'):
            is_admin = user_id in app.bot.config.admin_ids
        elif app.bot and hasattr(app.bot.config, 'ADMIN_IDS'):
            is_admin = user_id in app.bot.config.ADMIN_IDS

        if not is_admin:
            flash('Admin permissions required.', 'error')
            return redirect(url_for('dashboard'))

        # Get detailed analytics data
        analytics_data = {}
        if app.bot:
            # Command usage statistics
            command_stats = {}
            for command in app.bot.commands:
                command_stats[command.name] = getattr(command, 'usage_count', 0)

            # Guild analytics
            guild_data = []
            for guild in app.bot.guilds:
                guild_data.append({
                    'name': guild.name,
                    'member_count': guild.member_count,
                    'created_at': guild.created_at.isoformat(),
                    'id': guild.id
                })

            # Calculate uptime properly
            uptime_str = "0s"
            if hasattr(app.bot, 'start_time'):
                uptime_delta = datetime.now() - app.bot.start_time
                days = uptime_delta.days
                hours, remainder = divmod(uptime_delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                if days > 0:
                    uptime_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    uptime_str = f"{hours}h {minutes}m"
                elif minutes > 0:
                    uptime_str = f"{minutes}m {seconds}s"
                else:
                    uptime_str = f"{seconds}s"

            analytics_data = {
                'command_stats': command_stats,
                'guild_data': guild_data,
                'total_users': len(app.bot.users),
                'total_guilds': len(app.bot.guilds),
                'bot_latency': round(app.bot.latency * 1000),
                'uptime': uptime_str,
                'total_commands': len(app.bot.commands),
                'loaded_cogs': len(app.bot.cogs)
            }

        return render_template('analytics.html', analytics=analytics_data, user=session.get('user'))

    @app.route('/api/guild/<int:guild_id>/settings', methods=['GET'])
    def get_guild_settings(guild_id):
        """Get settings for a specific guild"""
        if not session.get('user_id'):
            return jsonify({'error': 'Not authenticated'}), 401

        # Check admin permissions
        user_id = int(session.get('user_id'))
        is_admin = False

        if app.bot and hasattr(app.bot.config, 'admin_ids'):
            is_admin = user_id in app.bot.config.admin_ids
        elif app.bot and hasattr(app.bot.config, 'ADMIN_IDS'):
            is_admin = user_id in app.bot.config.ADMIN_IDS

        if not is_admin:
            return jsonify({'error': 'Access denied'}), 403

        # Get guild settings
        settings = {}
        if app.bot:
            available_settings = [
                'ping', 'help', 'feedback', 'say', 'ascii', 'cmd_8ball',
                'jokes', 'weather', 'crypto', 'reddit', 'bible', 'roll',
                'minesweeper', 'autoresponses', 'games'
            ]

            for setting in available_settings:
                settings[setting] = app.bot.get_setting(guild_id, setting)

        return jsonify({'settings': settings})

    @app.route('/api/guild/<int:guild_id>/settings', methods=['POST'])
    def update_guild_settings(guild_id):
        """Update settings for a specific guild"""
        if not session.get('user_id'):
            return jsonify({'error': 'Not authenticated'}), 401

        # Check admin permissions
        user_id = int(session.get('user_id'))
        is_admin = False

        if app.bot and hasattr(app.bot.config, 'admin_ids'):
            is_admin = user_id in app.bot.config.admin_ids
        elif app.bot and hasattr(app.bot.config, 'ADMIN_IDS'):
            is_admin = user_id in app.bot.config.ADMIN_IDS

        if not is_admin:
            return jsonify({'error': 'Access denied'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update settings
        try:
            for setting, value in data.items():
                if hasattr(app.bot, 'update_setting'):
                    app.bot.update_setting(guild_id, setting, value)
                # Add logging
                logger.info(f"Updated setting {setting}={value} for guild {guild_id} by user {user_id}")

            return jsonify({'success': True, 'message': 'Settings updated successfully'})
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            return jsonify({'error': 'Failed to update settings'}), 500

    @app.route('/api/stats')
    def api_stats():
        """API endpoint for bot statistics"""
        if app.bot:
            # Calculate uptime properly
            uptime_str = "0s"
            if hasattr(app.bot, 'start_time'):
                uptime_delta = datetime.now() - app.bot.start_time
                uptime_str = str(uptime_delta).split('.')[0]  # Remove microseconds

            stats = {
                'status': 'online' if app.bot.is_ready() else 'offline',
                'guilds': len(app.bot.guilds),
                'users': len(app.bot.users),
                'commands': len(app.bot.commands),
                'latency': round(app.bot.latency * 1000),
                'uptime': uptime_str,
                'loaded_cogs': len(app.bot.cogs),
                'commands_used_today': getattr(app.bot, 'commands_used_today', 0),
                'timestamp': datetime.now().isoformat()
            }
        else:
            stats = {
                'status': 'offline',
                'guilds': 0,
                'users': 0,
                'commands': 0,
                'latency': 0,
                'uptime': '0s',
                'loaded_cogs': 0,
                'commands_used_today': 0,
                'timestamp': datetime.now().isoformat()
            }
        return jsonify(stats)

    @app.route('/logout')
    def logout():
        """Logout"""
        session.clear()
        flash('Logged out successfully!', 'info')
        return redirect(url_for('login'))