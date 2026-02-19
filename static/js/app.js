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
    currentChart: null,
    // Current query context for chat
    currentKql: null,
    currentResults: null,
    // New state for features
    selectedTimeRange: '24h',
    timeRangeManuallySet: false, // Track if user manually selected time range
    customTimeStart: null,
    customTimeEnd: null,
    queryHistory: [],
    favorites: [],
    chatHistory: [],
    chatMode: false
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
    exportPdfBtn: document.getElementById('exportPdfBtn'),
    
    // Chart
    showChartBtn: document.getElementById('showChartBtn'),
    chartContainer: document.getElementById('chartContainer'),
    chartType: document.getElementById('chartType'),
    closeChartBtn: document.getElementById('closeChartBtn'),
    resultsChart: document.getElementById('resultsChart'),
    
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
    
    // Time Range Picker
    timeRangePicker: document.getElementById('timeRangePicker'),
    customTimeBtn: document.getElementById('customTimeBtn'),
    customTimePicker: document.getElementById('customTimePicker'),
    customTimeStart: document.getElementById('customTimeStart'),
    customTimeEnd: document.getElementById('customTimeEnd'),
    applyCustomTime: document.getElementById('applyCustomTime'),
    
    // History & Favorites
    historySection: document.getElementById('historySection'),
    clearHistoryBtn: document.getElementById('clearHistoryBtn'),
    
    // AI Chat
    chatModal: document.getElementById('chatModal'),
    chatBtn: document.getElementById('chatModeBtn'),
    closeChatBtn: document.getElementById('closeChatBtn'),
    chatMessages: document.getElementById('chatMessages'),
    chatInput: document.getElementById('chatInput'),
    sendChatBtn: document.getElementById('sendChatBtn'),
    
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
    loadHistoryFromStorage();
    loadFavoritesFromStorage();
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
    if (document.getElementById('exportPdfBtn')) {
        document.getElementById('exportPdfBtn').addEventListener('click', () => exportToPdf());
    }
    
    // Chart controls
    const showChartBtn = document.getElementById('showChartBtn');
    const closeChartBtn = document.getElementById('closeChartBtn');
    const chartType = document.getElementById('chartType');
    const toggleViewBtn = document.getElementById('toggleViewBtn');
    
    if (showChartBtn) {
        showChartBtn.addEventListener('click', showChart);
    }
    if (toggleViewBtn) {
        toggleViewBtn.addEventListener('click', toggleChartView);
    }
    if (closeChartBtn) {
        closeChartBtn.addEventListener('click', hideChart);
    }
    if (chartType) {
        chartType.addEventListener('change', updateChart);
    }
    
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
    
    // Time Range Picker
    setupTimeRangePicker();
    
    // History & Favorites
    setupHistoryAndFavorites();
    
    // AI Chat Mode
    setupChatMode();
    
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
        // Get time range filter
        const timeFilter = getTimeRangeFilter();
        
        const response = await fetch(`${API_BASE}/api/query/natural`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, timeFilter })
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
        
        // Store current state for chat context
        state.currentKql = data.kql;
        state.currentResults = data.results;
        
        // Show generated KQL
        displayKql(data.kql);
        
        // Display results IMMEDIATELY
        displayResults(data.results, data.columns);
        
        // Update stats
        updateStats(queryTime, data.row_count);
        
        // Add to query history
        addToHistory(question, data.kql, data.row_count);
        
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

