"""
Advanced Settings Manager for Ladbot Web Interface
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class SettingsManager:
    """Manages bot settings with web interface support"""

    def __init__(self, bot):
        self.bot = bot
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.settings_file = self.data_dir / "web_settings.json"
        self.guild_settings_dir = self.data_dir / "guild_settings"

        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.guild_settings_dir.mkdir(exist_ok=True)

        # Load global settings
        self.global_settings = self.load_global_settings()

    def load_global_settings(self) -> Dict[str, Any]:
        """Load global bot settings"""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            return self.get_default_global_settings()
        except Exception as e:
            logger.error(f"Error loading global settings: {e}")
            return self.get_default_global_settings()

    def save_global_settings(self) -> bool:
        """Save global settings to file"""
        try:
            self.global_settings['last_updated'] = datetime.now().isoformat()
            with open(self.settings_file, 'w') as f:
                json.dump(self.global_settings, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving global settings: {e}")
            return False

    def get_default_global_settings(self) -> Dict[str, Any]:
        """Get default global settings"""
        return {
            'bot_name': 'Ladbot',
            'default_prefix': 'l.',
            'max_command_cooldown': 5,
            'error_logging': True,
            'analytics_enabled': True,
            'auto_backup': False,
            'maintenance_mode': False,
            'welcome_message_enabled': True,
            'default_embed_color': '#4e73df',
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }

    def load_guild_settings(self, guild_id: int) -> Dict[str, Any]:
        """Load settings for specific guild"""
        try:
            guild_file = self.guild_settings_dir / f"{guild_id}.json"
            if guild_file.exists():
                with open(guild_file, 'r') as f:
                    return json.load(f)
            return self.get_default_guild_settings()
        except Exception as e:
            logger.error(f"Error loading guild {guild_id} settings: {e}")
            return self.get_default_guild_settings()

    def save_guild_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """Save settings for specific guild"""
        try:
            guild_file = self.guild_settings_dir / f"{guild_id}.json"
            settings['last_updated'] = datetime.now().isoformat()
            settings['guild_id'] = guild_id

            with open(guild_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving guild {guild_id} settings: {e}")
            return False

    def get_default_guild_settings(self) -> Dict[str, Any]:
        """Get default guild settings"""
        return {
            'prefix': self.global_settings.get('default_prefix', 'l.'),
            'autoresponses': False,
            'welcome_messages': True,
            'moderation_enabled': True,
            'logging_enabled': True,
            'command_cooldown': 3,
            'embed_color': self.global_settings.get('default_embed_color', '#4e73df'),
            'disabled_commands': [],
            'admin_roles': [],
            'moderator_roles': [],
            'auto_delete_commands': False,
            'spam_protection': True,
            'nsfw_filter': True,
            'created_at': datetime.now().isoformat()
        }

    def get_all_commands(self) -> List[Dict[str, str]]:
        """Get all available bot commands"""
        commands = []
        for command in self.bot.commands:
            commands.append({
                'name': command.name,
                'description': command.help or 'No description available',
                'category': getattr(command.cog, 'qualified_name', 'General') if command.cog else 'General',
                'aliases': list(command.aliases) if command.aliases else []
            })
        return sorted(commands, key=lambda x: x['category'])

    def get_guild_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get roles for a specific guild"""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return []

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
            return sorted(roles, key=lambda x: x['name'])
        except Exception as e:
            logger.error(f"Error getting roles for guild {guild_id}: {e}")
            return []

    def apply_guild_settings(self, guild_id: int, settings: Dict[str, Any]) -> bool:
        """Apply settings to guild and update bot configuration"""
        try:
            # Save to file
            if not self.save_guild_settings(guild_id, settings):
                return False

            # Update bot's runtime configuration
            if hasattr(self.bot, 'settings_cache'):
                self.bot.settings_cache[guild_id] = settings

            logger.info(f"Applied settings for guild {guild_id}")
            return True
        except Exception as e:
            logger.error(f"Error applying settings for guild {guild_id}: {e}")
            return False

    def get_settings_categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get organized settings categories for web interface"""
        return {
            'General': [
                {
                    'key': 'prefix',
                    'name': 'Command Prefix',
                    'type': 'text',
                    'description': 'The prefix used for bot commands',
                    'default': 'l.',
                    'validation': {'min_length': 1, 'max_length': 5}
                },
                {
                    'key': 'embed_color',
                    'name': 'Embed Color',
                    'type': 'color',
                    'description': 'Default color for bot embeds',
                    'default': '#4e73df'
                },
                {
                    'key': 'command_cooldown',
                    'name': 'Command Cooldown (seconds)',
                    'type': 'number',
                    'description': 'Default cooldown between commands',
                    'default': 3,
                    'validation': {'min': 0, 'max': 60}
                }
            ],
            'Features': [
                {
                    'key': 'autoresponses',
                    'name': 'Auto Responses',
                    'type': 'boolean',
                    'description': 'Enable automatic responses to keywords',
                    'default': False
                },
                {
                    'key': 'welcome_messages',
                    'name': 'Welcome Messages',
                    'type': 'boolean',
                    'description': 'Send welcome messages to new members',
                    'default': True
                },
                {
                    'key': 'spam_protection',
                    'name': 'Spam Protection',
                    'type': 'boolean',
                    'description': 'Enable spam detection and prevention',
                    'default': True
                }
            ],
            'Moderation': [
                {
                    'key': 'moderation_enabled',
                    'name': 'Moderation Features',
                    'type': 'boolean',
                    'description': 'Enable moderation commands and features',
                    'default': True
                },
                {
                    'key': 'auto_delete_commands',
                    'name': 'Auto Delete Commands',
                    'type': 'boolean',
                    'description': 'Automatically delete command messages',
                    'default': False
                },
                {
                    'key': 'nsfw_filter',
                    'name': 'NSFW Filter',
                    'type': 'boolean',
                    'description': 'Filter inappropriate content',
                    'default': True
                }
            ],
            'Commands': [
                {
                    'key': 'disabled_commands',
                    'name': 'Disabled Commands',
                    'type': 'multiselect',
                    'description': 'Commands to disable in this server',
                    'default': [],
                    'options': 'commands'  # Special flag to load from bot commands
                }
            ],
            'Permissions': [
                {
                    'key': 'admin_roles',
                    'name': 'Admin Roles',
                    'type': 'multiselect',
                    'description': 'Roles with admin bot permissions',
                    'default': [],
                    'options': 'roles'  # Special flag to load from guild roles
                },
                {
                    'key': 'moderator_roles',
                    'name': 'Moderator Roles',
                    'type': 'multiselect',
                    'description': 'Roles with moderator bot permissions',
                    'default': [],
                    'options': 'roles'
                }
            ]
        }