/**
 * LADBOT ENHANCED DASHBOARD - JAVASCRIPT
 * Real-time bot integration with modern ES6+ features
 * Production-ready with comprehensive error handling
 */

// ===== CONFIGURATION & CONSTANTS =====
const CONFIG = {
    updateIntervals: {
        stats: 15000,        // 15 seconds for main stats
        analytics: 30000,    // 30 seconds for analytics
        health: 60000,       // 1 minute for health check
        realtime: 5000       // 5 seconds for real-time data
    },
    api: {
        maxRetries: 3,
        retryDelay: 1000,
        timeout: 10000
    },
    animations: {
        duration: 300,
        easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
    }
};

// ===== GLOBAL STATE MANAGEMENT =====
class DashboardState {
    constructor() {
        this.intervals = new Map();
        this.isRefreshing = false;
        this.connectionHealth = 'unknown';
        this.lastUpdate = null;
        this.retryCount = 0;
        this.data = {
            stats: {},
            analytics: {},
            commands: [],
            guilds: []
        };
    }

    updateStats(newStats) {
        this.data.stats = { ...this.data.stats, ...newStats };
        this.lastUpdate = new Date();
        this.emit('statsUpdated', this.data.stats);
    }

    updateAnalytics(newAnalytics) {
        this.data.analytics = { ...this.data.analytics, ...newAnalytics };
        this.emit('analyticsUpdated', this.data.analytics);
    }

    setConnectionHealth(status) {
        this.connectionHealth = status;
        this.emit('connectionChanged', status);
    }

    emit(event, data) {
        document.dispatchEvent(new CustomEvent(`dashboard:${event}`, { detail: data }));
    }
}

const state = new DashboardState();

// ===== API COMMUNICATION =====
class APIClient {
    constructor() {
        this.baseURL = window.location.origin;
        this.headers = {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        };
    }

    async request(endpoint, options = {}) {
        const config = {
            method: 'GET',
            headers: this.headers,
            timeout: CONFIG.api.timeout,
            ...options
        };

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), config.timeout);

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...config,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            state.retryCount = 0; // Reset on success
            return data;

        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }

            state.retryCount++;
            throw error;
        }
    }

    async getStats() {
        return this.request('/api/stats');
    }

    async getAnalytics() {
        return this.request('/api/analytics');
    }

    async getBotHealth() {
        return this.request('/api/bot/health');
    }

    async getCommandUsage() {
        return this.request('/api/commands/usage');
    }

    async reloadBot() {
        return this.request('/api/bot/reload', { method: 'POST' });
    }

    async updateSetting(setting, value) {
        return this.request('/api/settings', {
            method: 'POST',
            body: JSON.stringify({ setting, value })
        });
    }
}

const api = new APIClient();

// ===== UI COMPONENTS & ANIMATIONS =====
class UIManager {
    constructor() {
        this.animations = new Map();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Dashboard events
        document.addEventListener('dashboard:statsUpdated', (e) => {
            this.updateStatsDisplay(e.detail);
        });

        document.addEventListener('dashboard:analyticsUpdated', (e) => {
            this.updateAnalyticsDisplay(e.detail);
        });

        document.addEventListener('dashboard:connectionChanged', (e) => {
            this.updateConnectionStatus(e.detail);
        });

        // Button events
        this.setupRefreshButtons();
        this.setupSettingsToggles();
        this.setupModalHandlers();
    }

    setupRefreshButtons() {
        document.querySelectorAll('[data-refresh]').forEach(button => {
            button.addEventListener('click', async (e) => {
                e.preventDefault();
                const type = button.dataset.refresh;
                await this.handleRefresh(button, type);
            });
        });
    }

    async handleRefresh(button, type) {
        if (state.isRefreshing) return;

        const originalContent = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
        button.disabled = true;
        state.isRefreshing = true;

        try {
            switch (type) {
                case 'stats':
                    await dataManager.updateStats();
                    break;
                case 'analytics':
                    await dataManager.updateAnalytics();
                    break;
                case 'all':
                    await dataManager.updateAll();
                    break;
            }

            this.showToast('Data refreshed successfully', 'success');
            this.animateRefreshSuccess(button);

        } catch (error) {
            console.error('Refresh failed:', error);
            this.showToast(`Refresh failed: ${error.message}`, 'error');
            this.animateRefreshError(button);

        } finally {
            setTimeout(() => {
                button.innerHTML = originalContent;
                button.disabled = false;
                state.isRefreshing = false;
            }, 1000);
        }
    }

