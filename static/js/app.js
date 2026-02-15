/**
 * Azure Log Analyzer - Futuristic Frontend
 * Main Application JavaScript
 */

// ================================================
// Configuration & State
// ================================================

const API_BASE = '';
let state = {
    tables: [],
    lastResults: null,
    lastColumns: null,
    queryCount: 0,
    isConnected: false,
    currentChart: null
};

// ================================================
// DOM Elements
// ================================================

const elements = {
    // Query
    queryInput: document.getElementById('queryInput'),
    analyzeBtn: document.getElementById('analyzeBtn'),
    kqlBtn: document.getElementById('kqlBtn'),
    clearBtn: document.getElementById('clearBtn'),
    kqlDisplay: document.getElementById('kqlDisplay'),
    kqlCode: document.getElementById('kqlCode'),
    copyKqlBtn: document.getElementById('copyKqlBtn'),
    sampleChips: document.getElementById('sampleChips'),
    
    // Results
    resultsContainer: document.getElementById('resultsContainer'),
    emptyState: document.getElementById('emptyState'),
    loadingState: document.getElementById('loadingState'),
    resultsWrapper: document.getElementById('resultsWrapper'),
    tableHead: document.getElementById('tableHead'),
    tableBody: document.getElementById('tableBody'),
    rowCount: document.getElementById('rowCount'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
    exportJsonBtn: document.getElementById('exportJsonBtn'),
    
    // Charts
    chartContainer: document.getElementById('chartContainer'),
    resultsChart: document.getElementById('resultsChart'),
    chartType: document.getElementById('chartType'),
    showChartBtn: document.getElementById('showChartBtn'),
    closeChartBtn: document.getElementById('closeChartBtn'),
    
    // Tables
    tablesList: document.getElementById('tablesList'),
    tableSearch: document.getElementById('tableSearch'),
    refreshTablesBtn: document.getElementById('refreshTablesBtn'),
    schemaSection: document.getElementById('schemaSection'),
    schemaTableName: document.getElementById('schemaTableName'),
    schemaContent: document.getElementById('schemaContent'),
    closeSchemaBtn: document.getElementById('closeSchemaBtn'),
    
    // Tables Panel Toggle
    tablesPanel: document.getElementById('tablesPanel'),
    toggleTablesBtn: document.getElementById('toggleTablesBtn'),
    toggleTablesIcon: document.getElementById('toggleTablesIcon'),
    
    // Status
    connectionStatus: document.getElementById('connectionStatus'),
    currentTime: document.getElementById('currentTime'),
    workspaceId: document.getElementById('workspaceId'),
    aiStatus: document.getElementById('aiStatus'),
    queryTime: document.getElementById('queryTime'),
    totalQueries: document.getElementById('totalQueries'),
    
    // Toast
    toastContainer: document.getElementById('toastContainer')
};

// ================================================
// Initialization
// ================================================

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    startClock();
    createParticles();
});

async function initializeApp() {
    try {
        // Check configuration status
        const configResponse = await fetch(`${API_BASE}/api/config/status`);
        const config = await configResponse.json();
        
        if (config.configured) {
            updateConnectionStatus(true);
            elements.workspaceId.textContent = config.workspace_id || 'Connected';
            elements.aiStatus.textContent = config.ai_enabled ? 'ENABLED' : 'DISABLED';
            
            // Load tables
            loadTables();
            
            // Load sample queries
            loadSampleQueries();
        } else {
            updateConnectionStatus(false);
            showToast('Configuration Error: ' + (config.error || 'Check your .env file'), 'error');
        }
    } catch (error) {
        updateConnectionStatus(false);
        showToast('Failed to connect to API server', 'error');
    }
}

