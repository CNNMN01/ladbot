// Enhanced Dashboard JavaScript with Real-time Updates and API Error Handling
let refreshInterval;
let isRefreshing = false;
let apiHealthy = true;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Dashboard loaded');
    checkAPIHealth();
    initializeDashboard();
    setupAutoRefresh();
    setupEventListeners();
});

function initializeDashboard() {
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Initialize any charts or widgets
    initializeCharts();

    // Update last refresh time
    updateLastRefreshTime();

    // Show initial API status
    updateAPIStatus(apiHealthy);
}

function setupAutoRefresh() {
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(() => {
        if (!isRefreshing && document.visibilityState === 'visible' && apiHealthy) {
            refreshStats();
        }
    }, 30000);

    console.log('✅ Auto-refresh enabled (30s interval)');
}

function setupEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            refreshStats(true);
        });
    }

    // Analytics refresh button
    const refreshAnalyticsBtn = document.getElementById('refreshAnalyticsBtn');
    if (refreshAnalyticsBtn) {
        refreshAnalyticsBtn.addEventListener('click', function() {
            refreshAnalytics(true);
        });
    }

    // Settings form submission
    const settingsForm = document.getElementById('settingsForm');
    if (settingsForm) {
        settingsForm.addEventListener('submit', handleSettingsSubmit);
    }

    // Guild settings form
    const guildSettingsForm = document.getElementById('guildSettingsForm');
    if (guildSettingsForm) {
        guildSettingsForm.addEventListener('submit', handleGuildSettingsSubmit);
    }

    // Page visibility change - pause/resume refresh
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            clearInterval(refreshInterval);
            console.log('⏸️ Auto-refresh paused (page hidden)');
        } else {
            setupAutoRefresh();
            console.log('▶️ Auto-refresh resumed');
        }
    });

    // API error retry button
    const retryBtn = document.getElementById('api-retry-btn');
    if (retryBtn) {
        retryBtn.addEventListener('click', function() {
            checkAPIHealth();
        });
    }
}

async function checkAPIHealth() {
    try {
        console.log('🔍 Checking API health...');

        const response = await fetch('/api/system/status');
        const data = await response.json();

        if (response.ok && data.status === 'healthy') {
            apiHealthy = true;
            console.log('✅ API is healthy');
            updateAPIStatus(true);
            return true;
        } else {
            apiHealthy = false;
            console.warn('⚠️ API reports unhealthy status:', data);
            updateAPIStatus(false, data.error);
            return false;
        }
    } catch (error) {
        apiHealthy = false;
        console.error('❌ API health check failed:', error);
        updateAPIStatus(false, error.message);
        return false;
    }
}

function updateAPIStatus(healthy, error = null) {
    const statusElement = document.getElementById('api-status');
    if (statusElement) {
        if (healthy) {
            statusElement.innerHTML = `
                <span class="badge bg-success">
                    <i class="fas fa-check-circle"></i> API Connected
                </span>
            `;
        } else {
            statusElement.innerHTML = `
                <span class="badge bg-danger">
                    <i class="fas fa-exclamation-triangle"></i> API Error
                </span>
                <button id="api-retry-btn" class="btn btn-sm btn-outline-warning ms-2">
                    <i class="fas fa-redo"></i> Retry
                </button>
            `;

            // Re-attach event listener for retry button
            const retryBtn = document.getElementById('api-retry-btn');
            if (retryBtn) {
                retryBtn.addEventListener('click', function() {
                    checkAPIHealth();
                });
            }
        }
    }
}