    updateStatsDisplay(stats) {
        // Update stat cards with animation
        this.updateStatCard('guilds', stats.guilds || 0);
        this.updateStatCard('users', this.formatNumber(stats.users || 0));
        this.updateStatCard('commands', stats.commands_today || 0);
        this.updateStatCard('uptime', stats.uptime || '0:00:00');

        // Update bot status
        this.updateBotStatus(stats.bot_status, stats.latency);

        // Update progress bars
        this.updateProgressBar('memory-usage', stats.memory_percent || 0);
        this.updateProgressBar('cpu-usage', stats.cpu_percent || 0);

        // Update last update time
        this.updateElement('last-update-time', new Date().toLocaleTimeString());
    }

    updateStatCard(id, value) {
        const element = document.querySelector(`[data-stat="${id}"]`);
        if (!element) return;

        const currentValue = element.textContent;
        if (currentValue !== value.toString()) {
            // Animate the change
            element.style.transform = 'scale(1.1)';
            element.style.color = '#4facfe';

            setTimeout(() => {
                element.textContent = value;
                element.style.transform = 'scale(1)';
                element.style.color = '';
            }, 150);
        }
    }

    updateBotStatus(status, latency) {
        const statusElement = document.querySelector('.status-indicator');
        if (!statusElement) return;

        statusElement.className = `status-indicator status-${status || 'offline'}`;
        statusElement.innerHTML = `
            <i class="fas fa-circle"></i>
            Bot ${(status || 'offline').charAt(0).toUpperCase() + (status || 'offline').slice(1)}
            ${latency ? `• ${latency}ms` : ''}
        `;
    }

