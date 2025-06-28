/**
 * Ladbot Dashboard - Real-Time Analytics Script
 * Optimized for Railway deployment with comprehensive error handling
 * Author: Enhanced for Production Use
 */

// === GLOBAL STATE MANAGEMENT ===
let refreshInterval;
let analyticsInterval;
let isRefreshing = false;
let apiHealthy = true;
let lastUpdateTime = null;
let connectionRetries = 0;
const MAX_RETRIES = 3;
const UPDATE_INTERVALS = {
    stats: 15000,      // 15 seconds for main stats
    analytics: 30000,  // 30 seconds for analytics
    health: 60000      // 1 minute for health check
};

// === INITIALIZATION ===
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Ladbot Dashboard Initializing...');

    initializeDashboard();
    setupEventListeners();
    startRealTimeUpdates();
    checkInitialConnection();

    console.log('✅ Dashboard initialization complete');
});

// === DASHBOARD INITIALIZATION ===
function initializeDashboard() {
    // Initialize Bootstrap components
    initializeBootstrapComponents();

    // Set up UI components
    setupProgressBars();
    setupTooltips();

    // Show connection status
    updateConnectionStatus('connecting');

    // Initialize charts if needed
    initializeCharts();

    console.log('📊 Dashboard components initialized');
}

function initializeBootstrapComponents() {
    // Initialize tooltips
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Initialize popovers
    if (typeof bootstrap !== 'undefined') {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
}

// === REAL-TIME UPDATE SYSTEM ===
function startRealTimeUpdates() {
    // Main stats update (every 15 seconds)
    refreshInterval = setInterval(() => {
        if (!isRefreshing && document.visibilityState === 'visible' && apiHealthy) {
            updateBotStats();
        }
    }, UPDATE_INTERVALS.stats);

    // Analytics update (every 30 seconds)
    analyticsInterval = setInterval(() => {
        if (!isRefreshing && document.visibilityState === 'visible' && apiHealthy) {
            updateAnalytics();
        }
    }, UPDATE_INTERVALS.analytics);

    // Health check (every minute)
    setInterval(checkAPIHealth, UPDATE_INTERVALS.health);

    // Pause updates when tab is not visible
    document.addEventListener('visibilitychange', handleVisibilityChange);

    console.log('⚡ Real-time updates started');
}

function handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
        console.log('👁️ Tab visible - resuming updates');
        if (apiHealthy) {
            updateBotStats();
        }
    } else {
        console.log('👁️ Tab hidden - pausing updates');
    }
}

