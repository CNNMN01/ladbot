// Enhanced Dashboard JavaScript with Real-time Updates
let refreshInterval;
let isRefreshing = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Dashboard loaded');
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
}

function setupAutoRefresh() {
    // Auto-refresh every 30 seconds
    refreshInterval = setInterval(() => {
        if (!isRefreshing) {
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

        // Fetch fresh stats
        const response = await fetch('/api/stats');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const stats = await response.json();
        console.log('📊 Fresh stats received:', stats);

        // Update UI elements
        updateStatsDisplay(stats);
        updateLastRefreshTime();

        if (manual) {
            showToast('Stats refreshed successfully', 'success');
        }

    } catch (error) {
        console.error('❌ Error refreshing stats:', error);

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

function showToast(message, type = 'success') {
    // Create toast element
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
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
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    } else {
        // Fallback for when Bootstrap is not available
        toast.style.opacity = '1';
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
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

// Export functions for use in other scripts
window.dashboardUtils = {
    refreshStats,
    showToast,
    updateStatsDisplay,
    formatUptime,
    formatNumber
};