    updateProgressBar(id, percentage) {
        const progressBar = document.querySelector(`[data-progress="${id}"]`);
        if (!progressBar) return;

        progressBar.style.width = `${Math.min(percentage, 100)}%`;
        progressBar.setAttribute('aria-valuenow', percentage);

        // Color coding for different percentages
        progressBar.className = progressBar.className.replace(/bg-\w+/, '');
        if (percentage < 50) {
            progressBar.classList.add('bg-success');
        } else if (percentage < 80) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-danger');
        }
    }

    updateElement(selector, value) {
        const element = document.getElementById(selector) || document.querySelector(selector);
        if (element) {
            element.textContent = value;
        }
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toLocaleString();
    }

    // Toast notifications
    showToast(message, type = 'info', duration = 5000) {
        const toastContainer = this.getToastContainer();
        const toastId = 'toast-' + Date.now();

        const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-${this.getToastIcon(type)} me-2"></i>
                        ${this.escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHTML);

        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { delay: duration });
        toast.show();

        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });

        return toast;
    }

    getToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    }

    getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    updateConnectionStatus(status) {
        const indicator = document.getElementById('connection-status');
        if (!indicator) return;

        const statusConfig = {
            healthy: { color: 'success', icon: 'check-circle', text: 'Connected' },
            degraded: { color: 'warning', icon: 'exclamation-triangle', text: 'Slow Connection' },
            unhealthy: { color: 'danger', icon: 'times-circle', text: 'Connection Issues' },
            connecting: { color: 'info', icon: 'spinner fa-spin', text: 'Connecting...' }
        };

        const config = statusConfig[status] || statusConfig.unhealthy;
        indicator.innerHTML = `
            <i class="fas fa-${config.icon} text-${config.color}"></i>
            <span class="text-${config.color}">${config.text}</span>
        `;
    }

    // Animation helpers
    animateRefreshSuccess(button) {
        button.style.background = '#28a745';
        setTimeout(() => {
            button.style.background = '';
        }, 500);
    }

    animateRefreshError(button) {
        button.style.background = '#dc3545';
        setTimeout(() => {
            button.style.background = '';
        }, 500);
    }

    setupSettingsToggles() {
        document.querySelectorAll('.setting-toggle').forEach(toggle => {
            toggle.addEventListener('change', async (e) => {
                const setting = toggle.dataset.setting;
                const value = toggle.checked;

                try {
                    await api.updateSetting(setting, value);
                    this.showToast(`Setting "${setting}" updated`, 'success');
                } catch (error) {
                    console.error('Setting update failed:', error);
                    toggle.checked = !value; // Revert
                    this.showToast(`Failed to update setting: ${error.message}`, 'error');
                }
            });
        });
    }

    setupModalHandlers() {
        // Setup modals for bot actions
        document.querySelectorAll('[data-action="reload-bot"]').forEach(button => {
            button.addEventListener('click', () => this.handleBotReload());
        });
    }

    async handleBotReload() {
        const confirmed = await this.showConfirmModal(
            'Reload Bot',
            'Are you sure you want to reload the bot? This may cause a brief interruption in service.',
            'warning'
        );

        if (!confirmed) return;

        try {
            this.showToast('Reloading bot...', 'info');
            await api.reloadBot();
            this.showToast('Bot reloaded successfully', 'success');

            // Refresh data after reload
            setTimeout(() => {
                dataManager.updateAll();
            }, 2000);

        } catch (error) {
            console.error('Bot reload failed:', error);
            this.showToast(`Bot reload failed: ${error.message}`, 'error');
        }
    }

    async showConfirmModal(title, message, type = 'info') {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-${this.getToastIcon(type)}"></i>
                                ${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${message}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-${type}" data-confirm="true">Confirm</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            const bootstrapModal = new bootstrap.Modal(modal);
            bootstrapModal.show();

            modal.addEventListener('click', (e) => {
                if (e.target.dataset.confirm) {
                    resolve(true);
                    bootstrapModal.hide();
                }
            });

            modal.addEventListener('hidden.bs.modal', () => {
                resolve(false);
                modal.remove();
            });
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ===== DATA MANAGEMENT =====
class DataManager {
    constructor() {
        this.setupAutoRefresh();
    }

    setupAutoRefresh() {
        // Set up different update intervals for different data types
        state.intervals.set('stats', setInterval(() => {
            this.updateStats();
        }, CONFIG.updateIntervals.stats));

        state.intervals.set('analytics', setInterval(() => {
            this.updateAnalytics();
        }, CONFIG.updateIntervals.analytics));

        state.intervals.set('health', setInterval(() => {
            this.checkHealth();
        }, CONFIG.updateIntervals.health));

        console.log('🔄 Auto-refresh intervals set up');
    }

    async updateStats() {
        try {
            const stats = await api.getStats();
            state.updateStats(stats);
            state.setConnectionHealth('healthy');
            return stats;
        } catch (error) {
            console.error('Failed to update stats:', error);
            this.handleError(error);
            throw error;
        }
    }

    async updateAnalytics() {
        try {
            const analytics = await api.getAnalytics();
            state.updateAnalytics(analytics);
            return analytics;
        } catch (error) {
            console.error('Failed to update analytics:', error);
            this.handleError(error);
            throw error;
        }
    }

    async checkHealth() {
        try {
            const health = await api.getBotHealth();
            state.setConnectionHealth(health.status || 'healthy');
            return health;
        } catch (error) {
            console.error('Health check failed:', error);
            state.setConnectionHealth('unhealthy');
            throw error;
        }
    }

    async updateAll() {
        try {
            const [stats, analytics] = await Promise.allSettled([
                this.updateStats(),
                this.updateAnalytics()
            ]);

            if (stats.status === 'rejected' && analytics.status === 'rejected') {
                throw new Error('All updates failed');
            }

            return { stats: stats.value, analytics: analytics.value };
        } catch (error) {
            console.error('Failed to update all data:', error);
            throw error;
        }
    }

    handleError(error) {
        if (state.retryCount >= CONFIG.api.maxRetries) {
            state.setConnectionHealth('unhealthy');
            ui.showToast('Connection lost. Please check your internet connection.', 'error');
        } else {
            state.setConnectionHealth('degraded');
        }
    }

    destroy() {
        // Clean up intervals
        state.intervals.forEach((interval) => {
            clearInterval(interval);
        });
        state.intervals.clear();
        console.log('🧹 Data manager cleaned up');
    }
}

// ===== CHARTS & VISUALIZATIONS =====
class ChartManager {
    constructor() {
        this.charts = new Map();
        this.initializeCharts();
    }

    initializeCharts() {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js not loaded, skipping chart initialization');
            return;
        }

        this.createLatencyChart();
        this.createCommandChart();
        this.createActivityChart();
    }

    createLatencyChart() {
        const ctx = document.getElementById('latency-chart');
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Latency (ms)',
                    data: [],
                    borderColor: '#5865F2',
                    backgroundColor: 'rgba(88, 101, 242, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Latency (ms)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        this.charts.set('latency', chart);
    }

    createCommandChart() {
        const ctx = document.getElementById('command-chart');
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#5865F2', '#57F287', '#FEE75C', '#ED4245', '#00D4AA',
                        '#FF6B9D', '#4ECDC4', '#45B7D1', '#F9CA24', '#6C5CE7'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.charts.set('commands', chart);
    }

    createActivityChart() {
        const ctx = document.getElementById('activity-chart');
        if (!ctx) return;

        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Commands Per Hour',
                    data: [],
                    backgroundColor: 'rgba(88, 101, 242, 0.8)',
                    borderColor: '#5865F2',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Commands'
                        }
                    }
                }
            }
        });

        this.charts.set('activity', chart);
    }

    updateChart(chartName, data) {
        const chart = this.charts.get(chartName);
        if (!chart) return;

        // Update chart data based on type
        switch (chartName) {
            case 'latency':
                this.updateLatencyChart(chart, data);
                break;
            case 'commands':
                this.updateCommandChart(chart, data);
                break;
            case 'activity':
                this.updateActivityChart(chart, data);
                break;
        }

        chart.update('none'); // No animation for real-time updates
    }

    updateLatencyChart(chart, latencyData) {
        const now = new Date();
        chart.data.labels.push(now.toLocaleTimeString());
        chart.data.datasets[0].data.push(latencyData.current || 0);

        // Keep only last 20 data points
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
    }

    updateCommandChart(chart, commandData) {
        if (!Array.isArray(commandData)) return;

        chart.data.labels = commandData.map(cmd => cmd.name);
        chart.data.datasets[0].data = commandData.map(cmd => cmd.count);
    }

    updateActivityChart(chart, activityData) {
        if (!Array.isArray(activityData)) return;

        chart.data.labels = activityData.map(hour => `${hour.hour}:00`);
        chart.data.datasets[0].data = activityData.map(hour => hour.commands);
    }

    destroy() {
        this.charts.forEach(chart => chart.destroy());
        this.charts.clear();
    }
}