async function refreshStats(manual = false) {
    if (isRefreshing) return;

    isRefreshing = true;

    // Show loading indicator
    const refreshBtn = document.getElementById('refreshBtn');
    const originalBtnContent = refreshBtn ? refreshBtn.innerHTML : '';

    if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        refreshBtn.disabled = true;
    }

    try {
        console.log(`🔄 ${manual ? 'Manual' : 'Auto'} refresh started`);

        // Use the correct API endpoint
        const response = await fetch('/api/stats');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('📊 Fresh stats received:', data);

        // Update API health status
        apiHealthy = true;
        updateAPIStatus(true);

        // Update UI elements with the stats data
        updateStatsDisplay(data);
        updateLastRefreshTime();

        if (manual) {
            showToast('Stats refreshed successfully', 'success');
        }

    } catch (error) {
        console.error('❌ Error refreshing stats:', error);

        // Update API health status
        apiHealthy = false;
        updateAPIStatus(false, error.message);

        if (manual) {
            showToast('Failed to refresh stats: ' + error.message, 'error');
        }

        // Update UI to show error state
        updateStatsDisplay(null, error.message);

    } finally {
        isRefreshing = false;

        // Restore refresh button
        if (refreshBtn) {
            refreshBtn.innerHTML = originalBtnContent;
            refreshBtn.disabled = false;
        }
    }
}

async function refreshAnalytics(manual = false) {
    if (isRefreshing) return;

    isRefreshing = true;
    const refreshBtn = document.getElementById('refreshAnalyticsBtn');
    const originalContent = refreshBtn ? refreshBtn.innerHTML : '';

    // Show loading state
    if (refreshBtn) {
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        refreshBtn.disabled = true;
    }

    try {
        console.log('🔄 Refreshing analytics data...');

        const response = await fetch('/api/analytics/refresh');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.success) {
            updateAnalyticsUI(data.analytics, data.stats);
            updateLastRefreshTime();
            console.log('✅ Analytics refreshed successfully');

            // Show success feedback
            if (manual) {
                showToast('Analytics refreshed successfully', 'success');
            }
        } else {
            throw new Error(data.error || 'Unknown error');
        }

    } catch (error) {
        console.error('❌ Error refreshing analytics:', error);
        if (manual) {
            showToast('Failed to refresh analytics: ' + error.message, 'error');
        }
    } finally {
        isRefreshing = false;
        if (refreshBtn) {
            refreshBtn.innerHTML = originalContent;
            refreshBtn.disabled = false;
        }
    }
}

function updateStatsDisplay(stats, error = null) {
    if (error) {
        // Show error state
        updateElement('bot-status', 'Error');
        updateElement('bot-status-badge', 'bg-danger', 'class');
        return;
    }

    if (!stats) return;

    // Update stat cards
    updateElement('guild-count', stats.guilds || 0);
    updateElement('user-count', (stats.users || 0).toLocaleString());
    updateElement('command-count', stats.commands || 0);
    updateElement('uptime-display', stats.uptime || 'Unknown');

    // Update detailed stats
    updateElement('latency-display', `${stats.latency || 0}ms`);
    updateElement('loaded-cogs', stats.loaded_cogs || 0);
    updateElement('commands-today', stats.commands_today || 0);
    updateElement('session-commands', stats.session_commands || 0);
    updateElement('error-count', stats.error_count || 0);

    // Update status indicators
    const statusElement = document.getElementById('bot-status');
    const statusBadge = document.getElementById('bot-status-badge');

    if (statusElement) {
        statusElement.textContent = stats.bot_status === 'online' ? 'Online' : 'Offline';
    }

    if (statusBadge) {
        statusBadge.className = stats.bot_status === 'online' ?
            'badge bg-success' : 'badge bg-danger';
    }

    // Update progress bars if they exist
    updateProgressBar('memory-progress', stats.memory_usage || 0);
    updateProgressBar('cpu-progress', stats.cpu_usage || 0);

    // Update last updated time
    const lastUpdated = document.getElementById('last-updated');
    if (lastUpdated) {
        lastUpdated.textContent = stats.last_updated || new Date().toLocaleTimeString();
    }
}

