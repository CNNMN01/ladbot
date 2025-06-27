// Ladbot Dashboard JavaScript

// Global variables
let statsRefreshInterval;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Ladbot Dashboard loaded');

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Start auto-refresh for dashboard
    if (window.location.pathname === '/dashboard') {
        startStatsAutoRefresh();
    }
});

// Auto-refresh statistics
function startStatsAutoRefresh() {
    // Refresh every 30 seconds
    statsRefreshInterval = setInterval(refreshDashboardStats, 30000);
}

function stopStatsAutoRefresh() {
    if (statsRefreshInterval) {
        clearInterval(statsRefreshInterval);
    }
}

function refreshDashboardStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => {
            console.error('Error refreshing stats:', error);
        });
}

function updateDashboardStats(stats) {
    // Update stat cards if they exist
    const elements = {
        guilds: document.querySelector('.card.bg-primary h2'),
        users: document.querySelector('.card.bg-success h2'),
        commands: document.querySelector('.card.bg-info h2'),
        uptime: document.querySelector('.card.bg-warning h6')
    };

    if (elements.guilds) elements.guilds.textContent = stats.guilds || 0;
    if (elements.users) elements.users.textContent = stats.users || 0;
    if (elements.commands) elements.commands.textContent = stats.commands || 0;
    if (elements.uptime) elements.uptime.textContent = stats.uptime || 'Unknown';

    // Update detailed stats
    const statusBadge = document.querySelector('.badge');
    if (statusBadge) {
        statusBadge.textContent = stats.status || 'Unknown';
        statusBadge.className = `badge bg-${stats.status === 'Online' ? 'success' : 'danger'}`;
    }

    // Update other stats if elements exist
    updateTextContent('latency', `${stats.latency || 0}ms`);
    updateTextContent('cogs', stats.cogs || 0);
    updateTextContent('commands-used', stats.commands_used || 0);
}

function updateTextContent(className, value) {
    const elements = document.querySelectorAll(`.${className}`);
    elements.forEach(el => {
        if (el.textContent.includes(':')) {
            const parts = el.textContent.split(':');
            el.textContent = `${parts[0]}: ${value}`;
        } else {
            el.textContent = value;
        }
    });
}

// Utility functions
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';

    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// API helper functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Settings management functions
function bulkUpdateSettings(guildId, settings) {
    const updates = Object.entries(settings).map(([setting, value]) => {
        return apiRequest(`/api/guild/${guildId}/settings`, {
            method: 'POST',
            body: JSON.stringify({
                setting: setting,
                value: value
            })
        });
    });

    return Promise.all(updates);
}

// Theme management (future enhancement)
function toggleTheme() {
    const body = document.body;
    const isDark = body.classList.contains('dark-theme');

    if (isDark) {
        body.classList.remove('dark-theme');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
    }
}

// Load saved theme
function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
}

// Copy to clipboard utility
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!', 'success', 2000);
    }).catch(err => {
        console.error('Failed to copy: ', err);
        showNotification('Failed to copy to clipboard', 'danger', 2000);
    });
}

// Form validation helpers
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('is-invalid');
            isValid = false;
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Loading state management
function setLoading(element, isLoading) {
    if (isLoading) {
        element.disabled = true;
        element.dataset.originalText = element.innerHTML;
        element.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalText;
    }
}

// Initialize theme on load
loadTheme();

// Export functions for global use
window.LadBotDashboard = {
    refreshStats: refreshDashboardStats,
    showNotification: showNotification,
    copyToClipboard: copyToClipboard,
    toggleTheme: toggleTheme,
    apiRequest: apiRequest
};