// === API COMMUNICATION ===
async function makeAPIRequest(endpoint, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    try {
        const response = await fetch(endpoint, {
            ...options,
            signal: controller.signal,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Reset retry counter on success
        connectionRetries = 0;
        updateAPIHealth(true);

        return data;
    } catch (error) {
        clearTimeout(timeoutId);

        if (error.name === 'AbortError') {
            throw new Error('Request timeout');
        }

        connectionRetries++;
        if (connectionRetries >= MAX_RETRIES) {
            updateAPIHealth(false);
        }

        throw error;
    }
}

async function updateBotStats() {
    if (isRefreshing) return;

    try {
        showLoadingState('stats');

        const data = await makeAPIRequest('/api/stats');

        if (data && !data.error) {
            updateStatsDisplay(data);
            updateLastRefreshTime();

            // Update connection status
            updateConnectionStatus('connected', data.latency);
        } else {
            throw new Error(data.error || 'Invalid response');
        }

    } catch (error) {
        console.error('❌ Stats update failed:', error);
        updateConnectionStatus('error', null, error.message);
        showErrorState('stats', error.message);
    } finally {
        hideLoadingState('stats');
    }
}

async function updateAnalytics() {
    if (isRefreshing) return;

    try {
        showLoadingState('analytics');

        const data = await makeAPIRequest('/api/analytics');

        if (data && !data.error) {
            updateAnalyticsDisplay(data);
            updateCommandStatsTable(data.command_stats || []);
            updateGuildsList(data.guilds || []);
        } else {
            throw new Error(data.error || 'Invalid analytics response');
        }

    } catch (error) {
        console.error('❌ Analytics update failed:', error);
        showErrorState('analytics', error.message);
    } finally {
        hideLoadingState('analytics');
    }
}

async function checkAPIHealth() {
    try {
        const startTime = Date.now();
        const response = await makeAPIRequest('/api/health');
        const latency = Date.now() - startTime;

        if (response && response.status === 'healthy') {
            updateAPIHealth(true, latency);
        } else {
            updateAPIHealth(false);
        }
    } catch (error) {
        console.warn('⚠️ Health check failed:', error);
        updateAPIHealth(false);
    }
}

async function checkInitialConnection() {
    try {
        await updateBotStats();
        console.log('✅ Initial connection successful');
    } catch (error) {
        console.error('❌ Initial connection failed:', error);
        showConnectionError();
    }
}

// === UI UPDATE FUNCTIONS ===
function updateStatsDisplay(stats) {
    // Main stat cards
    updateElement('guild-count', stats.guilds || 0);
    updateElement('user-count', formatNumber(stats.users || 0));
    updateElement('command-count', stats.commands || 0);
    updateElement('uptime-display', stats.uptime || 'Unknown');

    // Performance metrics
    updateElement('latency-display', `${stats.latency || 0}ms`);
    updateElement('loaded-cogs', stats.loaded_cogs || 0);
    updateElement('commands-today', stats.commands_today || 0);
    updateElement('session-commands', stats.session_commands || 0);
    updateElement('total-commands', stats.total_commands || 0);
    updateElement('error-count', stats.error_count || 0);

    // Status indicators
    updateBotStatus(stats.bot_status || 'unknown');
    updateLatencyIndicator(stats.latency || 0);

    // Progress bars
    updateProgressBar('memory-usage', stats.memory_usage || 0);
    updateProgressBar('cpu-usage', stats.cpu_usage || 0);

    // Charts
    updateLatencyChart(stats.latency_history || []);
    updateCommandChart(stats.commands_today || 0);

    console.log('📊 Stats display updated');
}

function updateAnalyticsDisplay(analytics) {
    // Analytics cards
    updateElement('total-guilds', analytics.total_guilds || 0);
    updateElement('total-users', formatNumber(analytics.total_users || 0));
    updateElement('daily-commands', analytics.daily_commands || 0);
    updateElement('weekly-commands', analytics.weekly_commands || 0);
    updateElement('monthly-commands', analytics.monthly_commands || 0);
    updateElement('error-rate', `${analytics.error_rate || 0}%`);

    // Growth metrics
    updateElement('guild-growth', analytics.guild_growth || 0);
    updateElement('user-growth', analytics.user_growth || 0);
    updateElement('command-growth', analytics.command_growth || 0);

    // Performance metrics
    updateElement('avg-response-time', `${analytics.average_response_time || 0}ms`);
    updateElement('uptime-percentage', `${analytics.uptime_percentage || 0}%`);
    updateElement('peak-guilds', analytics.peak_guilds || 0);

    console.log('📈 Analytics display updated');
}

function updateCommandStatsTable(commandStats) {
    const tableBody = document.querySelector('#command-stats-table tbody');
    if (!tableBody || !Array.isArray(commandStats)) return;

    const rows = commandStats.slice(0, 10).map((cmd, index) => `
        <tr>
            <td>${index + 1}</td>
            <td><code>${escapeHtml(cmd.name || 'Unknown')}</code></td>
            <td><span class="badge bg-primary">${cmd.count || 0}</span></td>
            <td><span class="badge bg-secondary">${cmd.category || 'Other'}</span></td>
            <td><small class="text-muted">${cmd.last_used || 'Never'}</small></td>
        </tr>
    `).join('');

    tableBody.innerHTML = rows || '<tr><td colspan="5" class="text-center text-muted">No command data available</td></tr>';
}

function updateGuildsList(guilds) {
    const container = document.getElementById('guilds-list');
    if (!container || !Array.isArray(guilds)) return;

    const guildCards = guilds.slice(0, 5).map(guild => `
        <div class="col-md-6 mb-3">
            <div class="card h-100">
                <div class="card-body">
                    <h6 class="card-title">${escapeHtml(guild.name || 'Unknown Server')}</h6>
                    <p class="card-text">
                        <small class="text-muted">
                            <i class="fas fa-users"></i> ${guild.member_count || 0} members
                            ${guild.owner ? '<i class="fas fa-crown text-warning ms-2"></i>' : ''}
                        </small>
                    </p>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = guildCards || '<div class="col-12"><p class="text-muted text-center">No server data available</p></div>';
}

function updateBotStatus(status) {
    const statusElement = document.getElementById('bot-status');
    const statusBadge = document.getElementById('bot-status-badge');

    if (!statusElement) return;

    const statusConfig = {
        online: { text: 'Online', class: 'text-success', badge: 'bg-success' },
        idle: { text: 'Idle', class: 'text-warning', badge: 'bg-warning' },
        dnd: { text: 'Do Not Disturb', class: 'text-danger', badge: 'bg-danger' },
        offline: { text: 'Offline', class: 'text-secondary', badge: 'bg-secondary' },
        unknown: { text: 'Unknown', class: 'text-muted', badge: 'bg-secondary' }
    };

    const config = statusConfig[status] || statusConfig.unknown;

    statusElement.textContent = config.text;
    statusElement.className = config.class;

    if (statusBadge) {
        statusBadge.className = `badge ${config.badge}`;
    }
}

function updateLatencyIndicator(latency) {
    const indicator = document.getElementById('latency-indicator');
    if (!indicator) return;

    let status, className;

    if (latency < 100) {
        status = 'Excellent';
        className = 'text-success';
    } else if (latency < 200) {
        status = 'Good';
        className = 'text-warning';
    } else {
        status = 'Poor';
        className = 'text-danger';
    }

    indicator.innerHTML = `<span class="${className}">${status}</span> (${latency}ms)`;
}

function updateProgressBar(id, value) {
    const progressBar = document.getElementById(id);
    if (!progressBar) return;

    const percentage = Math.min(Math.max(value, 0), 100);
    progressBar.style.width = `${percentage}%`;
    progressBar.setAttribute('aria-valuenow', percentage);

    // Update color based on value
    progressBar.className = progressBar.className.replace(/bg-(success|warning|danger)/, '');
    if (percentage < 50) {
        progressBar.classList.add('bg-success');
    } else if (percentage < 80) {
        progressBar.classList.add('bg-warning');
    } else {
        progressBar.classList.add('bg-danger');
    }
}

function updateConnectionStatus(status, latency = null, error = null) {
    const statusIndicator = document.getElementById('connection-status');
    if (!statusIndicator) return;

    const statusConfig = {
        connecting: {
            icon: 'fas fa-spinner fa-spin',
            text: 'Connecting...',
            class: 'text-warning'
        },
        connected: {
            icon: 'fas fa-wifi',
            text: latency ? `Connected (${latency}ms)` : 'Connected',
            class: 'text-success'
        },
        error: {
            icon: 'fas fa-exclamation-triangle',
            text: error ? `Error: ${error}` : 'Connection Error',
            class: 'text-danger'
        },
        disconnected: {
            icon: 'fas fa-wifi-slash',
            text: 'Disconnected',
            class: 'text-secondary'
        }
    };

    const config = statusConfig[status] || statusConfig.disconnected;

    statusIndicator.innerHTML = `
        <i class="${config.icon}"></i>
        <span class="${config.class}">${config.text}</span>
    `;
}

function updateAPIHealth(healthy, latency = null) {
    apiHealthy = healthy;

    const healthIndicator = document.getElementById('api-health');
    if (healthIndicator) {
        if (healthy) {
            healthIndicator.innerHTML = `
                <span class="badge bg-success">
                    <i class="fas fa-check"></i> API Healthy
                    ${latency ? `(${latency}ms)` : ''}
                </span>
            `;
        } else {
            healthIndicator.innerHTML = `
                <span class="badge bg-danger">
                    <i class="fas fa-times"></i> API Issues
                </span>
            `;
        }
    }
}

// === LOADING AND ERROR STATES ===
function showLoadingState(section) {
    const loader = document.getElementById(`${section}-loader`);
    if (loader) {
        loader.style.display = 'block';
    }

    // Add loading class to section
    const sectionElement = document.getElementById(`${section}-section`);
    if (sectionElement) {
        sectionElement.classList.add('loading-state');
    }
}

function hideLoadingState(section) {
    const loader = document.getElementById(`${section}-loader`);
    if (loader) {
        loader.style.display = 'none';
    }

    // Remove loading class from section
    const sectionElement = document.getElementById(`${section}-section`);
    if (sectionElement) {
        sectionElement.classList.remove('loading-state');
    }
}

function showErrorState(section, message) {
    const errorContainer = document.getElementById(`${section}-error`);
    if (errorContainer) {
        errorContainer.innerHTML = `
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <i class="fas fa-exclamation-triangle"></i>
                <strong>Update Failed:</strong> ${escapeHtml(message)}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        errorContainer.style.display = 'block';
    }
}

function showConnectionError() {
    showToast('Failed to connect to bot API. Please check your connection.', 'error');
}

// === CHARTS AND VISUALIZATIONS ===
function initializeCharts() {
    // Initialize Chart.js charts if library is available
    if (typeof Chart !== 'undefined') {
        initializeLatencyChart();
        initializeCommandChart();
        initializeGuildChart();
    }
}

function initializeLatencyChart() {
    const ctx = document.getElementById('latency-chart');
    if (!ctx) return;

    // Chart initialization code here
    console.log('📈 Latency chart initialized');
}

function initializeCommandChart() {
    const ctx = document.getElementById('command-chart');
    if (!ctx) return;

    // Chart initialization code here
    console.log('📊 Command chart initialized');
}

function updateLatencyChart(latencyHistory) {
    // Update latency chart with new data
    console.log('📈 Latency chart updated');
}

function updateCommandChart(commandsToday) {
    // Update command chart with new data
    console.log('📊 Command chart updated');
}

// === EVENT LISTENERS ===
function setupEventListeners() {
    // Refresh buttons
    setupRefreshButton('refresh-stats-btn', () => manualRefresh('stats'));
    setupRefreshButton('refresh-analytics-btn', () => manualRefresh('analytics'));

    // Settings toggles
    setupSettingsToggles();

    // Search functionality
    setupSearchFilters();

    console.log('🎮 Event listeners set up');
}

function setupRefreshButton(buttonId, callback) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.addEventListener('click', callback);
    }
}

