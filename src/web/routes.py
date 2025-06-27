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

    # Import analytics
    try:
        from utils.analytics import analytics as bot_analytics
    except ImportError:
        bot_analytics = None

    # Get detailed analytics data
    analytics_data = {}
    if app.bot:
        # Get usage trends and user activity if analytics available
        if bot_analytics:
            usage_trends = bot_analytics.get_usage_trends(24)
            top_commands = bot_analytics.get_top_commands(10)
            user_activity = bot_analytics.get_user_activity_stats()
        else:
            usage_trends = []
            top_commands = []
            user_activity = {
                'active_users_24h': 0,
                'total_commands_24h': 0,
                'peak_hour': '00:00',
                'peak_hour_usage': 0,
                'hourly_breakdown': {}
            }

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

        # Guild analytics
        guild_data = []
        for guild in app.bot.guilds:
            guild_data.append({
                'name': guild.name,
                'member_count': guild.member_count,
                'created_at': guild.created_at.isoformat(),
                'id': guild.id
            })

        analytics_data = {
            'usage_trends': usage_trends,
            'top_commands': top_commands,
            'user_activity': user_activity,
            'guild_data': guild_data,
            'total_users': len(app.bot.users),
            'total_guilds': len(app.bot.guilds),
            'bot_latency': round(app.bot.latency * 1000),
            'uptime': uptime_str,
            'total_commands': len(app.bot.commands),
            'loaded_cogs': len(app.bot.cogs)
        }

    return render_template('analytics.html', analytics=analytics_data, user=session.get('user'))