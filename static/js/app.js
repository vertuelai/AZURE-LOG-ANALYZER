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
    lastQuestion: null,
    lastKql: null,
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
    
    // Tables
    tablesList: document.getElementById('tablesList'),
    tableSearch: document.getElementById('tableSearch'),
    refreshTablesBtn: document.getElementById('refreshTablesBtn'),
    schemaSection: document.getElementById('schemaSection'),
    schemaTableName: document.getElementById('schemaTableName'),
    schemaContent: document.getElementById('schemaContent'),
    closeSchemaBtn: document.getElementById('closeSchemaBtn'),
    
    // AI Insights
    aiInsightsContainer: document.getElementById('aiInsightsContainer'),
    aiInsightsContent: document.getElementById('aiInsightsContent'),
    aiInsightsLoading: document.getElementById('aiInsightsLoading'),
    aiInsightsText: document.getElementById('aiInsightsText'),
    refreshInsightsBtn: document.getElementById('refreshInsightsBtn'),
    closeInsightsBtn: document.getElementById('closeInsightsBtn'),
    
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
    
    // AI Insights controls
    if (elements.refreshInsightsBtn) {
        elements.refreshInsightsBtn.addEventListener('click', fetchAiInsights);
    }
    if (elements.closeInsightsBtn) {
        elements.closeInsightsBtn.addEventListener('click', closeAiInsights);
    }
    
    // Toggle tables panel minimize/maximize
    const toggleTablesBtn = document.getElementById('toggleTablesBtn');
    if (toggleTablesBtn) {
        toggleTablesBtn.addEventListener('click', toggleTablesPanel);
    }
}

// Toggle tables panel minimize/maximize
function toggleTablesPanel() {
    const tablesPanel = document.getElementById('tablesPanel');
    const toggleIcon = document.getElementById('toggleTablesIcon');
    const tablesList = document.getElementById('tablesList');
    const tableSearch = document.querySelector('.tables-panel .search-box');
    const schemaSection = document.getElementById('schemaSection');
    
    if (tablesPanel.classList.contains('minimized')) {
        // Maximize
        tablesPanel.classList.remove('minimized');
        toggleIcon.classList.remove('fa-plus');
        toggleIcon.classList.add('fa-minus');
        if (tablesList) tablesList.style.display = '';
        if (tableSearch) tableSearch.style.display = '';
        if (schemaSection) schemaSection.style.display = '';
    } else {
        // Minimize
        tablesPanel.classList.add('minimized');
        toggleIcon.classList.remove('fa-minus');
        toggleIcon.classList.add('fa-plus');
        if (tablesList) tablesList.style.display = 'none';
        if (tableSearch) tableSearch.style.display = 'none';
        if (schemaSection) schemaSection.style.display = 'none';
    }
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
        
        // Store for AI analysis
        state.lastQuestion = question;
        state.lastKql = data.kql;
        state.lastResults = data.results;
        state.lastColumns = data.columns;
        
        // Show generated KQL
        displayKql(data.kql);
        
        // Display results IMMEDIATELY
        displayResults(data.results, data.columns);
        
        // Update stats
        updateStats(queryTime, data.row_count);
        
        showToast(`Query completed: ${data.row_count} records found`, 'success');
        
        // Fetch AI insights asynchronously (non-blocking)
        if (data.results && data.results.length > 0) {
            fetchAiInsights();
        }
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
        
        // Store for AI analysis
        state.lastQuestion = '';
        state.lastKql = kql;
        state.lastResults = data.results;
        state.lastColumns = data.columns;
        
        // Display results IMMEDIATELY
        displayResults(data.results, data.columns);
        
        // Update stats
        updateStats(queryTime, data.row_count);
        
        // Hide KQL display since they entered it manually
        elements.kqlDisplay.classList.remove('visible');
        
        showToast(`Query completed: ${data.row_count} records found`, 'success');
        
        // Fetch AI insights asynchronously (non-blocking)
        if (data.results && data.results.length > 0) {
            fetchAiInsights();
        }
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

function hideChart() {
    if (state.currentChart) {
        state.currentChart.destroy();
        state.currentChart = null;
    }
    const chartContainer = document.getElementById('chartContainer');
    if (chartContainer) {
        chartContainer.style.display = 'none';
    }
}

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

// ================================================
// AI Insights Functions
// ================================================

async function fetchAiInsights() {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No results to analyze', 'info');
        return;
    }
    
    // Show insights container with loading state
    showAiInsightsLoading();
    
    try {
        const response = await fetch(`${API_BASE}/api/analyze/results`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                results: state.lastResults,
                columns: state.lastColumns,
                question: state.lastQuestion || '',
                kql: state.lastKql || ''
            })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showAiInsightsError(data.error);
            return;
        }
        
        // Display the AI insights
        displayAiInsights(data.insights);
    } catch (error) {
        showAiInsightsError(error.message);
    }
}

function showAiInsightsLoading() {
    if (elements.aiInsightsContainer) {
        elements.aiInsightsContainer.style.display = 'block';
    }
    if (elements.aiInsightsLoading) {
        elements.aiInsightsLoading.style.display = 'flex';
    }
    if (elements.aiInsightsText) {
        elements.aiInsightsText.style.display = 'none';
        elements.aiInsightsText.innerHTML = '';
    }
}

function displayAiInsights(insights) {
    if (elements.aiInsightsLoading) {
        elements.aiInsightsLoading.style.display = 'none';
    }
    if (elements.aiInsightsText) {
        // Convert markdown to HTML (simple conversion)
        const htmlContent = markdownToHtml(insights);
        elements.aiInsightsText.innerHTML = htmlContent;
        elements.aiInsightsText.style.display = 'block';
    }
    if (elements.aiInsightsContainer) {
        elements.aiInsightsContainer.style.display = 'block';
    }
}

function showAiInsightsError(error) {
    if (elements.aiInsightsLoading) {
        elements.aiInsightsLoading.style.display = 'none';
    }
    if (elements.aiInsightsText) {
        elements.aiInsightsText.innerHTML = `<div class="ai-error"><i class="fas fa-exclamation-triangle"></i> ${escapeHtml(error)}</div>`;
        elements.aiInsightsText.style.display = 'block';
    }
}

function closeAiInsights() {
    if (elements.aiInsightsContainer) {
        elements.aiInsightsContainer.style.display = 'none';
    }
}

function markdownToHtml(markdown) {
    if (!markdown) return '';
    
    let html = escapeHtml(markdown);
    
    // Convert markdown to HTML
    // Bold: **text** or __text__
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
    
    // Italic: *text* or _text_
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
    
    // Headers: ## Header
    html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');
    
    // Bullet points: - item or * item
    html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
    
    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
    
    // Numbered lists: 1. item
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    
    // Code: `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    
    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    
    // Wrap in paragraph if not already wrapped
    if (!html.startsWith('<')) {
        html = '<p>' + html + '</p>';
    }
    
    return html;
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