async function manualRefresh(type) {
    const button = event.target.closest('button');
    if (!button) return;

    const originalContent = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
    button.disabled = true;

    try {
        if (type === 'stats') {
            await updateBotStats();
        } else if (type === 'analytics') {
            await updateAnalytics();
        }

        showToast('Data refreshed successfully', 'success');
    } catch (error) {
        showToast(`Refresh failed: ${error.message}`, 'error');
    } finally {
        button.innerHTML = originalContent;
        button.disabled = false;
    }
}

function setupSettingsToggles() {
    document.querySelectorAll('.setting-toggle').forEach(toggle => {
        toggle.addEventListener('change', handleSettingChange);
    });
}

async function handleSettingChange(event) {
    const toggle = event.target;
    const setting = toggle.dataset.setting;
    const value = toggle.checked;

    try {
        await makeAPIRequest('/api/settings', {
            method: 'POST',
            body: JSON.stringify({ setting, value })
        });

        showToast('Setting updated successfully', 'success');
    } catch (error) {
        toggle.checked = !value; // Revert on error
        showToast(`Failed to update setting: ${error.message}`, 'error');
    }
}

function setupSearchFilters() {
    const searchInput = document.getElementById('command-search');
    if (searchInput) {
        searchInput.addEventListener('input', filterCommandTable);
    }
}

