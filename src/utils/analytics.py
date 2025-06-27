"""
Analytics tracking for Ladbot
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class BotAnalytics:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.analytics_file = self.data_dir / "analytics.json"

        # In-memory tracking
        self.command_usage = defaultdict(int)
        self.hourly_usage = defaultdict(int)
        self.daily_users = set()
        self.recent_activity = deque(maxlen=100)  # Last 100 activities

        # Load existing data
        self.load_analytics()

    def load_analytics(self):
        """Load analytics from file"""
        try:
            if self.analytics_file.exists():
                with open(self.analytics_file, 'r') as f:
                    data = json.load(f)
                    self.command_usage.update(data.get('command_usage', {}))
                    self.hourly_usage.update(data.get('hourly_usage', {}))

                    # Load recent activity
                    for activity in data.get('recent_activity', []):
                        self.recent_activity.append(activity)

                logger.info("📊 Analytics data loaded")
        except Exception as e:
            logger.error(f"Failed to load analytics: {e}")

    def save_analytics(self):
        """Save analytics to file"""
        try:
            data = {
                'command_usage': dict(self.command_usage),
                'hourly_usage': dict(self.hourly_usage),
                'recent_activity': list(self.recent_activity),
                'last_updated': datetime.now().isoformat()
            }

            with open(self.analytics_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save analytics: {e}")

    def track_command(self, command_name, user_id, guild_id):
        """Track command usage"""
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")

        # Track command usage
        self.command_usage[command_name] += 1
        self.hourly_usage[hour_key] += 1
        self.daily_users.add(user_id)

        # Track recent activity
        activity = {
            'timestamp': now.isoformat(),
            'command': command_name,
            'user_id': str(user_id),
            'guild_id': str(guild_id),
            'hour': hour_key
        }
        self.recent_activity.append(activity)

        # Save periodically
        if len(self.recent_activity) % 10 == 0:
            self.save_analytics()

    def get_usage_trends(self, hours=24):
        """Get usage trends for the last N hours"""
        now = datetime.now()
        trends = []

        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime("%Y-%m-%d-%H")
            usage_count = self.hourly_usage.get(hour_key, 0)

            trends.append({
                'hour': hour.strftime("%H:00"),
                'date': hour.strftime("%Y-%m-%d"),
                'usage': usage_count,
                'timestamp': hour.isoformat()
            })

        return list(reversed(trends))  # Oldest to newest

    def get_top_commands(self, limit=10):
        """Get most used commands"""
        sorted_commands = sorted(
            self.command_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_commands[:limit]

    def get_user_activity_stats(self):
        """Get user activity statistics"""
        now = datetime.now()

        # Activity in last 24 hours
        day_ago = now - timedelta(days=1)
        recent_activities = [
            a for a in self.recent_activity
            if datetime.fromisoformat(a['timestamp']) > day_ago
        ]

        # Unique users in last 24 hours
        unique_users = len(set(a['user_id'] for a in recent_activities))

        # Peak hour analysis
        hour_activity = defaultdict(int)
        for activity in recent_activities:
            hour = datetime.fromisoformat(activity['timestamp']).hour
            hour_activity[hour] += 1

        peak_hour = max(hour_activity.items(), key=lambda x: x[1]) if hour_activity else (0, 0)

        return {
            'active_users_24h': unique_users,
            'total_commands_24h': len(recent_activities),
            'peak_hour': f"{peak_hour[0]:02d}:00",
            'peak_hour_usage': peak_hour[1],
            'hourly_breakdown': dict(hour_activity)
        }


# Global analytics instance
analytics = BotAnalytics()