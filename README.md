# Ladbot

A comprehensive Discord entertainment bot with 55+ working command modules, interactive games, weather services, advanced admin management tools, and a professional web dashboard.

## Features

### Discord Bot
- 55+ commands across multiple categories (admin, entertainment, utility, information)
- Interactive games and entertainment features
- Weather integration with OpenWeatherMap API
- Cryptocurrency data and market information
- Reddit content integration
- Bible verse lookup
- ASCII art generation
- 8-ball magic responses
- Dice rolling and random generators
- Admin-only moderation tools
- Auto-response system
- Comprehensive error handling and logging

### Web Dashboard
- Real Discord OAuth authentication
- Live bot statistics and performance monitoring
- Interactive guild settings management
- Comprehensive analytics with data export
- Admin permission controls
- Professional Bootstrap 5 UI
- Real-time updates and auto-refresh
- Mobile-responsive design

## Installation

### Prerequisites
- Python 3.8 or higher
- Discord Bot Token
- Discord OAuth Application

### Setup

1. Clone the repository:
git clone https://github.com/your-username/ladbot.git
cd ladbot

2. Create virtual environment:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

3. Install dependencies:
pip install -r requirements.txt

4. Configure environment variables:
Copy .env.example to .env and fill in your values:

```
BOT_TOKEN=your_discord_bot_token
BOT_PREFIX=l.
ADMIN_IDS=your_discord_user_id,another_admin_id
DISCORD_CLIENT_ID=your_discord_application_id
DISCORD_CLIENT_SECRET=your_discord_client_secret
DISCORD_REDIRECT_URI=http://localhost:8080/callback
WEB_SECRET_KEY=your-secure-secret-key
```

5. Run the bot:
python main.py

## Discord Setup

### Bot Token
1. Go to https://discord.com/developers/applications
2. Create a new application or select existing
3. Go to Bot section
4. Copy the bot token to BOT_TOKEN in .env

### OAuth Setup
1. In the same application, go to OAuth2 > General
2. Copy Client ID to DISCORD_CLIENT_ID in .env
3. Generate and copy Client Secret to DISCORD_CLIENT_SECRET in .env
4. Add redirect URL: http://localhost:8080/callback (or your domain for production)

### Bot Permissions
Invite your bot with these permissions:
- Read Messages
- Send Messages
- Embed Links
- Add Reactions
- Use External Emojis
- Manage Messages (for admin commands)

## Usage

### Discord Commands
- `l.help` - Show all available commands
- `l.ping` - Check bot latency
- `l.weather <location>` - Get weather information
- `l.crypto <symbol>` - Get cryptocurrency data
- `l.8ball <question>` - Magic 8-ball responses
- `l.joke` - Random jokes
- `l.roll <dice>` - Roll dice (e.g., l.roll 2d6)
- `l.ascii <text>` - Generate ASCII art
- `l.settings` - Manage bot settings (admin only)

### Web Dashboard
1. Visit http://localhost:8080 (or your deployed URL)
2. Click "Login with Discord"
3. Authorize the application
4. Access admin dashboard (requires admin permissions)

Dashboard features:
- Real-time bot statistics
- Server management
- Command usage analytics
- Performance monitoring
- Settings configuration

## Admin Configuration

### Adding Admins
Add Discord user IDs to ADMIN_IDS in .env file:
ADMIN_IDS=123456789012345678,987654321098765432

To get Discord user IDs:
1. Enable Developer Mode in Discord settings
2. Right-click on user and select "Copy User ID"

### Admin Commands
- `l.settings` - Configure bot settings for servers
- `l.reload` - Reload bot modules
- `l.logs` - View recent bot logs
- `l.console` - Execute admin commands

## Optional APIs

### Weather (Optional)
Get free API key at https://openweathermap.org/api
Add OPENWEATHER_API_KEY=your_key to .env
Restart bot (1000 calls/day free tier)