async function exportToPdf() {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No results to export', 'info');
        return;
    }
    
    showToast('Generating PDF...', 'info');
    
    try {
        // Create a printable HTML document
        const printWindow = window.open('', '_blank');
        const columns = state.lastColumns || Object.keys(state.lastResults[0]);
        
        let tableHtml = '<table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; font-size: 10px;">';
        
        // Header
        tableHtml += '<thead><tr style="background: #1a1a2e; color: #00f0ff;">';
        columns.forEach(col => {
            tableHtml += `<th style="border: 1px solid #333; padding: 8px; text-align: left;">${col}</th>`;
        });
        tableHtml += '</tr></thead>';
        
        // Body
        tableHtml += '<tbody>';
        state.lastResults.forEach((row, idx) => {
            const bgColor = idx % 2 === 0 ? '#0a0a1a' : '#12122a';
            tableHtml += `<tr style="background: ${bgColor}; color: #e0e0e0;">`;
            columns.forEach(col => {
                let value = row[col];
                if (value === null || value === undefined) value = '';
                if (typeof value === 'object') value = JSON.stringify(value);
                // Truncate long values
                const displayValue = String(value).length > 100 ? String(value).substring(0, 100) + '...' : String(value);
                tableHtml += `<td style="border: 1px solid #333; padding: 6px; max-width: 200px; word-wrap: break-word;">${displayValue}</td>`;
            });
            tableHtml += '</tr>';
        });
        tableHtml += '</tbody></table>';
        
        const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>ADIC LogAssist AI - Export</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        margin: 20px; 
                        background: #0a0a1a; 
                        color: #e0e0e0;
                    }
                    h1 { color: #00f0ff; font-size: 18px; }
                    .meta { color: #888; font-size: 12px; margin-bottom: 20px; }
                    @media print {
                        body { background: white; color: black; }
                        table { font-size: 8px; }
                        th { background: #333 !important; color: white !important; }
                        tr { background: white !important; color: black !important; }
                    }
                </style>
            </head>
            <body>
                <h1>ADIC LogAssist AI - Query Results</h1>
                <div class="meta">
                    <p>Exported: ${new Date().toLocaleString()}</p>
                    <p>Total Records: ${state.lastResults.length}</p>
                    ${state.lastKql ? `<p>Query: <code>${state.lastKql.substring(0, 200)}...</code></p>` : ''}
                </div>
                ${tableHtml}
                <script>
                    window.onload = function() {
                        window.print();
                    }
                </script>
            </body>
            </html>
        `;
        
        printWindow.document.write(htmlContent);
        printWindow.document.close();
        
        showToast('PDF ready - use Print dialog to save as PDF', 'success');
    } catch (error) {
        console.error('PDF export error:', error);
        showToast('PDF export failed', 'error');
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

function showChart() {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No data to visualize', 'info');
        return;
    }
    
    const chartContainer = document.getElementById('chartContainer');
    if (chartContainer) {
        chartContainer.style.display = 'block';
    }
    
    updateChart();
}

function updateChart() {
    const canvas = document.getElementById('resultsChart');
    const chartTypeSelect = document.getElementById('chartType');
    if (!canvas || !state.lastResults || state.lastResults.length === 0) return;
    
    // Destroy existing chart
    if (state.currentChart) {
        state.currentChart.destroy();
    }
    
    const chartType = chartTypeSelect?.value || 'bar';
    const results = state.lastResults;
    const columns = state.lastColumns || Object.keys(results[0]);
    
    // Find suitable columns for charting
    // Look for a label column (string) and value columns (numeric)
    let labelColumn = null;
    let valueColumns = [];
    
    columns.forEach(col => {
        const sampleValue = results[0][col];
        if (typeof sampleValue === 'number') {
            valueColumns.push(col);
        } else if (!labelColumn && typeof sampleValue === 'string') {
            labelColumn = col;
        }
    });
    
    // If no numeric columns, try to count occurrences
    if (valueColumns.length === 0) {
        // Create a count-based chart
        const countColumn = labelColumn || columns[0];
        const counts = {};
        results.forEach(row => {
            const key = String(row[countColumn] || 'Unknown').substring(0, 30);
            counts[key] = (counts[key] || 0) + 1;
        });
        
        const labels = Object.keys(counts).slice(0, 20);
        const data = labels.map(l => counts[l]);
        
        createChart(canvas, chartType, labels, [{ label: 'Count', data }]);
    } else {
        // Use numeric columns
        const labels = results.slice(0, 50).map((row, i) => {
            if (labelColumn) {
                return String(row[labelColumn] || '').substring(0, 20);
            }
            return `Row ${i + 1}`;
        });
        
        const datasets = valueColumns.slice(0, 3).map((col, idx) => ({
            label: col,
            data: results.slice(0, 50).map(row => row[col] || 0)
        }));
        
        createChart(canvas, chartType, labels, datasets);
    }
}

function createChart(canvas, type, labels, datasets) {
    const colors = [
        { bg: 'rgba(0, 240, 255, 0.6)', border: '#00f0ff' },
        { bg: 'rgba(180, 0, 255, 0.6)', border: '#b400ff' },
        { bg: 'rgba(0, 255, 136, 0.6)', border: '#00ff88' },
        { bg: 'rgba(255, 107, 53, 0.6)', border: '#ff6b35' }
    ];
    
    const chartDatasets = datasets.map((ds, idx) => {
        const colorIdx = idx % colors.length;
        return {
            label: ds.label,
            data: ds.data,
            backgroundColor: type === 'pie' ? 
                ds.data.map((_, i) => colors[i % colors.length].bg) : 
                colors[colorIdx].bg,
            borderColor: type === 'pie' ? 
                ds.data.map((_, i) => colors[i % colors.length].border) : 
                colors[colorIdx].border,
            borderWidth: 2
        };
    });
    
    state.currentChart = new Chart(canvas, {
        type: type,
        data: {
            labels: labels,
            datasets: chartDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: { color: '#e0e0e0' }
                }
            },
            scales: type !== 'pie' ? {
                x: {
                    ticks: { color: '#a0a0c0' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                },
                y: {
                    ticks: { color: '#a0a0c0' },
                    grid: { color: 'rgba(255,255,255,0.1)' }
                }
            } : {}
        }
    });
}

function toggleChartView() {
    const chartContainer = document.getElementById('chartContainer');
    if (chartContainer && chartContainer.style.display !== 'none') {
        hideChart();
    } else {
        showChart();
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
// Time Range Picker
// ================================================

function setupTimeRangePicker() {
    // Time range button clicks
    document.querySelectorAll('.time-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.selectedTimeRange = btn.dataset.range;
            state.timeRangeManuallySet = true; // User manually selected a time range
            
            // Hide custom picker if preset selected
            if (state.selectedTimeRange !== 'custom') {
                elements.customTimePicker?.classList.add('hidden');
            }
        });
    });
    
    // Custom range button
    elements.customTimeBtn?.addEventListener('click', () => {
        document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
        elements.customTimeBtn.classList.add('active');
        state.selectedTimeRange = 'custom';
        state.timeRangeManuallySet = true;
        elements.customTimePicker?.classList.remove('hidden');
    });
    
    // Apply custom time
    elements.applyCustomTime?.addEventListener('click', () => {
        const start = elements.customTimeStart?.value;
        const end = elements.customTimeEnd?.value;
        if (start && end) {
            state.customTimeStart = start;
            state.customTimeEnd = end;
            showToast('Custom time range applied', 'success');
        } else {
            showToast('Please select both start and end times', 'warning');
        }
    });
}

function getTimeRangeFilter() {
    // Always apply the selected time range filter
    const now = new Date();
    let startTime;
    
    switch (state.selectedTimeRange) {
        case '1h':
            startTime = new Date(now - 60 * 60 * 1000);
            break;
        case '6h':
            startTime = new Date(now - 6 * 60 * 60 * 1000);
            break;
        case '24h':
            startTime = new Date(now - 24 * 60 * 60 * 1000);
            break;
        case '7d':
            startTime = new Date(now - 7 * 24 * 60 * 60 * 1000);
            break;
        case '30d':
            startTime = new Date(now - 30 * 24 * 60 * 60 * 1000);
            break;
        case 'custom':
            if (state.customTimeStart && state.customTimeEnd) {
                return `| where TimeGenerated between (datetime('${state.customTimeStart}') .. datetime('${state.customTimeEnd}'))`;
            }
            // Fall back to 24h if custom not set
            startTime = new Date(now - 24 * 60 * 60 * 1000);
            break;
        default:
            startTime = new Date(now - 24 * 60 * 60 * 1000);
    }
    
    return startTime ? `| where TimeGenerated >= datetime('${startTime.toISOString()}')` : '';
}

// ================================================
// Query History & Favorites
// ================================================

function setupHistoryAndFavorites() {
    // Load from localStorage
    loadHistoryFromStorage();
    loadFavoritesFromStorage();
    
    // Tab switching
    document.querySelectorAll('.history-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.history-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            const tabType = tab.dataset.tab;
            document.querySelectorAll('.history-content').forEach(content => {
                content.classList.toggle('hidden', content.id !== `${tabType}-list`);
            });
        });
    });
    
    // Clear history button
    elements.clearHistoryBtn?.addEventListener('click', () => {
        if (confirm('Clear all query history?')) {
            state.queryHistory = [];
            saveHistoryToStorage();
            renderHistory();
            showToast('History cleared', 'success');
        }
    });
    
    // Initial render
    renderHistory();
    renderFavorites();
}

function loadHistoryFromStorage() {
    try {
        const saved = localStorage.getItem('adicLogAssist_history');
        state.queryHistory = saved ? JSON.parse(saved) : [];
    } catch (e) {
        state.queryHistory = [];
    }
}

function saveHistoryToStorage() {
    try {
        localStorage.setItem('adicLogAssist_history', JSON.stringify(state.queryHistory.slice(0, 50)));
    } catch (e) {
        console.warn('Failed to save history:', e);
    }
}

function loadFavoritesFromStorage() {
    try {
        const saved = localStorage.getItem('adicLogAssist_favorites');
        state.favorites = saved ? JSON.parse(saved) : [];
    } catch (e) {
        state.favorites = [];
    }
}

function saveFavoritesToStorage() {
    try {
        localStorage.setItem('adicLogAssist_favorites', JSON.stringify(state.favorites));
    } catch (e) {
        console.warn('Failed to save favorites:', e);
    }
}

function addToHistory(query, kql, resultCount) {
    const entry = {
        id: Date.now(),
        query: query,
        kql: kql,
        resultCount: resultCount,
        timestamp: new Date().toISOString()
    };
    
    // Remove duplicate if exists
    state.queryHistory = state.queryHistory.filter(h => h.query !== query);
    
    // Add to front
    state.queryHistory.unshift(entry);
    
    // Keep max 50
    state.queryHistory = state.queryHistory.slice(0, 50);
    
    saveHistoryToStorage();
    renderHistory();
}

function toggleFavorite(query, kql) {
    const exists = state.favorites.find(f => f.query === query);
    
    if (exists) {
        state.favorites = state.favorites.filter(f => f.query !== query);
        showToast('Removed from favorites', 'info');
    } else {
        state.favorites.unshift({
            id: Date.now(),
            query: query,
            kql: kql,
            timestamp: new Date().toISOString()
        });
        showToast('Added to favorites', 'success');
    }
    
    saveFavoritesToStorage();
    renderFavorites();
    renderHistory(); // Update star icons
}

function isFavorite(query) {
    return state.favorites.some(f => f.query === query);
}

function renderHistory() {
    const container = document.getElementById('history-list');
    if (!container) return;
    
    if (state.queryHistory.length === 0) {
        container.innerHTML = '<div class="empty-state">No query history yet</div>';
        return;
    }
    
    container.innerHTML = state.queryHistory.map((item, index) => `
        <div class="history-item">
            <div class="history-item-content" data-index="${index}" data-type="history">
                <div class="history-query">${escapeHtml(item.query)}</div>
                <div class="history-meta">
                    <span>${formatTimeAgo(item.timestamp)}</span>
                    <span>${item.resultCount || 0} results</span>
                </div>
            </div>
            <button class="favorite-btn ${isFavorite(item.query) ? 'active' : ''}" data-index="${index}" data-type="history-fav">
                ★
            </button>
        </div>
    `).join('');
    
    // Attach click handlers
    container.querySelectorAll('.history-item-content').forEach(el => {
        el.addEventListener('click', () => {
            const idx = parseInt(el.dataset.index);
            runHistoryQuery(state.queryHistory[idx].query);
        });
    });
    container.querySelectorAll('.favorite-btn').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = parseInt(el.dataset.index);
            const item = state.queryHistory[idx];
            toggleFavorite(item.query, item.kql || '');
        });
    });
}

function renderFavorites() {
    const container = document.getElementById('favorites-list');
    if (!container) return;
    
    if (state.favorites.length === 0) {
        container.innerHTML = '<div class="empty-state">No favorites yet. Star a query to save it.</div>';
        return;
    }
    
    container.innerHTML = state.favorites.map((item, index) => `
        <div class="history-item">
            <div class="history-item-content" data-index="${index}" data-type="favorite">
                <div class="history-query">${escapeHtml(item.query)}</div>
                <div class="history-meta">
                    <span>Saved ${formatTimeAgo(item.timestamp)}</span>
                </div>
            </div>
            <button class="favorite-btn active" data-index="${index}" data-type="favorite-fav">
                ★
            </button>
        </div>
    `).join('');
    
    // Attach click handlers
    container.querySelectorAll('.history-item-content').forEach(el => {
        el.addEventListener('click', () => {
            const idx = parseInt(el.dataset.index);
            runHistoryQuery(state.favorites[idx].query);
        });
    });
    container.querySelectorAll('.favorite-btn').forEach(el => {
        el.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = parseInt(el.dataset.index);
            const item = state.favorites[idx];
            toggleFavorite(item.query, item.kql || '');
        });
    });
}

function runHistoryQuery(query) {
    elements.queryInput.value = query;
    executeNaturalQuery();
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatTimeAgo(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diff = Math.floor((now - then) / 1000);
    
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return then.toLocaleDateString();
}

// ================================================
// AI Chat Mode
// ================================================

function setupChatMode() {
    // Open chat button
    elements.chatBtn?.addEventListener('click', openChatModal);
    
    // Close chat
    elements.closeChatBtn?.addEventListener('click', closeChatModal);
    
    // Send message
    elements.sendChatBtn?.addEventListener('click', sendChatMessage);
    
    // Enter to send
    elements.chatInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // Close on backdrop click
    elements.chatModal?.addEventListener('click', (e) => {
        if (e.target === elements.chatModal) {
            closeChatModal();
        }
    });
}

function openChatModal() {
    if (!elements.chatModal) return;
    
    elements.chatModal.classList.remove('hidden');
    elements.chatInput?.focus();
    
    // Update context info
    updateChatContext();
    
    // Show welcome message if first time
    if (state.chatHistory.length === 0) {
        addChatMessage('assistant', 'Hello! I can help you analyze your Azure logs. Ask me questions about your query results, request summaries, or ask for specific insights.');
    }
}

function closeChatModal() {
    elements.chatModal?.classList.add('hidden');
}

function updateChatContext() {
    const contextEl = document.getElementById('chat-context-info');
    if (!contextEl) return;
    
    const hasResults = state.currentResults && state.currentResults.length > 0;
    const hasKql = state.currentKql;
    
    if (hasResults) {
        contextEl.innerHTML = `
            <strong>Context:</strong> ${state.currentResults.length} results from query
            ${hasKql ? `<br><code style="font-size: 0.75rem;">${state.currentKql.substring(0, 80)}...</code>` : ''}
        `;
    } else {
        contextEl.innerHTML = '<em>No query results loaded. Run a query first for context-aware chat.</em>';
    }
}

async function sendChatMessage() {
    const input = elements.chatInput;
    const message = input?.value?.trim();
    
    if (!message) return;
    
    // Add user message
    addChatMessage('user', message);
    input.value = '';
    
    // Show typing indicator
    const typingId = addChatMessage('assistant', '<div class="typing-indicator"><span></span><span></span><span></span></div>', true);
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                context: {
                    kql: state.currentKql,
                    results: state.currentResults?.slice(0, 20), // Send first 20 results for context
                    resultCount: state.currentResults?.length || 0
                },
                history: state.chatHistory.slice(-10) // Last 10 messages for context
            })
        });
        
        // Remove typing indicator
        removeChatMessage(typingId);
        
        if (!response.ok) {
            throw new Error('Chat request failed');
        }
        
        const data = await response.json();
        
        // Add assistant response
        addChatMessage('assistant', data.response);
        
        // Handle suggested query from AI (single query)
        if (data.suggested_query) {
            addSuggestedQueryButton(data.suggested_query);
        }
        
        // Handle suggested queries array if any
        if (data.suggestedQueries && data.suggestedQueries.length > 0) {
            addSuggestedQueries(data.suggestedQueries);
        }
        
    } catch (error) {
        removeChatMessage(typingId);
        addChatMessage('assistant', 'Sorry, I encountered an error. Please try again.');
        console.error('Chat error:', error);
    }
}

function addChatMessage(role, content, isTemp = false) {
    const container = elements.chatMessages;
    if (!container) return null;
    
    const msgId = `msg-${Date.now()}`;
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    div.id = msgId;
    
    if (isTemp) {
        div.innerHTML = content;
    } else {
        // Simple markdown-like formatting
        let formatted = content
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        
        div.innerHTML = `<div class="message-content">${formatted}</div>`;
        
        // Save to history (not temp messages)
        state.chatHistory.push({ role, content });
    }
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    
    return msgId;
}

function removeChatMessage(msgId) {
    document.getElementById(msgId)?.remove();
}

function addSuggestedQueryButton(query) {
    const container = elements.chatMessages;
    if (!container || !query) return;
    
    const div = document.createElement('div');
    div.className = 'suggested-queries';
    div.innerHTML = `
        <div class="suggested-label">Suggested query:</div>
        <div class="suggested-query-code"><code>${escapeHtml(query)}</code></div>
        <button class="suggested-query-btn run-query-btn" data-query="${escapeHtml(query)}">
            <i class="fas fa-play"></i> Run this query
        </button>
    `;
    
    // Add click handler
    div.querySelector('.run-query-btn').addEventListener('click', function() {
        const q = this.dataset.query;
        closeChatModal();
        elements.queryInput.value = q;
        executeNaturalQuery();
    });
    
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addSuggestedQueries(queries) {
    const container = elements.chatMessages;
    if (!container || !queries.length) return;
    
    const div = document.createElement('div');
    div.className = 'suggested-queries';
    div.innerHTML = `
        <div class="suggested-label">Suggested queries:</div>
        ${queries.map(q => `<button class="suggested-query-btn" onclick="useSuggestedQuery('${escapeHtml(q)}')">${escapeHtml(q)}</button>`).join('')}
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function useSuggestedQuery(query) {
    closeChatModal();
    elements.queryInput.value = query;
    executeNaturalQuery();
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
    
    // Escape to close modals or clear
    if (e.key === 'Escape') {
        if (elements.chatModal && !elements.chatModal.classList.contains('hidden')) {
            closeChatModal();
        } else {
            clearInput();
        }
    }
    
    // Focus input with /
    if (e.key === '/' && document.activeElement !== elements.queryInput) {
        e.preventDefault();
        elements.queryInput.focus();
    }
    
    // Ctrl+H for history
    if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
        e.preventDefault();
        document.querySelector('.history-tab[data-tab="history"]')?.click();
    }
});
