"""
Web Dashboard Routes - Enhanced with Reset Defaults Functionality
"""
import os
import sys
from pathlib import Path
from flask import render_template, session, redirect, url_for, request, jsonify, flash
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def register_routes(app):
    """Register all web routes"""

    # ===== UTILITY FUNCTIONS =====

    def get_bot_stats():
        """Get bot statistics safely"""
        try:
            bot = app.bot
            if not bot or not bot.is_ready():
                return {
                    'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                    'uptime': 'Offline', 'loaded_cogs': 0, 'commands_today': 0, 'error_count': 0,
                    'bot_status': 'offline', 'bot_ready': False
                }

            # Calculate uptime
            uptime = datetime.now() - bot.start_time if hasattr(bot, 'start_time') else None
            uptime_str = str(uptime).split('.')[0] if uptime else 'Unknown'

            return {
                'guilds': len(bot.guilds),
                'users': len(bot.users),
                'commands': len(bot.commands),
                'latency': round(bot.latency * 1000),
                'uptime': uptime_str,
                'loaded_cogs': len(bot.cogs),
                'commands_today': getattr(bot, 'commands_used_today', 0),
                'error_count': getattr(bot, 'error_count', 0),
                'bot_status': 'online',
                'bot_ready': True
            }
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': 'Error', 'loaded_cogs': 0, 'commands_today': 0, 'error_count': 0,
                'bot_status': 'error', 'bot_ready': False
            }

    def require_auth():
        """Check if user is authenticated"""
        return 'user_id' in session

    def require_admin(guild_id=None):
        """Check if user is admin"""
        if not require_auth():
            return False

        bot = app.bot
        if not bot:
            return False

        user_id = int(session['user_id'])

        # Check if user is bot admin
        admin_ids = getattr(bot.settings, 'ADMIN_IDS', [])
        if user_id in admin_ids:
            return True

        # Check if user is guild admin
        if guild_id:
            guild = bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                if member and member.guild_permissions.administrator:
                    return True

        return False

    # ===== MAIN ROUTES =====

    @app.route('/')
    def index():
        """Home page - redirect to dashboard if logged in"""
        if require_auth():
            return redirect(url_for('dashboard'))
        return render_template('login.html')

    @app.route('/login')
    def login():
        """Discord OAuth login"""
        from .oauth import get_discord_oauth_url
        oauth_url = get_discord_oauth_url(app.config['DISCORD_CLIENT_ID'], app.config['DISCORD_REDIRECT_URI'])
        return redirect(oauth_url)

    @app.route('/callback')
    def oauth_callback():
        """Handle Discord OAuth callback"""
        code = request.args.get('code')
        if not code:
            flash('Authentication failed: No authorization code received', 'error')
            return redirect(url_for('index'))

        try:
            from .oauth import exchange_code_for_token, get_user_info

            # Exchange code for token
            token_data = exchange_code_for_token(
                code,
                app.config['DISCORD_CLIENT_ID'],
                app.config['DISCORD_CLIENT_SECRET'],
                app.config['DISCORD_REDIRECT_URI']
            )

            if not token_data:
                flash('Authentication failed: Could not exchange code for token', 'error')
                return redirect(url_for('index'))

            # Get user info
            user_info = get_user_info(token_data['access_token'])
            if not user_info:
                flash('Authentication failed: Could not get user information', 'error')
                return redirect(url_for('index'))

            # Store in session
            session['user_id'] = user_info['id']
            session['user'] = user_info
            session['access_token'] = token_data['access_token']

            flash(f'Welcome, {user_info["username"]}!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            flash('Authentication failed: Internal error', 'error')
            return redirect(url_for('index'))

    @app.route('/dashboard')
    def dashboard():
        """Main dashboard"""
        if not require_auth():
            return redirect(url_for('login'))

        try:
            stats = get_bot_stats()
            return render_template('dashboard.html',
                                 stats=stats,
                                 bot_stats=stats,  # For backwards compatibility
                                 user=session.get('user'))
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            fallback_stats = {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': 'Error', 'loaded_cogs': 0, 'commands_today': 0, 'error_count': 0,
                'bot_status': 'error', 'bot_ready': False
            }
            return render_template('dashboard.html',
                                 stats=fallback_stats,
                                 bot_stats=fallback_stats,
                                 user=session.get('user'),
                                 error_message="Error loading dashboard")

    @app.route('/settings')
    def settings():
        """Basic settings page"""
        if not require_auth():
            return redirect(url_for('login'))

        stats = get_bot_stats()
        return render_template('settings.html', stats=stats, user=session.get('user'))

    @app.route('/advanced-settings')
    def advanced_settings():
        """Advanced settings page"""
        if not require_auth():
            return redirect(url_for('login'))

        bot = app.bot
        if not bot:
            flash('Bot not available', 'error')
            return redirect(url_for('dashboard'))

        # Get user's guilds that the bot is in
        user_guilds = []
        try:
            if hasattr(bot, 'guilds'):
                for guild in bot.guilds:
                    member = guild.get_member(int(session['user_id']))
                    if member and member.guild_permissions.administrator:
                        user_guilds.append({
                            'id': guild.id,
                            'name': guild.name,
                            'icon': guild.icon.url if guild.icon else None,
                            'member_count': guild.member_count
                        })
        except Exception as e:
            logger.error(f"Error getting user guilds: {e}")

        stats = get_bot_stats()
        return render_template('advanced_settings.html',
                             stats=stats,
                             user=session.get('user'),
                             guilds=user_guilds)

    @app.route('/guild/<int:guild_id>/settings')
    def guild_settings(guild_id):
        """Guild-specific settings page"""
        if not require_auth():
            return redirect(url_for('login'))

        if not require_admin(guild_id):
            flash('You need administrator permissions for this server', 'error')
            return redirect(url_for('advanced_settings'))

        bot = app.bot
        if not bot:
            flash('Bot not available', 'error')
            return redirect(url_for('dashboard'))

        guild = bot.get_guild(guild_id)
        if not guild:
            flash('Server not found or bot not in server', 'error')
            return redirect(url_for('advanced_settings'))

        # Get current settings
        current_settings = {}
        try:
            if hasattr(bot, 'get_setting'):
                default_settings = {
                    'ping': True, 'help': True, 'info': True, 'say': True,
                    'weather': True, 'crypto': True, 'reddit': True, 'eightball': True,
                    'jokes': True, 'ascii_art': True, 'games': True, 'dinosaurs': True,
                    'bible': True, 'converter': True, 'roll': True, 'feedback': True,
                    'tools': True, 'minesweeper': True, 'autoresponses': False
                }

                for setting in default_settings:
                    current_settings[setting] = bot.get_setting(guild_id, setting)
            else:
                logger.warning("Bot has no get_setting method")
        except Exception as e:
            logger.error(f"Error loading guild settings: {e}")

        return render_template('guild_settings.html',
                             guild={
                                 'id': guild.id,
                                 'name': guild.name,
                                 'icon': guild.icon.url if guild.icon else None,
                                 'member_count': guild.member_count
                             },
                             current_settings=current_settings,
                             user=session.get('user'))

    @app.route('/analytics')
    def analytics():
        """Analytics page"""
        if not require_auth():
            return redirect(url_for('login'))

        stats = get_bot_stats()
        return render_template('analytics.html', stats=stats, user=session.get('user'))

    # ===== API ROUTES =====

    @app.route('/api/bot/stats')
    def api_bot_stats():
        """API endpoint for bot statistics"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        stats = get_bot_stats()
        return jsonify(stats)

    @app.route('/api/guild/<int:guild_id>/settings', methods=['GET', 'POST'])
    def api_guild_settings(guild_id):
        """API endpoint for guild settings"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        if not require_admin(guild_id):
            return jsonify({'error': 'Admin permissions required'}), 403

        bot = app.bot
        if not bot:
            return jsonify({'error': 'Bot not available'}), 503

        if request.method == 'GET':
            # Get current settings
            try:
                settings = {}
                if hasattr(bot, 'get_setting'):
                    default_settings = {
                        'ping': True, 'help': True, 'info': True, 'say': True,
                        'weather': True, 'crypto': True, 'reddit': True, 'eightball': True,
                        'jokes': True, 'ascii_art': True, 'games': True, 'dinosaurs': True,
                        'bible': True, 'converter': True, 'roll': True, 'feedback': True,
                        'tools': True, 'minesweeper': True, 'autoresponses': False
                    }

                    for setting in default_settings:
                        settings[setting] = bot.get_setting(guild_id, setting)

                return jsonify({'success': True, 'settings': settings})
            except Exception as e:
                return jsonify({'error': f'Failed to get settings: {str(e)}'}), 500

        elif request.method == 'POST':
            # Update settings
            try:
                data = request.get_json()
                setting = data.get('setting')
                value = data.get('value')

                if not setting:
                    return jsonify({'error': 'Setting name required'}), 400

                # Save setting using multiple methods for compatibility
                success = False

                if hasattr(bot, 'set_setting'):
                    try:
                        bot.set_setting(guild_id, setting, value)
                        success = True
                    except Exception as e:
                        logger.debug(f"set_setting failed: {e}")

                # Try updating cache
                if hasattr(bot, 'settings_cache'):
                    try:
                        if guild_id not in bot.settings_cache:
                            bot.settings_cache[guild_id] = {}
                        bot.settings_cache[guild_id][setting] = value
                        success = True
                    except Exception as e:
                        logger.debug(f"cache update failed: {e}")

                # Try file save
                try:
                    data_dir = getattr(bot, 'data_manager', None)
                    if data_dir and hasattr(data_dir, 'data_dir'):
                        settings_file = data_dir.data_dir / f"guild_settings_{guild_id}.json"
                    else:
                        settings_file = Path("data") / f"guild_settings_{guild_id}.json"

                    # Load existing settings
                    settings_data = {}
                    if settings_file.exists():
                        with open(settings_file, 'r') as f:
                            settings_data = json.load(f)

                    # Update setting
                    settings_data[setting] = value

                    # Save back to file
                    with open(settings_file, 'w') as f:
                        json.dump(settings_data, f, indent=2)
                    success = True
                except Exception as e:
                    logger.debug(f"file save failed: {e}")

                if success:
                    return jsonify({'success': True, 'message': f'Setting {setting} updated'})
                else:
                    return jsonify({'error': 'Failed to save setting'}), 500

            except Exception as e:
                logger.error(f"Error updating guild setting: {e}")
                return jsonify({'error': f'Failed to update setting: {str(e)}'}), 500

    @app.route('/api/guild/<int:guild_id>/reset-defaults', methods=['POST'])
    def api_reset_guild_defaults(guild_id):
        """Reset guild settings to defaults"""
        if not require_auth():
            return jsonify({'error': 'Authentication required'}), 401

        if not require_admin(guild_id):
            return jsonify({'error': 'Admin permissions required'}), 403

        bot = app.bot
        if not bot:
            return jsonify({'error': 'Bot not available'}), 503

        try:
            # Default settings (matching your bot's DEFAULT_SETTINGS)
            default_settings = {
                'ping': True,
                'help': True,
                'info': True,
                'say': True,
                'weather': True,
                'crypto': True,
                'reddit': True,
                'eightball': True,
                'cmd_8ball': True,
                'jokes': True,
                'ascii_art': True,
                'games': True,
                'dinosaurs': True,
                'bible': True,
                'converter': True,
                'roll': True,
                'feedback': True,
                'tools': True,
                'minesweeper': True,
                'autoresponses': False,
            }

            # Reset settings using multiple methods for compatibility
            reset_count = 0

            # Method 1: Try bot's set_setting method
            if hasattr(bot, 'set_setting'):
                for setting, value in default_settings.items():
                    try:
                        bot.set_setting(guild_id, setting, value)
                        reset_count += 1
                    except Exception as e:
                        logger.debug(f"set_setting failed for {setting}: {e}")

            # Method 2: Update settings cache
            if hasattr(bot, 'settings_cache'):
                if guild_id not in bot.settings_cache:
                    bot.settings_cache[guild_id] = {}

                for setting, value in default_settings.items():
                    bot.settings_cache[guild_id][setting] = value

            # Method 3: Direct file save
            try:
                data_dir = getattr(bot, 'data_manager', None)
                if data_dir and hasattr(data_dir, 'data_dir'):
                    settings_file = data_dir.data_dir / f"guild_settings_{guild_id}.json"
                else:
                    settings_file = Path("data") / f"guild_settings_{guild_id}.json"

                # Save default settings to file
                with open(settings_file, 'w') as f:
                    json.dump(default_settings, f, indent=2)

            except Exception as e:
                logger.error(f"Failed to save default settings to file: {e}")

            logger.info(f"Reset {len(default_settings)} settings to defaults for guild {guild_id} by user {session['user_id']}")

            return jsonify({
                'success': True,
                'message': f'Successfully reset {len(default_settings)} settings to defaults',
                'settings_reset': len(default_settings),
                'default_settings': default_settings
            })

        except Exception as e:
            logger.error(f"Error resetting guild settings: {e}")
            return jsonify({'error': f'Failed to reset settings: {str(e)}'}), 500

    # ===== DEMO/DEV ROUTES =====

    @app.route('/demo-login')
    def demo_login():
        """Demo login for development"""
        if app.config.get('ENV') == 'production':
            return "Demo login disabled in production", 403

        # Create fake user session for demo
        session['user_id'] = '123456789'
        session['user'] = {
            'id': '123456789',
            'username': 'Demo User',
            'discriminator': '0001',
            'avatar': None
        }

        flash('Demo login successful!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/logout')
    def logout():
        """Logout and clear session"""
        session.clear()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))

    # ===== ERROR HANDLERS =====

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found', 'status': 404}), 404
        else:
            fallback_stats = {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': 'Error', 'loaded_cogs': 0, 'commands_today': 0, 'error_count': 0,
                'bot_status': 'error', 'bot_ready': False
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
            fallback_stats = {
                'guilds': 0, 'users': 0, 'commands': 0, 'latency': 0,
                'uptime': 'Error', 'loaded_cogs': 0, 'commands_today': 0, 'error_count': 0,
                'bot_status': 'error', 'bot_ready': False
            }
            return render_template('dashboard.html',
                                 stats=fallback_stats,
                                 bot_stats=fallback_stats,
                                 user=session.get('user'),
                                 error_message="Internal server error"), 500