function setupEventListeners() {
    // Query actions
    elements.analyzeBtn.addEventListener('click', executeNaturalQuery);
    elements.kqlBtn.addEventListener('click', executeKqlQuery);
    elements.clearBtn.addEventListener('click', clearInput);
    elements.copyKqlBtn.addEventListener('click', copyKql);
    
    // Enter key to submit
    elements.queryInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            executeNaturalQuery();
        }
    });
    
    // Export buttons
    elements.exportCsvBtn.addEventListener('click', () => exportResults('csv'));
    elements.exportJsonBtn.addEventListener('click', () => exportResults('json'));
    
    // Tables
    elements.refreshTablesBtn.addEventListener('click', loadTables);
    elements.tableSearch.addEventListener('input', filterTables);
    elements.closeSchemaBtn.addEventListener('click', closeSchema);
    
    // Toggle tables panel minimize/maximize
    if (elements.toggleTablesBtn) {
        elements.toggleTablesBtn.addEventListener('click', toggleTablesPanel);
    }
    
    // Chart controls
    if (elements.showChartBtn) {
        elements.showChartBtn.addEventListener('click', showChart);
    }
    if (elements.closeChartBtn) {
        elements.closeChartBtn.addEventListener('click', hideChart);
    }
    if (elements.chartType) {
        elements.chartType.addEventListener('change', () => {
            if (state.lastResults && state.lastResults.length > 0) {
                renderChart();
            }
        });
    }
}

// ================================================
// Tables Panel Toggle
// ================================================

function toggleTablesPanel() {
    const panel = elements.tablesPanel;
    const icon = elements.toggleTablesIcon;
    
    if (!panel) return;
    
    const isMinimized = panel.classList.toggle('minimized');
    
    if (icon) {
        icon.classList.remove('fa-minus', 'fa-plus');
        icon.classList.add(isMinimized ? 'fa-plus' : 'fa-minus');
    }
    
    // Toggle visibility of child elements
    const searchBox = panel.querySelector('.search-box');
    const tablesList = panel.querySelector('.tables-list');
    const schemaSection = panel.querySelector('.schema-section');
    
    if (searchBox) searchBox.style.display = isMinimized ? 'none' : '';
    if (tablesList) tablesList.style.display = isMinimized ? 'none' : '';
    if (schemaSection && !isMinimized) schemaSection.style.display = 'none';
}

// ================================================
// Chart Functions
// ================================================

function showChart() {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No data available to chart', 'info');
        return;
    }
    
    elements.chartContainer.style.display = 'block';
    renderChart();
}

function hideChart() {
    elements.chartContainer.style.display = 'none';
    if (state.currentChart) {
        state.currentChart.destroy();
        state.currentChart = null;
    }
}

function renderChart() {
    const data = state.lastResults;
    const columns = state.lastColumns;
    
    if (!data || data.length === 0 || !columns) return;
    
    // Destroy existing chart
    if (state.currentChart) {
        state.currentChart.destroy();
    }
    
    // Find suitable columns for charting
    const chartData = analyzeDataForChart(data, columns);
    
    if (!chartData) {
        showToast('Data not suitable for charting. Need numeric values.', 'info');
        return;
    }
    
    const ctx = elements.resultsChart.getContext('2d');
    const chartType = elements.chartType.value;
    
    // Chart colors
    const colors = [
        'rgba(0, 240, 255, 0.8)',
        'rgba(180, 0, 255, 0.8)',
        'rgba(0, 255, 136, 0.8)',
        'rgba(255, 107, 53, 0.8)',
        'rgba(255, 51, 102, 0.8)',
        'rgba(255, 204, 0, 0.8)',
        'rgba(102, 126, 234, 0.8)',
        'rgba(118, 75, 162, 0.8)'
    ];
    
    const borderColors = colors.map(c => c.replace('0.8', '1'));
    
    state.currentChart = new Chart(ctx, {
        type: chartType,
        data: {
            labels: chartData.labels.slice(0, 20), // Limit to 20 items
            datasets: [{
                label: chartData.valueColumn,
                data: chartData.values.slice(0, 20),
                backgroundColor: chartType === 'line' ? colors[0] : colors.slice(0, chartData.values.length),
                borderColor: chartType === 'line' ? borderColors[0] : borderColors.slice(0, chartData.values.length),
                borderWidth: 2,
                tension: 0.4,
                fill: chartType === 'line'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: chartType === 'pie' || chartType === 'doughnut',
                    position: 'right',
                    labels: {
                        color: '#a0a0c0',
                        font: { family: 'Rajdhani' }
                    }
                },
                title: {
                    display: true,
                    text: `${chartData.labelColumn} vs ${chartData.valueColumn}`,
                    color: '#00f0ff',
                    font: { family: 'Orbitron', size: 14 }
                }
            },
            scales: chartType === 'pie' || chartType === 'doughnut' ? {} : {
                x: {
                    ticks: { color: '#a0a0c0', font: { family: 'Rajdhani' } },
                    grid: { color: 'rgba(0, 240, 255, 0.1)' }
                },
                y: {
                    ticks: { color: '#a0a0c0', font: { family: 'Rajdhani' } },
                    grid: { color: 'rgba(0, 240, 255, 0.1)' }
                }
            }
        }
    });
}

