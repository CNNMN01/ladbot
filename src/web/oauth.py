"""
Discord OAuth implementation for Ladbot Dashboard
"""
import os
import requests
from urllib.parse import urlencode
from flask import session, request, redirect, url_for, flash
import logging

logger = logging.getLogger(__name__)


class DiscordOAuth:
    def __init__(self):
        self.client_id = os.getenv('DISCORD_CLIENT_ID')
        self.client_secret = os.getenv('DISCORD_CLIENT_SECRET')
        self.redirect_uri = os.getenv('DISCORD_REDIRECT_URI')
        self.base_url = 'https://discord.com/api'

    def get_login_url(self):
        """Generate Discord OAuth login URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'identify'
        }
        return f"https://discord.com/api/oauth2/authorize?{urlencode(params)}"

    def exchange_code(self, code):
        """Exchange OAuth code for access token"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri
        }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(f"{self.base_url}/oauth2/token", data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"OAuth token exchange failed: {e}")
            return None

    def get_user_info(self, access_token):
        """Get user information from Discord"""
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.get(f"{self.base_url}/users/@me", headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None


oauth = DiscordOAuth()