## Project Structure
```
ladbot/
├── src/
│   ├── config/
│   │   └── settings.py         # Configuration management
│   ├── bot/
│   │   └── ladbot.py          # Main bot class
│   ├── cogs/                  # Command modules
│   │   ├── admin/             # Admin-only commands
│   │   ├── entertainment/     # Games and fun commands
│   │   ├── utility/           # Utility commands
│   │   └── information/       # Information commands
│   ├── utils/                 # Shared utilities
│   └── web/                   # Web dashboard
│       ├── templates/         # HTML templates
│       ├── app.py            # Flask application
│       ├── routes.py         # Web routes
│       └── oauth.py          # Discord OAuth
├── logs/                      # Log files
├── data/                      # Bot data and configuration
├── main.py                    # Entry point
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create from .env.example)
└── README.md
```
## Development

### Adding New Commands

1. Create a new .py file in the appropriate cogs/ subdirectory
2. Follow the established cog class structure:
```
from discord.ext import commands
from utils.decorators import guild_setting_enabled

class MyCog(commands.Cog):
   def __init__(self, bot):
       self.bot = bot

   @commands.command()
   @guild_setting_enabled("my_command")
   async def my_command(self, ctx):
       await ctx.send("Hello world!")

async def setup(bot):
   await bot.add_cog(MyCog(bot))
```
3. Restart bot or use l.reload to load new cog

### Testing

Test locally:
python main.py

Verify web dashboard:
Visit http://localhost:8080

### Logging

Logs are stored in logs/bot.log with rotation:
- INFO: General bot operations
- WARNING: Non-critical issues
- ERROR: Command failures and critical issues
- DEBUG: Detailed troubleshooting info (when DEBUG=true)

## Deployment

### Railway (Recommended)

1. Push code to GitHub
2. Connect repository to Railway.app
3. Railway auto-detects Python and deploys
4. Set environment variables in Railway dashboard
5. Update Discord OAuth redirect URL to your Railway domain

### Other Platforms

- Heroku: heroku create your-bot-name
- DigitalOcean App Platform
- AWS/Google Cloud/Azure
- VPS with nginx reverse proxy

### Production Considerations

- Use secure WEB_SECRET_KEY
- Set DEBUG=false
- Configure proper logging rotation
- Set up monitoring and health checks
- Enable only necessary bot intents
- Regular backups of bot data

## Troubleshooting

### Bot Won't Start
1. Check .env file has real values (not placeholders)
2. Verify bot token is correct
3. Install all requirements: pip install -r requirements.txt
4. Check Python version: python --version (need 3.8+)

### Permission Errors
1. Enable required intents in Discord Developer Portal
2. Ensure bot has necessary server permissions
3. Check admin IDs are correctly set in .env

### Web Dashboard Issues
1. Verify Discord OAuth settings match your domain
2. Check DISCORD_REDIRECT_URI matches exactly
3. Ensure admin IDs are correct for dashboard access

### Command Not Working
1. Check if command is enabled in settings
2. Verify required permissions
3. Use l.reload to refresh cogs after changes

## Statistics

Current bot capabilities:
- 55+ working commands with aliases
- 25+ loaded cogs and modules
- Multi-difficulty interactive games
- Cross-platform weather support
- Comprehensive admin tools
- Production-ready database system
- Full web dashboard with analytics
- Real Discord OAuth authentication

## Contributing

1. Fork the repository
2. Create a feature branch: git checkout -b feature-name
3. Make your changes with appropriate tests
4. Ensure all tests pass
5. Submit a pull request with detailed description

## Support

- Use l.feedback <message> to contact developers
- Check GitHub Issues for known problems
- Review logs/bot.log for debugging information

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- discord.py library for Discord API integration
- OpenWeatherMap for weather data
- CoinGecko for cryptocurrency data
- Bootstrap and Font Awesome for web UI
- All contributors and testers

Ladbot - Built with Python, powered by Discord.py, designed for entertainment and management.