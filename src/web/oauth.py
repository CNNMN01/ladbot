"""
Discord OAuth implementation for Ladbot Dashboard - Standalone Functions
"""
import os
import requests
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)


def get_discord_oauth_url(client_id, redirect_uri, scope='identify'):
    """Generate Discord OAuth login URL"""
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': scope
    }
    return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"


def exchange_code_for_token(code, client_id, client_secret, redirect_uri):
    """Exchange OAuth code for access token"""
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"OAuth token exchange failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in token exchange: {e}")
        return None


def get_user_info(access_token):
    """Get user information from Discord"""
    headers = {'Authorization': f'Bearer {access_token}'}

    try:
        response = requests.get('https://discord.com/api/users/@me', headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get user info: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting user info: {e}")
        return None


def revoke_token(access_token, client_id, client_secret):
    """Revoke an access token"""
    data = {
        'token': access_token,
        'client_id': client_id,
        'client_secret': client_secret
    }

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        response = requests.post('https://discord.com/api/oauth2/token/revoke', data=data, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")
        return False


# Legacy class-based interface for backward compatibility
class DiscordOAuth:
    """Legacy class-based OAuth interface"""

    def __init__(self):
        self.client_id = os.getenv('DISCORD_CLIENT_ID')
        self.client_secret = os.getenv('DISCORD_CLIENT_SECRET')
        self.redirect_uri = os.getenv('DISCORD_REDIRECT_URI')
        self.base_url = 'https://discord.com/api'

    def get_login_url(self):
        """Generate Discord OAuth login URL"""
        return get_discord_oauth_url(self.client_id, self.redirect_uri)

    def exchange_code(self, code):
        """Exchange OAuth code for access token"""
        return exchange_code_for_token(code, self.client_id, self.client_secret, self.redirect_uri)

    def get_user_info(self, access_token):
        """Get user information from Discord"""
        return get_user_info(access_token)


# Global instance for backward compatibility
oauth = DiscordOAuth()


# Utility functions for validation
def validate_oauth_config():
    """Validate OAuth configuration"""
    client_id = os.getenv('DISCORD_CLIENT_ID')
    client_secret = os.getenv('DISCORD_CLIENT_SECRET')
    redirect_uri = os.getenv('DISCORD_REDIRECT_URI')

    if not client_id:
        logger.warning("DISCORD_CLIENT_ID not set - OAuth login will not work")
        return False

    if not client_secret:
        logger.warning("DISCORD_CLIENT_SECRET not set - OAuth login will not work")
        return False

    if not redirect_uri:
        logger.warning("DISCORD_REDIRECT_URI not set - OAuth login will not work")
        return False

    return True


def get_oauth_status():
    """Get OAuth configuration status"""
    return {
        'configured': validate_oauth_config(),
        'client_id': os.getenv('DISCORD_CLIENT_ID'),
        'redirect_uri': os.getenv('DISCORD_REDIRECT_URI'),
        'has_secret': bool(os.getenv('DISCORD_CLIENT_SECRET'))
    }