// ===== DASHBOARD INITIALIZATION =====
class Dashboard {
    constructor() {
        this.ui = new UIManager();
        this.dataManager = new DataManager();
        this.chartManager = new ChartManager();

        this.initialize();
    }

    async initialize() {
        console.log('🚀 Initializing Ladbot Dashboard...');

        try {
            // Initial data load
            await this.dataManager.updateAll();
            console.log('✅ Initial data loaded');

            // Setup real-time updates
            this.setupRealTimeUpdates();
            console.log('🔄 Real-time updates configured');

            // Setup event listeners
            this.setupGlobalEventListeners();
            console.log('🎮 Event listeners configured');

            // Initialize Bootstrap components
            this.initializeBootstrapComponents();
            console.log('🎨 Bootstrap components initialized');

            this.ui.showToast('Dashboard loaded successfully', 'success');
            console.log('✅ Dashboard initialization complete');

        } catch (error) {
            console.error('❌ Dashboard initialization failed:', error);
            this.ui.showToast('Dashboard initialization failed', 'error');
        }
    }

    setupRealTimeUpdates() {
        // Listen for data updates and update charts
        document.addEventListener('dashboard:statsUpdated', (e) => {
            const stats = e.detail;
            if (stats.latency !== undefined) {
                this.chartManager.updateChart('latency', { current: stats.latency });
            }
        });

        document.addEventListener('dashboard:analyticsUpdated', (e) => {
            const analytics = e.detail;
            if (analytics.command_stats) {
                this.chartManager.updateChart('commands', analytics.command_stats);
            }
            if (analytics.hourly_activity) {
                this.chartManager.updateChart('activity', analytics.hourly_activity);
            }
        });
    }

    setupGlobalEventListeners() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseUpdates();
            } else {
                this.resumeUpdates();
            }
        });

        // Handle online/offline events
        window.addEventListener('online', () => {
            state.setConnectionHealth('healthy');
            this.dataManager.updateAll();
        });

        window.addEventListener('offline', () => {
            state.setConnectionHealth('unhealthy');
        });

        // Handle beforeunload
        window.addEventListener('beforeunload', () => {
            this.destroy();
        });
    }

    initializeBootstrapComponents() {
        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }

    pauseUpdates() {
        state.intervals.forEach((interval) => {
            clearInterval(interval);
        });
        console.log('⏸️ Updates paused');
    }

    resumeUpdates() {
        this.dataManager.setupAutoRefresh();
        console.log('▶️ Updates resumed');
    }

    destroy() {
        this.dataManager.destroy();
        this.chartManager.destroy();
        console.log('🧹 Dashboard destroyed');
    }
}

// ===== GLOBAL INSTANCES =====
let dashboard;
let ui;
let dataManager;
let chartManager;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('📱 DOM Content Loaded - Starting Dashboard...');

    dashboard = new Dashboard();
    ui = dashboard.ui;
    dataManager = dashboard.dataManager;
    chartManager = dashboard.chartManager;

    // Make instances globally available for debugging
    window.ladbot = {
        dashboard,
        ui,
        dataManager,
        chartManager,
        state,
        api,
        CONFIG
    };
});

// ===== GLOBAL FUNCTIONS FOR BACKWARDS COMPATIBILITY =====
function refreshDashboard() {
    return dataManager.updateAll();
}

function refreshStats() {
    return dataManager.updateStats();
}

function refreshAnalytics() {
    return dataManager.updateAnalytics();
}

function showToast(message, type = 'info') {
    return ui.showToast(message, type);
}

// ===== ERROR HANDLING =====
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    if (ui) {
        ui.showToast('An unexpected error occurred', 'error');
    }
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    if (ui) {
        ui.showToast('A network error occurred', 'error');
    }
});

console.log('📄 Ladbot Dashboard Script Loaded Successfully');