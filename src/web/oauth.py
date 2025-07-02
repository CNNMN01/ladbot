"""
Discord OAuth Integration for Ladbot Web Dashboard
Complete OAuth2 flow with comprehensive error handling and security features
"""

import requests
import logging
import traceback
from urllib.parse import urlencode, parse_qs
from flask import session, request, redirect, url_for, flash, current_app, jsonify
from datetime import datetime, timedelta
import secrets
import hashlib
import base64
from typing import Dict, Any, Optional, Tuple, List

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

        # Clear used state
        session.pop('oauth_state', None)
        session.pop('oauth_timestamp', None)

        # Check if state exists
        if not stored_state or not stored_timestamp:
            logger.warning("OAuth state validation failed: No stored state")
            return False

        # Check if state matches
        if stored_state != received_state:
            logger.warning("OAuth state validation failed: State mismatch")
            return False

        # Check if state is not expired (10 minutes max)
        state_age = datetime.now().timestamp() - stored_timestamp
        if state_age > 600:  # 10 minutes
            logger.warning("OAuth state validation failed: State expired")
            return False

        return True

    def get_auth_url(self) -> str:
        """Generate Discord OAuth authorization URL"""
        if not self.is_configured():
            logger.error("OAuth not configured - cannot generate auth URL")
            return ""

        state = self.generate_state()

        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(OAUTH_SCOPES),
            'state': state
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

            # Validate guilds data
            if not isinstance(guilds_data, list):
                logger.error("Guilds data is not a list")
                return None

            # Filter and process guild data
            processed_guilds = []
            for guild in guilds_data:
                if isinstance(guild, dict) and 'id' in guild and 'name' in guild:
                    processed_guilds.append({
                        'id': guild['id'],
                        'name': guild['name'],
                        'icon': guild.get('icon'),
                        'owner': guild.get('owner', False),
                        'permissions': guild.get('permissions', '0'),
                        'features': guild.get('features', [])
                    })

            logger.info(f"Successfully fetched {len(processed_guilds)} guilds")
            return processed_guilds

        except requests.RequestException as e:
            logger.error(f"Network error fetching user guilds: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching user guilds: {e}")
            return None

    def revoke_token(self, access_token: str) -> bool:
        """Revoke access token"""
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

            if response.status_code == 200:
                logger.info("Successfully revoked access token")
                return True
            else:
                logger.warning(f"Token revocation failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error revoking token: {e}")
            return False


# ===== FLASK ROUTE REGISTRATION =====

def register_oauth_routes(app):
    """Register OAuth routes with the Flask app"""

    oauth = DiscordOAuth(app)

    @app.route('/auth/discord')
    def discord_auth():
        """Initiate Discord OAuth flow"""
        if not oauth.is_configured():
            flash('OAuth not configured. Please contact administrator.', 'error')
            return redirect(url_for('index'))

        auth_url = oauth.get_auth_url()
        if not auth_url:
            flash('Unable to generate authorization URL.', 'error')
            return redirect(url_for('index'))

        return redirect(auth_url)

    @app.route('/callback')
    def oauth_callback():
        """Handle OAuth callback from Discord"""
        try:
            # Check for errors
            error = request.args.get('error')
            if error:
                error_description = request.args.get('error_description', 'Unknown error')
                logger.warning(f"OAuth error: {error} - {error_description}")
                flash(f'Authentication failed: {error_description}', 'error')
                return redirect(url_for('index'))

            # Get authorization code and state
            code = request.args.get('code')
            state = request.args.get('state')

            if not code:
                flash('No authorization code received.', 'error')
                return redirect(url_for('index'))

            # Validate state (CSRF protection)
            if not oauth.validate_state(state):
                flash('Invalid state parameter. Please try again.', 'error')
                return redirect(url_for('index'))

            # Exchange code for token
            token_info = oauth.exchange_code_for_token(code)
            if not token_info:
                flash('Failed to obtain access token.', 'error')
                return redirect(url_for('index'))

            access_token = token_info['access_token']

            # Get user information
            user_data = oauth.get_user_info(access_token)
            if not user_data:
                flash('Failed to retrieve user information.', 'error')
                return redirect(url_for('index'))

            # Get user guilds (optional, with error handling)
            user_guilds = None
            try:
                user_guilds = oauth.get_user_guilds(access_token)
                if not user_guilds:
                    logger.warning("Could not fetch user guilds (non-critical)")
            except Exception as e:
                logger.warning(f"Non-critical error fetching user guilds: {e}")

            # Store session data
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

            # Redirect to dashboard
            return redirect(url_for('dashboard'))

        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            flash('An unexpected error occurred during authentication.', 'error')
            return redirect(url_for('index'))

    # Token validation middleware
    @app.before_request
    def check_token_expiry():
        """Check if access token is expired before each request"""
        if 'access_token' in session and 'token_expires_at' in session:
            try:
                expires_at = datetime.fromisoformat(session['token_expires_at'])
                if datetime.now() >= expires_at:
                    # Token expired
                    session.clear()
                    if request.endpoint not in ['index', 'discord_auth', 'oauth_callback', 'static']:
                        flash('Your session has expired. Please log in again.', 'warning')
                        return redirect(url_for('discord_auth'))
            except Exception as e:
                logger.warning(f"Error checking token expiry: {e}")

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