function analyzeDataForChart(data, columns) {
    // Find a numeric column for values
    let valueColumn = null;
    let labelColumn = null;
    
    // Priority columns for values (numeric)
    const numericPriority = ['count', 'count_', 'sum', 'avg', 'min', 'max', 'value', 'total', 'duration', 'size', 'CounterValue', 'ResultCount'];
    
    // Find value column
    for (const col of columns) {
        const colLower = col.toLowerCase();
        if (numericPriority.some(p => colLower.includes(p.toLowerCase()))) {
            if (typeof data[0][col] === 'number') {
                valueColumn = col;
                break;
            }
        }
    }
    
    // If no priority match, find first numeric column
    if (!valueColumn) {
        for (const col of columns) {
            if (typeof data[0][col] === 'number') {
                valueColumn = col;
                break;
            }
        }
    }
    
    if (!valueColumn) return null;
    
    // Find label column (prefer non-numeric, non-timestamp)
    const labelPriority = ['name', 'type', 'category', 'computer', 'resource', 'level', 'status'];
    
    for (const col of columns) {
        if (col === valueColumn) continue;
        const colLower = col.toLowerCase();
        if (labelPriority.some(p => colLower.includes(p))) {
            labelColumn = col;
            break;
        }
    }
    
    // If no priority match, find first string column
    if (!labelColumn) {
        for (const col of columns) {
            if (col === valueColumn) continue;
            if (col.toLowerCase().includes('time') || col.toLowerCase().includes('date')) continue;
            if (typeof data[0][col] === 'string') {
                labelColumn = col;
                break;
            }
        }
    }
    
    // Fall back to TimeGenerated or first column
    if (!labelColumn) {
        labelColumn = columns.find(c => c.toLowerCase().includes('time')) || columns[0];
    }
    
    // Extract data
    const labels = data.map(row => {
        const val = row[labelColumn];
        if (val instanceof Date) return val.toLocaleString();
        if (typeof val === 'string' && val.length > 30) return val.substring(0, 30) + '...';
        return String(val ?? 'N/A');
    });
    
    const values = data.map(row => {
        const val = row[valueColumn];
        return typeof val === 'number' ? val : parseFloat(val) || 0;
    });
    
    return { labels, values, labelColumn, valueColumn };
}

// ================================================
// API Functions
// ================================================

async function executeNaturalQuery() {
    const question = elements.queryInput.value.trim();
    if (!question) {
        showToast('Please enter a question', 'info');
        return;
    }
    
    showLoading();
    const startTime = performance.now();
    
    try {
        const response = await fetch(`${API_BASE}/api/query/natural`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question })
        });
        
        const data = await response.json();
        const queryTime = Math.round(performance.now() - startTime);
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Show generated KQL
        displayKql(data.kql);
        
        // Display results
        displayResults(data.results, data.columns);
        
        // Update stats
        updateStats(queryTime, data.row_count);
        
        showToast(`Query completed: ${data.row_count} records found`, 'success');
    } catch (error) {
        showError(error.message);
    }
}

async function executeKqlQuery() {
    const kql = elements.queryInput.value.trim();
    if (!kql) {
        showToast('Please enter a KQL query', 'info');
        return;
    }
    
    showLoading();
    const startTime = performance.now();
    
    try {
        const response = await fetch(`${API_BASE}/api/query/kql`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ kql })
        });
        
        const data = await response.json();
        const queryTime = Math.round(performance.now() - startTime);
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        // Display results
        displayResults(data.results, data.columns);
        
        // Update stats
        updateStats(queryTime, data.row_count);
        
        // Hide KQL display since they entered it manually
        elements.kqlDisplay.classList.remove('visible');
        
        showToast(`Query completed: ${data.row_count} records found`, 'success');
    } catch (error) {
        showError(error.message);
    }
}