function updateAnalyticsUI(analytics, stats) {
    // Update stat cards
    updateElement('total-guilds', analytics.total_guilds || 0);
    updateElement('total-users', (analytics.total_users || 0).toLocaleString());
    updateElement('commands-today', analytics.daily_commands || 0);
    updateElement('bot-latency', `${analytics.bot_latency || 0}ms`);

    // Update bot health
    updateElement('uptime-display', analytics.uptime || 'Unknown');
    updateElement('loaded-cogs', analytics.loaded_cogs || 0);
    updateElement('error-rate', `${analytics.error_rate || 0}%`);

    // Update status indicator
    const statusIndicator = document.getElementById('status-indicator');
    if (statusIndicator) {
        if (analytics.bot_status === 'online') {
            statusIndicator.innerHTML = `
                <i class="fas fa-circle text-success fa-2x"></i>
                <h5 class="text-success mt-2">Online</h5>
            `;
        } else {
            statusIndicator.innerHTML = `
                <i class="fas fa-circle text-danger fa-2x"></i>
                <h5 class="text-danger mt-2">Offline</h5>
            `;
        }
    }

    // Update command stats table
    updateCommandStatsTable(analytics.command_stats);

    // Update server list table
    updateServerListTable(analytics.server_list);

    // Update last updated time
    updateElement('last-updated', analytics.last_updated || new Date().toLocaleString());
}

function updateCommandStatsTable(commandStats) {
    const container = document.getElementById('command-stats-container');
    if (!container) return;

    if (!commandStats || commandStats.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-chart-bar fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Command Data Yet</h5>
                <p class="text-muted">Command usage statistics will appear here as users interact with the bot.</p>
            </div>
        `;
        return;
    }

    const tableHTML = `
        <div class="table-responsive">
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Command</th>
                        <th>Usage Count</th>
                        <th>Percentage</th>
                        <th>Usage Bar</th>
                    </tr>
                </thead>
                <tbody>
                    ${commandStats.map(cmd => `
                        <tr>
                            <td><code>${cmd.name}</code></td>
                            <td><span class="badge bg-primary">${cmd.usage}</span></td>
                            <td>${cmd.percentage}%</td>
                            <td>
                                <div class="progress" style="height: 20px;">
                                    <div class="progress-bar bg-success" role="progressbar" 
                                         style="width: ${cmd.percentage}%" 
                                         aria-valuenow="${cmd.percentage}" 
                                         aria-valuemin="0" aria-valuemax="100">
                                    </div>
                                </div>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = tableHTML;
}

function updateServerListTable(serverList) {
    const container = document.getElementById('server-list-container');
    if (!container) return;

    if (!serverList || serverList.length === 0) {
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="fas fa-server fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">No Server Data Available</h5>
                <p class="text-muted">Server information will appear here once the bot joins servers.</p>
            </div>
        `;
        return;
    }

    const tableHTML = `
        <div class="table-responsive">
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Server Name</th>
                        <th>Members</th>
                        <th>Created</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${serverList.map(server => `
                        <tr>
                            <td>
                                <div class="d-flex align-items-center">
                                    ${server.icon ? 
                                        `<img src="${server.icon}" class="rounded-circle me-2" width="32" height="32">` :
                                        `<div class="bg-primary rounded-circle d-flex align-items-center justify-content-center me-2" style="width: 32px; height: 32px;">
                                            <i class="fas fa-server text-white"></i>
                                         </div>`
                                    }
                                    <strong>${server.name}</strong>
                                </div>
                            </td>
                            <td>
                                <span class="badge bg-secondary">${server.members.toLocaleString()} members</span>
                            </td>
                            <td>${server.created}</td>
                            <td>
                                <span class="badge bg-success">
                                    <i class="fas fa-check-circle"></i> Active
                                </span>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = tableHTML;
}

function updateElement(id, value, attribute = 'textContent') {
    const element = document.getElementById(id);
    if (element) {
        if (attribute === 'textContent') {
            element.textContent = value;
        } else if (attribute === 'innerHTML') {
            element.innerHTML = value;
        } else if (attribute === 'class') {
            element.className = value;
        } else {
            element.setAttribute(attribute, value);
        }
    }
}

function updateProgressBar(id, percentage) {
    const progressBar = document.getElementById(id);
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);

        // Update color based on percentage
        progressBar.className = `progress-bar ${getProgressBarColor(percentage)}`;
    }
}

