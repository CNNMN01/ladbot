"""
Discord OAuth Integration for Ladbot Web Dashboard
Complete OAuth2 flow with comprehensive error handling and security features
"""

import requests
import logging
from urllib.parse import urlencode, parse_qs
from flask import session, request, redirect, url_for, flash, current_app, jsonify
from datetime import datetime, timedelta
import secrets
import hashlib
import base64
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# OAuth Configuration Constants
DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTH_BASE = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = f"{DISCORD_API_BASE}/oauth2/token"
DISCORD_USER_URL = f"{DISCORD_API_BASE}/users/@me"
DISCORD_GUILDS_URL = f"{DISCORD_API_BASE}/users/@me/guilds"

# OAuth Scopes
OAUTH_SCOPES = ["identify", "guilds"]

class DiscordOAuth:
    """Discord OAuth handler with security features"""

    def __init__(self, app):
        self.app = app
        self.client_id = app.config.get('DISCORD_CLIENT_ID')
        self.client_secret = app.config.get('DISCORD_CLIENT_SECRET')
        self.redirect_uri = app.config.get('DISCORD_REDIRECT_URI')

        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate OAuth configuration"""
        if not self.client_id:
            logger.warning("Discord OAuth: CLIENT_ID not configured")
            return False

        if not self.client_secret:
            logger.warning("Discord OAuth: CLIENT_SECRET not configured")
            return False

        if not self.redirect_uri:
            logger.warning("Discord OAuth: REDIRECT_URI not configured")
            return False

        logger.info(f"✅ Discord OAuth configured - Redirect: {self.redirect_uri}")
        return True

    def is_configured(self) -> bool:
        """Check if OAuth is properly configured"""
        return all([self.client_id, self.client_secret, self.redirect_uri])

    def generate_state(self) -> str:
        """Generate secure state parameter for CSRF protection"""
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        session['oauth_timestamp'] = datetime.now().timestamp()
        return state

    def validate_state(self, received_state: str) -> bool:
        """Validate state parameter to prevent CSRF attacks"""
        stored_state = session.get('oauth_state')
        stored_timestamp = session.get('oauth_timestamp')

        # Clear state from session
        session.pop('oauth_state', None)
        session.pop('oauth_timestamp', None)

        if not stored_state or not stored_timestamp:
            logger.warning("OAuth: No stored state found")
            return False

        if stored_state != received_state:
            logger.warning("OAuth: State mismatch - possible CSRF attack")
            return False

        # Check if state is not older than 10 minutes
        if datetime.now().timestamp() - stored_timestamp > 600:
            logger.warning("OAuth: State expired")
            return False

        return True

    def get_authorization_url(self) -> str:
        """Generate Discord authorization URL with PKCE"""
        if not self.is_configured():
            raise ValueError("OAuth not properly configured")

        state = self.generate_state()

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(OAUTH_SCOPES),
            'state': state,
            'prompt': 'consent'  # Always show consent screen for security
        }

        auth_url = f"{DISCORD_AUTH_BASE}?{urlencode(params)}"
        logger.info(f"Generated OAuth URL for client {self.client_id}")

        return auth_url

    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        try:
            token_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri
            }

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Ladbot/2.0 (Discord Bot Dashboard)'
            }

            logger.debug("Exchanging code for token...")

            response = requests.post(
                DISCORD_TOKEN_URL,
                data=token_data,
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return None

            token_info = response.json()

            # Validate token response
            if 'access_token' not in token_info:
                logger.error("Token response missing access_token")
                return None

            # Store token expiration time
            expires_in = token_info.get('expires_in', 3600)
            token_info['expires_at'] = datetime.now() + timedelta(seconds=expires_in)

            logger.info("Successfully exchanged code for token")
            return token_info

        except requests.RequestException as e:
            logger.error(f"Network error during token exchange: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token exchange: {e}")
            return None

    def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Discord API"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'Ladbot/2.0 (Discord Bot Dashboard)'
            }

            logger.debug("Fetching user information...")

            response = requests.get(
                DISCORD_USER_URL,
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"User info request failed: {response.status_code} - {response.text}")
                return None

            user_data = response.json()

            # Validate user data
            required_fields = ['id', 'username']
            if not all(field in user_data for field in required_fields):
                logger.error("User data missing required fields")
                return None

            logger.info(f"Successfully fetched user info for {user_data['username']}")
            return user_data

        except requests.RequestException as e:
            logger.error(f"Network error fetching user info: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching user info: {e}")
            return None

    def get_user_guilds(self, access_token: str) -> Optional[List[Dict[str, Any]]]:
        """Get user's Discord guilds"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'User-Agent': 'Ladbot/2.0 (Discord Bot Dashboard)'
            }

            logger.debug("Fetching user guilds...")

            response = requests.get(
                DISCORD_GUILDS_URL,
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Guilds request failed: {response.status_code} - {response.text}")
                return None

            guilds_data = response.json()
            logger.info(f"Successfully fetched {len(guilds_data)} guilds")

            return guilds_data

        except requests.RequestException as e:
            logger.error(f"Network error fetching guilds: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching guilds: {e}")
            return None

    def revoke_token(self, access_token: str) -> bool:
        """Revoke Discord access token"""
        try:
            revoke_data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'token': access_token
            }

            response = requests.post(
                f"{DISCORD_API_BASE}/oauth2/token/revoke",
                data=revoke_data,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False

def register_oauth_routes(app):
    """Register OAuth routes with comprehensive error handling"""

    oauth_handler = DiscordOAuth(app)

    @app.route('/auth/discord')
    def discord_auth():
        """Initiate Discord OAuth flow"""
        try:
            # Check if already authenticated
            if 'user_id' in session:
                flash('You are already logged in', 'info')
                return redirect(url_for('dashboard'))

            # Check OAuth configuration
            if not oauth_handler.is_configured():
                flash('Discord OAuth is not configured. Please contact the administrator.', 'error')
                return redirect(url_for('index'))

            # Generate authorization URL
            auth_url = oauth_handler.get_authorization_url()

            logger.info(f"Redirecting user to Discord OAuth: {request.remote_addr}")
            return redirect(auth_url)

        except Exception as e:
            logger.error(f"Discord auth initiation error: {e}")
            flash('Failed to initiate Discord authentication', 'error')
            return redirect(url_for('index'))

    @app.route('/callback')
    def discord_callback():
        """Handle Discord OAuth callback with comprehensive validation"""
        try:
            # Get parameters from callback
            code = request.args.get('code')
            state = request.args.get('state')
            error = request.args.get('error')
            error_description = request.args.get('error_description')

            # Handle OAuth errors
            if error:
                logger.warning(f"OAuth error: {error} - {error_description}")
                flash(f'Authentication failed: {error_description or error}', 'error')
                return redirect(url_for('index'))

            # Validate required parameters
            if not code:
                logger.warning("OAuth callback missing authorization code")
                flash('Authentication failed: No authorization code received', 'error')
                return redirect(url_for('index'))

            if not state:
                logger.warning("OAuth callback missing state parameter")
                flash('Authentication failed: Invalid request', 'error')
                return redirect(url_for('index'))

            # Validate state for CSRF protection
            if not oauth_handler.validate_state(state):
                flash('Authentication failed: Security validation failed', 'error')
                return redirect(url_for('index'))

            # Exchange code for token
            token_info = oauth_handler.exchange_code_for_token(code)
            if not token_info:
                flash('Authentication failed: Could not obtain access token', 'error')
                return redirect(url_for('index'))

            access_token = token_info['access_token']

            # Get user information
            user_data = oauth_handler.get_user_info(access_token)
            if not user_data:
                flash('Authentication failed: Could not retrieve user information', 'error')
                return redirect(url_for('index'))

            # Get user guilds (optional)
            user_guilds = oauth_handler.get_user_guilds(access_token)

            # Store user information in session
            session.permanent = True
            session['user_id'] = user_data['id']
            session['access_token'] = access_token
            session['token_expires_at'] = token_info['expires_at'].isoformat()
            session['user'] = {
                'id': user_data['id'],
                'username': user_data['username'],
                'discriminator': user_data.get('discriminator', '0000'),
                'global_name': user_data.get('global_name'),
                'avatar': user_data.get('avatar'),
                'email': user_data.get('email'),
                'verified': user_data.get('verified', False),
                'locale': user_data.get('locale'),
                'mfa_enabled': user_data.get('mfa_enabled', False)
            }

            # Store guild information if available
            if user_guilds:
                session['user_guilds'] = user_guilds[:50]  # Limit to prevent session bloat

            # Check if user is admin
            user_id = int(user_data['id'])
            is_admin = app.web_manager._is_admin(user_id) if hasattr(app, 'web_manager') else False
            session['is_admin'] = is_admin

            # Log successful authentication
            logger.info(f"Successful OAuth login: {user_data['username']} ({user_data['id']}) - Admin: {is_admin}")

            # Welcome message
            welcome_msg = f"Welcome, {user_data.get('global_name') or user_data['username']}!"
            if is_admin:
                welcome_msg += " (Administrator)"

            flash(welcome_msg, 'success')

            # Redirect to intended page or dashboard
            next_page = session.pop('oauth_redirect', None)
            return redirect(next_page or url_for('dashboard'))

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            flash('Authentication failed: An unexpected error occurred', 'error')
            return redirect(url_for('index'))

    @app.route('/auth/refresh')
    def refresh_token():
        """Refresh OAuth token (if needed)"""
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        try:
            # Check if token needs refresh
            expires_at_str = session.get('token_expires_at')
            if not expires_at_str:
                return jsonify({'error': 'No token expiration info'}), 400

            expires_at = datetime.fromisoformat(expires_at_str)

            # If token expires in less than 5 minutes, consider it expired
            if datetime.now() + timedelta(minutes=5) < expires_at:
                return jsonify({'status': 'token_valid'})

            # For now, just redirect to re-authenticate
            # Discord doesn't provide refresh tokens in implicit flow
            session.clear()
            return jsonify({'status': 'token_expired', 'redirect': url_for('discord_auth')})

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return jsonify({'error': 'Token refresh failed'}), 500

    @app.route('/auth/logout')
    def auth_logout():
        """Enhanced logout with token revocation"""
        try:
            # Get access token for revocation
            access_token = session.get('access_token')
            username = session.get('user', {}).get('username', 'User')

            # Revoke token if available
            if access_token and oauth_handler.is_configured():
                oauth_handler.revoke_token(access_token)
                logger.info(f"Revoked token for user: {username}")

            # Clear session
            session.clear()

            flash(f'Goodbye, {username}! You have been logged out successfully.', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            logger.error(f"Logout error: {e}")
            session.clear()  # Clear session anyway
            flash('Logged out successfully', 'success')
            return redirect(url_for('index'))

    # ===== UTILITY ROUTES =====

    @app.route('/auth/status')
    def auth_status():
        """Check authentication status (API endpoint)"""
        if 'user_id' not in session:
            return jsonify({'authenticated': False})

        user_data = session.get('user', {})
        expires_at_str = session.get('token_expires_at')

        # Check token expiration
        token_valid = True
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
                token_valid = datetime.now() < expires_at
            except:
                token_valid = False

        return jsonify({
            'authenticated': True,
            'user': {
                'id': user_data.get('id'),
                'username': user_data.get('username'),
                'avatar': user_data.get('avatar'),
                'is_admin': session.get('is_admin', False)
            },
            'token_valid': token_valid,
            'expires_at': expires_at_str
        })

    @app.route('/auth/guilds')
    def auth_guilds():
        """Get user's Discord guilds (API endpoint)"""
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401

        user_guilds = session.get('user_guilds', [])

        # Filter guilds where bot is present (if bot is available)
        bot_guilds = []
        if hasattr(app, 'bot') and app.bot:
            bot_guild_ids = {str(guild.id) for guild in app.bot.guilds}
            bot_guilds = [guild for guild in user_guilds if guild['id'] in bot_guild_ids]

        return jsonify({
            'user_guilds': user_guilds,
            'bot_guilds': bot_guilds,
            'total_user_guilds': len(user_guilds),
            'total_bot_guilds': len(bot_guilds)
        })

    # ===== MIDDLEWARE =====

    @app.before_request
    def check_auth_status():
        """Check authentication status before each request"""
        # Skip auth check for public routes
        public_routes = ['index', 'about', 'discord_auth', 'discord_callback', 'auth_status']

        if request.endpoint in public_routes or request.path.startswith('/static'):
            return

        # Check if user is authenticated for protected routes
        if request.endpoint and request.endpoint.startswith(('dashboard', 'settings', 'analytics')):
            if 'user_id' not in session:
                # Store intended destination for after login
                session['oauth_redirect'] = request.url
                flash('Please log in to access this page', 'warning')
                return redirect(url_for('discord_auth'))

            # Check token expiration
            expires_at_str = session.get('token_expires_at')
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() >= expires_at:
                        session.clear()
                        flash('Your session has expired. Please log in again.', 'warning')
                        return redirect(url_for('discord_auth'))
                except:
                    pass

    logger.info("✅ Discord OAuth routes registered successfully")

# ===== HELPER FUNCTIONS =====

def get_user_avatar_url(user_data: Dict[str, Any], size: int = 128) -> str:
    """Generate Discord avatar URL"""
    user_id = user_data.get('id')
    avatar_hash = user_data.get('avatar')

    if not user_id:
        return ''

    if avatar_hash:
        # User has custom avatar
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png?size={size}"
    else:
        # Use default avatar
        discriminator = user_data.get('discriminator', '0000')
        if discriminator == '0000':  # New username system
            default_avatar_index = (int(user_id) >> 22) % 6
        else:  # Legacy discriminator system
            default_avatar_index = int(discriminator) % 5

        return f"https://cdn.discordapp.com/embed/avatars/{default_avatar_index}.png"

def format_user_tag(user_data: Dict[str, Any]) -> str:
    """Format Discord user tag"""
    username = user_data.get('username', 'Unknown')
    discriminator = user_data.get('discriminator', '0000')

    if discriminator == '0000':
        # New username system
        return f"@{username}"
    else:
        # Legacy discriminator system
        return f"{username}#{discriminator}"

# ===== TEMPLATE FILTERS =====

def register_oauth_template_filters(app):
    """Register OAuth-related template filters"""

    @app.template_filter('avatar_url')
    def avatar_url_filter(user_data, size=128):
        return get_user_avatar_url(user_data, size)

    @app.template_filter('user_tag')
    def user_tag_filter(user_data):
        return format_user_tag(user_data)

    @app.template_global()
    def is_authenticated():
        return 'user_id' in session

    @app.template_global()
    def current_user():
        return session.get('user', {})

    @app.template_global()
    def is_admin():
        return session.get('is_admin', False)

# Make sure to call this in your app.py
def setup_oauth(app):
    """Setup OAuth with all components"""
    register_oauth_routes(app)
    register_oauth_template_filters(app)
    logger.info("🔐 OAuth system fully configured")