async function loadTables() {
    elements.tablesList.innerHTML = `
        <div class="loading-inline">
            <i class="fas fa-spinner fa-spin"></i>
            <span>Loading tables...</span>
        </div>
    `;
    
    try {
        const response = await fetch(`${API_BASE}/api/tables`);
        const data = await response.json();
        
        if (data.error) {
            elements.tablesList.innerHTML = `
                <div class="loading-inline">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Error loading tables</span>
                </div>
            `;
            return;
        }
        
        state.tables = data.tables || [];
        renderTables(state.tables);
    } catch (error) {
        elements.tablesList.innerHTML = `
            <div class="loading-inline">
                <i class="fas fa-exclamation-triangle"></i>
                <span>Failed to load tables</span>
            </div>
        `;
    }
}

async function loadTableSchema(tableName) {
    try {
        const response = await fetch(`${API_BASE}/api/table/${tableName}/schema`);
        const data = await response.json();
        
        if (data.error) {
            showToast('Error loading schema: ' + data.error, 'error');
            return;
        }
        
        displaySchema(tableName, data.schema);
    } catch (error) {
        showToast('Failed to load schema', 'error');
    }
}

async function loadSampleQueries() {
    try {
        const response = await fetch(`${API_BASE}/api/sample-queries`);
        const data = await response.json();
        
        if (data.samples) {
            renderSampleQueries(data.samples);
        }
    } catch (error) {
        console.error('Failed to load sample queries:', error);
    }
}

async function exportResults(format) {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No results to export', 'info');
        return;
    }
    
    try {
        window.location.href = `${API_BASE}/api/export/${format}`;
        showToast(`Exporting as ${format.toUpperCase()}...`, 'success');
    } catch (error) {
        showToast('Export failed', 'error');
    }
}

// ================================================
// UI Functions
// ================================================

function displayKql(kql) {
    elements.kqlCode.textContent = kql;
    elements.kqlDisplay.classList.add('visible');
}

function displayResults(results, columns) {
    state.lastResults = results;
    state.lastColumns = columns;
    
    // Hide chart when new results come in
    hideChart();
    
    if (!results || results.length === 0) {
        showEmpty();
        elements.rowCount.textContent = '0 records';
        return;
    }
    
    // Build table header
    elements.tableHead.innerHTML = `
        <tr>
            <th>#</th>
            ${columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}
        </tr>
    `;
    
    // Build table body
    elements.tableBody.innerHTML = results.map((row, index) => `
        <tr>
            <td>${index + 1}</td>
            ${columns.map(col => `<td title="${escapeHtml(String(row[col] ?? ''))}">${escapeHtml(formatValue(row[col]))}</td>`).join('')}
        </tr>
    `).join('');
    
    // Update row count
    elements.rowCount.textContent = `${results.length} records`;
    
    // Show results
    elements.emptyState.style.display = 'none';
    elements.loadingState.style.display = 'none';
    elements.resultsWrapper.style.display = 'block';
}

function renderTables(tables) {
    if (!tables || tables.length === 0) {
        elements.tablesList.innerHTML = `
            <div class="loading-inline">
                <i class="fas fa-inbox"></i>
                <span>No tables found</span>
            </div>
        `;
        return;
    }
    
    elements.tablesList.innerHTML = tables.map(table => `
        <div class="table-item" data-table="${escapeHtml(table)}">
            <span class="table-item-name">${escapeHtml(table)}</span>
            <i class="fas fa-chevron-right table-item-icon"></i>
        </div>
    `).join('');
    
    // Add click handlers
    elements.tablesList.querySelectorAll('.table-item').forEach(item => {
        item.addEventListener('click', () => {
            const tableName = item.dataset.table;
            loadTableSchema(tableName);
        });
        
        // Double click to insert table name
        item.addEventListener('dblclick', () => {
            const tableName = item.dataset.table;
            elements.queryInput.value = `${tableName} | take 10`;
            elements.queryInput.focus();
        });
    });
}