function getProgressBarColor(percentage) {
    if (percentage < 50) return 'bg-success';
    if (percentage < 75) return 'bg-warning';
    return 'bg-danger';
}

function updateLastRefreshTime() {
    const lastRefreshElement = document.getElementById('last-refresh-time');
    if (lastRefreshElement) {
        lastRefreshElement.textContent = new Date().toLocaleTimeString();
    }

    const lastRefresh = document.getElementById('last-refresh');
    if (lastRefresh) {
        lastRefresh.textContent = 'Last refresh: ' + new Date().toLocaleTimeString();
    }
}

async function handleSettingsSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const settings = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        showToast('Settings saved successfully', 'success');

    } catch (error) {
        console.error('Error saving settings:', error);
        showToast('Failed to save settings', 'error');
    }
}

async function handleGuildSettingsSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const guildId = form.dataset.guildId;
    const formData = new FormData(form);

    // Convert form data to object, handling checkboxes
    const settings = {};
    for (let [key, value] of formData.entries()) {
        settings[key] = value;
    }

    // Handle unchecked checkboxes
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        if (!formData.has(checkbox.name)) {
            settings[checkbox.name] = false;
        } else {
            settings[checkbox.name] = true;
        }
    });

    try {
        const response = await fetch(`/api/guild/${guildId}/settings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        showToast('Guild settings saved successfully', 'success');

    } catch (error) {
        console.error('Error saving guild settings:', error);
        showToast('Failed to save guild settings', 'error');
    }
}

async function resetGuildSettings(guildId) {
    if (!confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/api/guild/${guildId}/reset-defaults`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();

        if (result.success) {
            showToast('Settings reset to defaults successfully', 'success');
            // Reload the page to show updated settings
            setTimeout(() => window.location.reload(), 1500);
        } else {
            throw new Error(result.error || 'Failed to reset settings');
        }

    } catch (error) {
        console.error('Error resetting guild settings:', error);
        showToast('Failed to reset settings: ' + error.message, 'error');
    }
}

function showToast(message, type = 'success') {
    // Create toast element
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'success'} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-${type === 'error' ? 'exclamation-triangle' : 'check-circle'} me-2"></i>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Show toast
    if (typeof bootstrap !== 'undefined') {
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: 5000
        });
        bsToast.show();

        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    } else {
        // Fallback for when Bootstrap is not available
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

function initializeCharts() {
    // Initialize any charts here
    // This is where you'd set up Chart.js or other charting libraries
    console.log('📈 Charts initialized');
}

// Utility functions
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
        return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

function formatNumber(num) {
    return num.toLocaleString();
}

// API monitoring functions
function startAPIMonitoring() {
    // Check API health every 5 minutes
    setInterval(async () => {
        if (document.visibilityState === 'visible') {
            const wasHealthy = apiHealthy;
            await checkAPIHealth();

            // If API recovered, show notification
            if (!wasHealthy && apiHealthy) {
                showToast('API connection restored', 'success');
            }
        }
    }, 300000); // 5 minutes
}

// Error reporting function
function reportError(error, context = '') {
    console.error(`Error in ${context}:`, error);

    // In a production environment, you might want to send this to an error tracking service
    // sendErrorToService({ error: error.message, context, timestamp: new Date().toISOString() });
}

// Export functions for use in other scripts and global access
window.dashboardUtils = {
    refreshStats,
    refreshAnalytics,
    showToast,
    updateStatsDisplay,
    updateAnalyticsUI,
    formatUptime,
    formatNumber,
    checkAPIHealth,
    resetGuildSettings,
    reportError
};

// Start API monitoring
startAPIMonitoring();

console.log('🎯 Dashboard utilities loaded and ready');