function filterCommandTable() {
    const searchTerm = event.target.value.toLowerCase();
    const rows = document.querySelectorAll('#command-stats-table tbody tr');

    rows.forEach(row => {
        const commandName = row.querySelector('code')?.textContent.toLowerCase() || '';
        const shouldShow = commandName.includes(searchTerm);
        row.style.display = shouldShow ? '' : 'none';
    });
}

// === UTILITY FUNCTIONS ===
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function updateLastRefreshTime() {
    lastUpdateTime = new Date();
    const timeString = lastUpdateTime.toLocaleTimeString();

    updateElement('last-refresh-time', timeString);
    updateElement('last-updated', timeString);
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function showToast(message, type = 'info') {
    // Create toast notification
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toastId = 'toast-' + Date.now();
    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${escapeHtml(message)}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    // Remove from DOM after hiding
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '9999';
    document.body.appendChild(container);
    return container;
}

function setupTooltips() {
    // Enhanced tooltips for better UX
    document.querySelectorAll('[title]').forEach(element => {
        if (!element.hasAttribute('data-bs-toggle')) {
            element.setAttribute('data-bs-toggle', 'tooltip');
        }
    });
}

function setupProgressBars() {
    // Initialize progress bars with animations
    document.querySelectorAll('.progress-bar').forEach(bar => {
        bar.style.transition = 'width 0.3s ease-in-out';
    });
}

// === CLEANUP ===
window.addEventListener('beforeunload', function() {
    if (refreshInterval) clearInterval(refreshInterval);
    if (analyticsInterval) clearInterval(analyticsInterval);
    console.log('🧹 Dashboard cleanup completed');
});

// === EXPORT FOR TESTING ===
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        updateBotStats,
        updateAnalytics,
        checkAPIHealth,
        makeAPIRequest
    };
}

console.log('📝 Ladbot Dashboard Script Loaded Successfully');