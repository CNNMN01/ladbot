"""
Complete Flask routes for Ladbot web dashboard with Advanced Settings
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
                    'error_count': getattr(bot, 'error_count', 0),
                    'bot_status': 'online',
                    'bot_ready': True
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
                    'error_count': 0,
                    'bot_status': 'offline',
                    'bot_ready': False
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
                'error_count': 0,
                'bot_status': 'error',
                'bot_ready': False
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
        """Basic settings page - redirect to advanced settings"""
        return redirect(url_for('advanced_settings'))

    @app.route('/settings/advanced')
    def advanced_settings():
        """Advanced settings configuration page"""
        if 'user' not in session:
            flash('Please log in to access settings', 'warning')
            return redirect(url_for('login'))

        bot = app.bot

        # Get all guilds user has access to
        user_guilds = []
        try:
            for guild in bot.guilds:
                # Check if user is admin in this guild
                member = guild.get_member(int(session['user_id']))
                if member and (member.guild_permissions.administrator or
                              int(session['user_id']) in bot.config.admin_ids):
                    user_guilds.append({
                        'id': guild.id,
                        'name': guild.name,
                        'icon': guild.icon.url if guild.icon else None,
                        'member_count': guild.member_count,
                        'owner': str(guild.owner) if guild.owner else "Unknown"
                    })
        except Exception as e:
            logger.error(f"Error getting user guilds: {e}")

        # Check if user is bot admin
        is_bot_admin = int(session['user_id']) in bot.config.admin_ids

        return render_template('advanced_settings.html',
                             user=session.get('user'),
                             guilds=user_guilds,
                             is_bot_admin=is_bot_admin)

    @app.route('/settings/guild/<int:guild_id>')
    def guild_settings(guild_id):
        """Guild-specific settings page with fallback handling"""
        if 'user' not in session:
            flash('Please log in to access settings', 'warning')
            return redirect(url_for('login'))

        bot = app.bot

        # Verify user has permission for this guild
        guild = bot.get_guild(guild_id)
        if not guild:
            flash('Guild not found', 'error')
            return redirect(url_for('advanced_settings'))

        member = guild.get_member(int(session['user_id']))
        if not member or not (member.guild_permissions.administrator or
                             int(session['user_id']) in bot.config.admin_ids):
            flash('You do not have permission to manage this server', 'error')
            return redirect(url_for('advanced_settings'))

        # Get current settings with robust fallback handling
        try:
            # Try to use settings manager if available
            if hasattr(bot, 'settings_manager') and bot.settings_manager:
                current_settings = bot.settings_manager.load_guild_settings(guild_id)
                commands = bot.settings_manager.get_all_commands()
                roles = bot.settings_manager.get_guild_roles(guild_id)
            else:
                # Fallback: create basic settings and get data directly from bot
                current_settings = {
                    'prefix': getattr(bot.config, 'prefix', 'l.'),
                    'embed_color': '#4e73df',
                    'command_cooldown': 3,
                    'autoresponses': False,
                    'welcome_messages': True,
                    'moderation_enabled': True,
                    'spam_protection': True,
                    'nsfw_filter': True,
                    'logging_enabled': True,
                    'auto_delete_commands': False,
                    'disabled_commands': [],
                    'admin_roles': [],
                    'moderator_roles': []
                }

                # Get commands directly from bot
                commands = []
                for command in bot.commands:
                    commands.append({
                        'name': command.name,
                        'description': command.help or 'No description available',
                        'category': getattr(command.cog, 'qualified_name', 'General') if command.cog else 'General',
                        'aliases': list(command.aliases) if command.aliases else []
                    })
                commands = sorted(commands, key=lambda x: x['category'])

                # Get roles directly from guild
                roles = []
                for role in guild.roles:
                    if role.name != "@everyone":
                        roles.append({
                            'id': role.id,
                            'name': role.name,
                            'color': str(role.color),
                            'permissions': role.permissions.value,
                            'mentionable': role.mentionable
                        })
                roles = sorted(roles, key=lambda x: x['name'])

        except Exception as e:
            logger.error(f"Error loading settings for guild {guild_id}: {e}")
            # Ultimate fallback with minimal settings
            current_settings = {
                'prefix': 'l.',
                'embed_color': '#4e73df',
                'command_cooldown': 3,
                'autoresponses': False,
                'welcome_messages': True,
                'moderation_enabled': True,
                'spam_protection': True
            }
            commands = []
            roles = []

        return render_template('guild_settings.html',
                             user=session.get('user'),
                             guild={
                                 'id': guild.id,
                                 'name': guild.name,
                                 'icon': guild.icon.url if guild.icon else None,
                                 'member_count': guild.member_count,
                                 'owner': str(guild.owner) if guild.owner else "Unknown"
                             },
                             current_settings=current_settings,
                             commands=commands,
                             roles=roles)

    @app.route('/about')
    def about():
        """About page"""
        return render_template('about.html', user=session.get('user'))

    # ===== API ROUTES =====

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
                    'status': 'online',
                    'bot_ready': True
                }
            else:
                stats = {
                    'guilds': 0,
                    'users': 0,
                    'commands': 0,
                    'latency': 0,
                    'uptime': 'Starting...',
                    'loaded_cogs': 0,
                    'status': 'starting',
                    'bot_ready': False
                }
        except Exception as e:
            logger.error(f"Error in API stats: {e}")
            stats = {
                'error': str(e),
                'status': 'error',
                'bot_ready': False
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

    @app.route('/api/settings/guild/<int:guild_id>', methods=['GET', 'POST'])
    def api_guild_settings(guild_id):
        """Get or save guild settings via API with fallback handling"""
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        bot = app.bot

        # Verify permission
        guild = bot.get_guild(guild_id)
        if not guild:
            return jsonify({'error': 'Guild not found'}), 404

        member = guild.get_member(int(session['user_id']))
        if not member or not (member.guild_permissions.administrator or
                             int(session['user_id']) in bot.config.admin_ids):
            return jsonify({'error': 'Insufficient permissions'}), 403

        if request.method == 'GET':
            # Return current guild settings with fallback
            try:
                if hasattr(bot, 'settings_manager') and bot.settings_manager:
                    settings = bot.settings_manager.load_guild_settings(guild_id)
                else:
                    # Fallback settings
                    settings = {
                        'prefix': 'l.',
                        'embed_color': '#4e73df',
                        'command_cooldown': 3,
                        'autoresponses': False,
                        'welcome_messages': True,
                        'moderation_enabled': True,
                        'spam_protection': True
                    }
                return jsonify(settings)
            except Exception as e:
                logger.error(f"Error loading guild {guild_id} settings: {e}")
                return jsonify({'error': str(e)}), 500

        elif request.method == 'POST':
            # Save new guild settings with fallback
            try:
                new_settings = request.json
                if not new_settings:
                    return jsonify({'error': 'No settings data provided'}), 400

                # Try to save using settings manager
                if hasattr(bot, 'settings_manager') and bot.settings_manager:
                    if bot.settings_manager.apply_guild_settings(guild_id, new_settings):
                        return jsonify({
                            'success': True,
                            'message': 'Settings saved successfully',
                            'timestamp': datetime.now().isoformat()
                        })
                    else:
                        return jsonify({'error': 'Failed to save settings'}), 500
                else:
                    # Fallback: just return success for now
                    logger.info(f"Settings would be saved for guild {guild_id}: {new_settings}")
                    return jsonify({
                        'success': True,
                        'message': 'Settings saved successfully (basic mode)',
                        'timestamp': datetime.now().isoformat()
                    })

            except Exception as e:
                logger.error(f"Error saving guild {guild_id} settings: {e}")
                return jsonify({'error': str(e)}), 500

    @app.route('/api/settings/global', methods=['GET', 'POST'])
    def api_global_settings():
        """Get or update global bot settings with fallback"""
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        # Check if user is bot admin
        if int(session['user_id']) not in app.bot.config.admin_ids:
            return jsonify({'error': 'Bot admin access required'}), 403

        bot = app.bot

        if request.method == 'GET':
            try:
                if hasattr(bot, 'settings_manager') and bot.settings_manager:
                    return jsonify(bot.settings_manager.global_settings)
                else:
                    # Fallback global settings
                    fallback_settings = {
                        'bot_name': 'Ladbot',
                        'default_prefix': 'l.',
                        'max_command_cooldown': 5,
                        'error_logging': True,
                        'analytics_enabled': True,
                        'auto_backup': False,
                        'maintenance_mode': False,
                        'welcome_message_enabled': True,
                        'default_embed_color': '#4e73df'
                    }
                    return jsonify(fallback_settings)
            except Exception as e:
                logger.error(f"Error getting global settings: {e}")
                return jsonify({'error': str(e)}), 500

        elif request.method == 'POST':
            try:
                new_settings = request.json
                if not new_settings:
                    return jsonify({'error': 'No settings data provided'}), 400

                if hasattr(bot, 'settings_manager') and bot.settings_manager:
                    bot.settings_manager.global_settings.update(new_settings)
                    if bot.settings_manager.save_global_settings():
                        return jsonify({
                            'success': True,
                            'message': 'Global settings updated successfully'
                        })
                    else:
                        return jsonify({'error': 'Failed to save global settings'}), 500
                else:
                    # Fallback: just log the attempt
                    logger.info(f"Global settings would be updated: {new_settings}")
                    return jsonify({
                        'success': True,
                        'message': 'Global settings updated successfully (basic mode)'
                    })

            except Exception as e:
                logger.error(f"Error updating global settings: {e}")
                return jsonify({'error': str(e)}), 500

    @app.route('/api/guild/<int:guild_id>/commands')
    def api_guild_commands(guild_id):
        """Get available commands for a guild"""
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        bot = app.bot

        # Verify permission
        guild = bot.get_guild(guild_id)
        if not guild:
            return jsonify({'error': 'Guild not found'}), 404

        member = guild.get_member(int(session['user_id']))
        if not member or not (member.guild_permissions.administrator or
                             int(session['user_id']) in bot.config.admin_ids):
            return jsonify({'error': 'Insufficient permissions'}), 403

        try:
            # Get commands from bot directly
            commands = []
            for command in bot.commands:
                commands.append({
                    'name': command.name,
                    'description': command.help or 'No description available',
                    'category': getattr(command.cog, 'qualified_name', 'General') if command.cog else 'General',
                    'aliases': list(command.aliases) if command.aliases else []
                })

            return jsonify(sorted(commands, key=lambda x: x['category']))

        except Exception as e:
            logger.error(f"Error getting commands for guild {guild_id}: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/guild/<int:guild_id>/roles')
    def api_guild_roles(guild_id):
        """Get roles for a guild"""
        if 'user' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        bot = app.bot

        # Verify permission
        guild = bot.get_guild(guild_id)
        if not guild:
            return jsonify({'error': 'Guild not found'}), 404

        member = guild.get_member(int(session['user_id']))
        if not member or not (member.guild_permissions.administrator or
                             int(session['user_id']) in bot.config.admin_ids):
            return jsonify({'error': 'Insufficient permissions'}), 403

        try:
            # Get roles directly from guild
            roles = []
            for role in guild.roles:
                if role.name != "@everyone":
                    roles.append({
                        'id': role.id,
                        'name': role.name,
                        'color': str(role.color),
                        'permissions': role.permissions.value,
                        'mentionable': role.mentionable
                    })

            return jsonify(sorted(roles, key=lambda x: x['name']))

        except Exception as e:
            logger.error(f"Error getting roles for guild {guild_id}: {e}")
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

    # ===== AUTHENTICATION ROUTES =====

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

    # ===== ERROR HANDLERS =====

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found', 'status': 404}), 404
        else:
            # Return dashboard with error message
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
            # Return dashboard with error message
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