function filterTables() {
    const searchTerm = elements.tableSearch.value.toLowerCase();
    const filtered = state.tables.filter(table => 
        table.toLowerCase().includes(searchTerm)
    );
    renderTables(filtered);
}

function displaySchema(tableName, schema) {
    elements.schemaTableName.textContent = tableName;
    elements.schemaContent.innerHTML = schema.map(col => `
        <div class="schema-row">
            <span class="schema-column-name">${escapeHtml(col.ColumnName || col.name)}</span>
            <span class="schema-column-type">${escapeHtml(col.DataType || col.type)}</span>
        </div>
    `).join('');
    
    elements.schemaSection.style.display = 'block';
}

function closeSchema() {
    elements.schemaSection.style.display = 'none';
}

function renderSampleQueries(samples) {
    const queries = [];
    samples.forEach(category => {
        category.queries.slice(0, 2).forEach(q => queries.push(q));
    });
    
    elements.sampleChips.innerHTML = queries.slice(0, 6).map(query => `
        <span class="sample-chip">${escapeHtml(truncate(query, 35))}</span>
    `).join('');
    
    // Add click handlers
    elements.sampleChips.querySelectorAll('.sample-chip').forEach((chip, index) => {
        chip.addEventListener('click', () => {
            elements.queryInput.value = queries[index];
            elements.queryInput.focus();
        });
    });
}

function showLoading() {
    elements.emptyState.style.display = 'none';
    elements.resultsWrapper.style.display = 'none';
    elements.loadingState.style.display = 'flex';
}

function showEmpty() {
    elements.loadingState.style.display = 'none';
    elements.resultsWrapper.style.display = 'none';
    elements.emptyState.style.display = 'flex';
}

function showError(message) {
    elements.loadingState.style.display = 'none';
    elements.resultsWrapper.style.display = 'none';
    elements.emptyState.style.display = 'flex';
    showToast('Error: ' + message, 'error');
}

function updateConnectionStatus(connected) {
    state.isConnected = connected;
    const statusEl = elements.connectionStatus;
    
    if (connected) {
        statusEl.classList.remove('error');
        statusEl.querySelector('.status-text').textContent = 'CONNECTED';
    } else {
        statusEl.classList.add('error');
        statusEl.querySelector('.status-text').textContent = 'DISCONNECTED';
    }
}

function updateStats(queryTime, rowCount) {
    state.queryCount++;
    elements.queryTime.textContent = `${queryTime}ms`;
    elements.totalQueries.textContent = state.queryCount;
}

function clearInput() {
    elements.queryInput.value = '';
    elements.kqlDisplay.classList.remove('visible');
    elements.queryInput.focus();
}

function copyKql() {
    const kql = elements.kqlCode.textContent;
    navigator.clipboard.writeText(kql).then(() => {
        showToast('KQL copied to clipboard', 'success');
    }).catch(() => {
        showToast('Failed to copy', 'error');
    });
}

// ================================================
// Toast Notifications
// ================================================

function showToast(message, type = 'info') {
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    elements.toastContainer.appendChild(toast);
    
    // Close button
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });
    
    // Auto remove
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// ================================================
// Utility Functions
// ================================================

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

function formatValue(value) {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.slice(0, length) + '...' : str;
}

// ================================================
// Clock
// ================================================

function startClock() {
    function updateClock() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        elements.currentTime.textContent = `${hours}:${minutes}:${seconds}`;
    }
    
    updateClock();
    setInterval(updateClock, 1000);
}

// ================================================
// Particles Animation
// ================================================

function createParticles() {
    const container = document.getElementById('particles');
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = `${Math.random() * 100}%`;
        particle.style.animationDelay = `${Math.random() * 15}s`;
        particle.style.animationDuration = `${10 + Math.random() * 20}s`;
        container.appendChild(particle);
    }
}

// ================================================
// Keyboard Shortcuts
// ================================================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to analyze
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (document.activeElement === elements.queryInput) {
            e.preventDefault();
            executeNaturalQuery();
        }
    }
    
    // Escape to clear
    if (e.key === 'Escape') {
        clearInput();
    }
    
    // Focus input with /
    if (e.key === '/' && document.activeElement !== elements.queryInput) {
        e.preventDefault();
        elements.queryInput.focus();
    }
});
