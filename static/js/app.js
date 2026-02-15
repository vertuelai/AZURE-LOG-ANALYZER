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
    generateReportBtn: document.getElementById('generateReportBtn'),
    
    // Scroll Navigation
    scrollStartBtn: document.getElementById('scrollStartBtn'),
    scrollEndBtn: document.getElementById('scrollEndBtn'),
    fullscreenBtn: document.getElementById('fullscreenBtn'),
    
    // Visualization Dropdown
    vizDropdown: document.getElementById('vizDropdown'),
    vizDropdownBtn: document.getElementById('vizDropdownBtn'),
    vizDropdownMenu: document.getElementById('vizDropdownMenu'),
    
    // Visualization Container
    vizContainer: document.getElementById('vizContainer'),
    vizTitle: document.getElementById('vizTitle'),
    resultsChart: document.getElementById('resultsChart'),
    chartType: document.getElementById('chartType'),
    dataColumn: document.getElementById('dataColumn'),
    closeVizBtn: document.getElementById('closeVizBtn'),
    
    // Statistics Container
    statsContainer: document.getElementById('statsContainer'),
    statsTitle: document.getElementById('statsTitle'),
    statsContent: document.getElementById('statsContent'),
    closeStatsBtn: document.getElementById('closeStatsBtn'),
    
    // Tables
    tablesList: document.getElementById('tablesList'),
    tableSearch: document.getElementById('tableSearch'),
    refreshTablesBtn: document.getElementById('refreshTablesBtn'),
    schemaSection: document.getElementById('schemaSection'),
    schemaTableName: document.getElementById('schemaTableName'),
    schemaContent: document.getElementById('schemaContent'),
    closeSchemaBtn: document.getElementById('closeSchemaBtn'),
    
    // Panel Toggles
    tablesPanel: document.getElementById('tablesPanel'),
    toggleTablesBtn: document.getElementById('toggleTablesBtn'),
    toggleTablesIcon: document.getElementById('toggleTablesIcon'),
    toggleQueryBtn: document.getElementById('toggleQueryBtn'),
    queryPanel: document.getElementById('queryPanel'),
    queryContent: document.getElementById('queryContent'),
    tablesContent: document.getElementById('tablesContent'),
    resultsPanel: document.getElementById('resultsPanel'),
    
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
    
    // Toggle query panel
    if (elements.toggleQueryBtn) {
        elements.toggleQueryBtn.addEventListener('click', toggleQueryPanel);
    }
    
    // Scroll navigation
    if (elements.scrollStartBtn) {
        elements.scrollStartBtn.addEventListener('click', scrollToStart);
    }
    if (elements.scrollEndBtn) {
        elements.scrollEndBtn.addEventListener('click', scrollToEnd);
    }
    if (elements.fullscreenBtn) {
        elements.fullscreenBtn.addEventListener('click', toggleFullscreen);
    }
    
    // Visualization Dropdown
    if (elements.vizDropdownBtn) {
        elements.vizDropdownBtn.addEventListener('click', toggleVizDropdown);
    }
    
    // Dropdown items
    document.querySelectorAll('.dropdown-item[data-viz]').forEach(item => {
        item.addEventListener('click', (e) => {
            const vizType = e.currentTarget.getAttribute('data-viz');
            handleVisualization(vizType);
            closeVizDropdown();
        });
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown')) {
            closeVizDropdown();
        }
    });
    
    // Visualization controls
    if (elements.closeVizBtn) {
        elements.closeVizBtn.addEventListener('click', hideVisualization);
    }
    if (elements.closeStatsBtn) {
        elements.closeStatsBtn.addEventListener('click', hideStats);
    }
    if (elements.chartType) {
        elements.chartType.addEventListener('change', () => {
            if (state.lastResults && state.lastResults.length > 0) {
                renderChart();
            }
        });
    }
    if (elements.dataColumn) {
        elements.dataColumn.addEventListener('change', () => {
            if (state.lastResults && state.lastResults.length > 0) {
                renderChart();
            }
        });
    }
    
    // Generate Report
    if (elements.generateReportBtn) {
        elements.generateReportBtn.addEventListener('click', generatePDFReport);
    }
}

// ================================================
// Tables Panel Toggle
// ================================================

function toggleTablesPanel() {
    const panel = elements.tablesPanel;
    const content = elements.tablesContent;
    const icon = elements.toggleTablesIcon;
    
    if (!panel) return;
    
    const isMinimized = panel.classList.toggle('minimized');
    
    if (icon) {
        icon.classList.remove('fa-minus', 'fa-plus');
        icon.classList.add(isMinimized ? 'fa-plus' : 'fa-minus');
    }
    
    if (content) {
        content.style.display = isMinimized ? 'none' : '';
    }
}

// ================================================
// Query Panel Toggle
// ================================================

function toggleQueryPanel() {
    const panel = elements.queryPanel;
    const content = elements.queryContent;
    
    if (!panel || !content) return;
    
    const isMinimized = panel.classList.toggle('minimized');
    content.style.display = isMinimized ? 'none' : '';
}

// ================================================
// Scroll Navigation Functions
// ================================================

function scrollToStart() {
    const wrapper = elements.resultsWrapper;
    if (wrapper) {
        wrapper.scrollTo({ left: 0, behavior: 'smooth' });
    }
}

function scrollToEnd() {
    const wrapper = elements.resultsWrapper;
    if (wrapper) {
        wrapper.scrollTo({ left: wrapper.scrollWidth, behavior: 'smooth' });
    }
}

function toggleFullscreen() {
    const panel = elements.resultsPanel;
    if (!panel) return;
    
    const isFullscreen = panel.classList.toggle('fullscreen');
    
    if (elements.fullscreenBtn) {
        elements.fullscreenBtn.innerHTML = isFullscreen 
            ? '<i class="fas fa-compress"></i>'
            : '<i class="fas fa-expand"></i>';
    }
    
    // Hide/show bottom panels
    const bottomPanels = document.querySelector('.bottom-panels');
    if (bottomPanels) {
        bottomPanels.style.display = isFullscreen ? 'none' : '';
    }
}

// ================================================
// Visualization Dropdown Functions
// ================================================

function toggleVizDropdown() {
    const menu = elements.vizDropdownMenu;
    if (menu) {
        menu.classList.toggle('show');
    }
}

function closeVizDropdown() {
    const menu = elements.vizDropdownMenu;
    if (menu) {
        menu.classList.remove('show');
    }
}

function handleVisualization(vizType) {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No data available for visualization', 'info');
        return;
    }
    
    switch(vizType) {
        case 'bar':
        case 'line':
        case 'pie':
        case 'doughnut':
        case 'area':
            showVisualization(vizType);
            break;
        case 'trend':
            showTrendAnalysis();
            break;
        case 'timeline':
            showTimeline();
            break;
        case 'heatmap':
            showHeatmap();
            break;
        case 'summary':
            showSummaryReport();
            break;
        case 'stats':
            showStatistics();
            break;
        default:
            showVisualization('bar');
    }
}

// ================================================
// Chart/Visualization Functions
// ================================================

function showVisualization(chartType = 'bar') {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No data available to visualize', 'info');
        return;
    }
    
    // Hide other containers
    hideStats();
    elements.resultsWrapper.style.display = 'none';
    
    // Populate column selector
    populateColumnSelector();
    
    // Set chart type
    if (elements.chartType) {
        elements.chartType.value = chartType;
    }
    
    // Show viz container
    elements.vizContainer.style.display = 'flex';
    elements.vizTitle.textContent = chartType.toUpperCase() + ' CHART';
    
    renderChart();
}

function hideVisualization() {
    elements.vizContainer.style.display = 'none';
    if (state.currentChart) {
        state.currentChart.destroy();
        state.currentChart = null;
    }
    elements.resultsWrapper.style.display = 'block';
}

function populateColumnSelector() {
    const columns = state.lastColumns;
    if (!columns || !elements.dataColumn) return;
    
    elements.dataColumn.innerHTML = '';
    
    // Find numeric and date columns
    const data = state.lastResults;
    columns.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = col;
        elements.dataColumn.appendChild(option);
    });
    
    // Auto-select a numeric column if available
    const numericCol = findNumericColumn(data, columns);
    if (numericCol) {
        elements.dataColumn.value = numericCol;
    }
}

function findNumericColumn(data, columns) {
    for (const col of columns) {
        const values = data.slice(0, 10).map(row => row[col]);
        if (values.some(v => typeof v === 'number' || !isNaN(parseFloat(v)))) {
            return col;
        }
    }
    return columns[0];
}

function renderChart() {
    const data = state.lastResults;
    const columns = state.lastColumns;
    
    if (!data || data.length === 0 || !columns) return;
    
    // Destroy existing chart
    if (state.currentChart) {
        state.currentChart.destroy();
    }
    
    // Get selected column or find suitable one
    const selectedColumn = elements.dataColumn?.value || findNumericColumn(data, columns);
    
    // Find suitable columns for charting
    const chartData = analyzeDataForChart(data, columns, selectedColumn);
    
    if (!chartData) {
        showToast('Data not suitable for charting. Need numeric values.', 'info');
        return;
    }
    
    const ctx = elements.resultsChart.getContext('2d');
    let chartType = elements.chartType?.value || 'bar';
    
    // Convert area to line with fill
    const isArea = chartType === 'area';
    if (isArea) chartType = 'line';
    
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
            labels: chartData.labels.slice(0, 50), // Limit to 50 items
            datasets: [{
                label: chartData.valueColumn,
                data: chartData.values.slice(0, 50),
                backgroundColor: chartType === 'line' 
                    ? (isArea ? 'rgba(0, 240, 255, 0.3)' : colors[0]) 
                    : colors.slice(0, chartData.values.length),
                borderColor: chartType === 'line' ? borderColors[0] : borderColors.slice(0, chartData.values.length),
                borderWidth: 2,
                tension: 0.4,
                fill: isArea,
                pointRadius: chartType === 'line' ? 3 : undefined,
                pointHoverRadius: chartType === 'line' ? 6 : undefined
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
                    ticks: { color: '#a0a0c0', font: { family: 'Rajdhani' }, maxRotation: 45 },
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

function analyzeDataForChart(data, columns, preferredColumn = null) {
    // Find a numeric column for values
    let valueColumn = preferredColumn;
    let labelColumn = null;
    
    // Priority columns for values (numeric)
    const numericPriority = ['count', 'count_', 'sum', 'avg', 'min', 'max', 'value', 'total', 'duration', 'size', 'CounterValue', 'ResultCount'];
    
    // Verify preferred column is numeric or find one
    if (valueColumn) {
        const hasNumeric = data.some(row => typeof row[valueColumn] === 'number' || !isNaN(parseFloat(row[valueColumn])));
        if (!hasNumeric) valueColumn = null;
    }
    
    // Find value column if not set
    if (!valueColumn) {
        for (const col of columns) {
            const colLower = col.toLowerCase();
            if (numericPriority.some(p => colLower.includes(p.toLowerCase()))) {
                if (typeof data[0][col] === 'number') {
                    valueColumn = col;
                    break;
                }
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
// Statistics & Report Functions
// ================================================

function showStatistics() {
    const data = state.lastResults;
    const columns = state.lastColumns;
    
    if (!data || data.length === 0) {
        showToast('No data available', 'info');
        return;
    }
    
    // Hide other containers
    hideVisualization();
    elements.resultsWrapper.style.display = 'none';
    
    // Calculate statistics
    const stats = calculateStatistics(data, columns);
    
    // Build stats HTML
    let html = `
        <div class="stat-box">
            <i class="stat-box-icon fas fa-database"></i>
            <span class="stat-box-value">${data.length}</span>
            <span class="stat-box-label">Total Records</span>
        </div>
        <div class="stat-box">
            <i class="stat-box-icon fas fa-columns"></i>
            <span class="stat-box-value">${columns.length}</span>
            <span class="stat-box-label">Columns</span>
        </div>
    `;
    
    // Add numeric column stats
    for (const stat of stats.numericStats) {
        html += `
            <div class="stat-box">
                <i class="stat-box-icon fas fa-calculator"></i>
                <span class="stat-box-value">${stat.avg.toFixed(2)}</span>
                <span class="stat-box-label">${stat.column} (Avg)</span>
            </div>
            <div class="stat-box">
                <i class="stat-box-icon fas fa-arrow-up"></i>
                <span class="stat-box-value">${stat.max.toFixed(2)}</span>
                <span class="stat-box-label">${stat.column} (Max)</span>
            </div>
            <div class="stat-box">
                <i class="stat-box-icon fas fa-arrow-down"></i>
                <span class="stat-box-value">${stat.min.toFixed(2)}</span>
                <span class="stat-box-label">${stat.column} (Min)</span>
            </div>
        `;
    }
    
    // Add category breakdowns
    for (const cat of stats.categoryStats) {
        html += `
            <div class="summary-section">
                <h4><i class="fas fa-tags"></i> ${cat.column} Distribution</h4>
                <table class="summary-table">
                    <tr><th>Value</th><th>Count</th><th>Percentage</th></tr>
                    ${cat.values.slice(0, 10).map(v => `
                        <tr>
                            <td>${v.value}</td>
                            <td>${v.count}</td>
                            <td>${((v.count / data.length) * 100).toFixed(1)}%</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
        `;
    }
    
    elements.statsContent.innerHTML = html;
    elements.statsContainer.style.display = 'flex';
    elements.statsTitle.textContent = 'DATA STATISTICS';
}

function hideStats() {
    if (elements.statsContainer) {
        elements.statsContainer.style.display = 'none';
    }
}

function calculateStatistics(data, columns) {
    const numericStats = [];
    const categoryStats = [];
    
    for (const col of columns) {
        const values = data.map(row => row[col]).filter(v => v !== null && v !== undefined);
        
        // Check if numeric
        const numericValues = values.filter(v => typeof v === 'number' || !isNaN(parseFloat(v))).map(v => parseFloat(v));
        
        if (numericValues.length > 0 && numericValues.length === values.length) {
            numericStats.push({
                column: col,
                min: Math.min(...numericValues),
                max: Math.max(...numericValues),
                avg: numericValues.reduce((a, b) => a + b, 0) / numericValues.length,
                sum: numericValues.reduce((a, b) => a + b, 0)
            });
        } else if (values.length > 0) {
            // Category column
            const counts = {};
            values.forEach(v => {
                const key = String(v).substring(0, 50);
                counts[key] = (counts[key] || 0) + 1;
            });
            
            const uniqueValues = Object.keys(counts).length;
            if (uniqueValues <= 20 && uniqueValues > 1) {
                categoryStats.push({
                    column: col,
                    values: Object.entries(counts)
                        .map(([value, count]) => ({ value, count }))
                        .sort((a, b) => b.count - a.count)
                });
            }
        }
    }
    
    return { numericStats: numericStats.slice(0, 5), categoryStats: categoryStats.slice(0, 3) };
}

function showSummaryReport() {
    const data = state.lastResults;
    const columns = state.lastColumns;
    
    if (!data || data.length === 0) {
        showToast('No data available', 'info');
        return;
    }
    
    // Hide other containers
    hideVisualization();
    elements.resultsWrapper.style.display = 'none';
    
    const stats = calculateStatistics(data, columns);
    
    // Build summary report
    let html = `
        <div class="summary-section">
            <h4><i class="fas fa-file-alt"></i> QUERY SUMMARY REPORT</h4>
            <table class="summary-table">
                <tr><th>Metric</th><th>Value</th></tr>
                <tr><td>Total Records</td><td>${data.length}</td></tr>
                <tr><td>Total Columns</td><td>${columns.length}</td></tr>
                <tr><td>Generated At</td><td>${new Date().toLocaleString()}</td></tr>
            </table>
        </div>
    `;
    
    if (stats.numericStats.length > 0) {
        html += `
            <div class="summary-section">
                <h4><i class="fas fa-chart-bar"></i> NUMERIC ANALYSIS</h4>
                <table class="summary-table">
                    <tr><th>Column</th><th>Min</th><th>Max</th><th>Average</th><th>Sum</th></tr>
                    ${stats.numericStats.map(s => `
                        <tr>
                            <td>${s.column}</td>
                            <td>${s.min.toFixed(2)}</td>
                            <td>${s.max.toFixed(2)}</td>
                            <td>${s.avg.toFixed(2)}</td>
                            <td>${s.sum.toFixed(2)}</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
        `;
    }
    
    for (const cat of stats.categoryStats) {
        html += `
            <div class="summary-section">
                <h4><i class="fas fa-tags"></i> ${cat.column.toUpperCase()} BREAKDOWN</h4>
                <table class="summary-table">
                    <tr><th>Value</th><th>Count</th><th>Percentage</th></tr>
                    ${cat.values.slice(0, 10).map(v => `
                        <tr>
                            <td>${v.value}</td>
                            <td>${v.count}</td>
                            <td>${((v.count / data.length) * 100).toFixed(1)}%</td>
                        </tr>
                    `).join('')}
                </table>
            </div>
        `;
    }
    
    elements.statsContent.innerHTML = html;
    elements.statsContainer.style.display = 'flex';
    elements.statsTitle.textContent = 'SUMMARY REPORT';
}

function showTrendAnalysis() {
    const data = state.lastResults;
    const columns = state.lastColumns;
    
    // Find time column
    const timeCol = columns.find(c => c.toLowerCase().includes('time') || c.toLowerCase().includes('date'));
    
    if (!timeCol) {
        showToast('No timestamp column found for trend analysis', 'info');
        return;
    }
    
    // Set up for line chart
    if (elements.chartType) {
        elements.chartType.value = 'line';
    }
    
    showVisualization('line');
    elements.vizTitle.textContent = 'TREND ANALYSIS';
}

function showTimeline() {
    showVisualization('line');
    elements.vizTitle.textContent = 'TIMELINE VIEW';
}

function showHeatmap() {
    // For now, show statistics as heatmap isn't directly supported
    showStatistics();
    elements.statsTitle.textContent = 'ACTIVITY HEATMAP (Data Distribution)';
    showToast('Heatmap view shows data distribution', 'info');
}

function generatePDFReport() {
    if (!state.lastResults || state.lastResults.length === 0) {
        showToast('No data available to generate report', 'info');
        return;
    }
    
    // Create printable report
    const data = state.lastResults;
    const columns = state.lastColumns;
    const stats = calculateStatistics(data, columns);
    
    const reportWindow = window.open('', '_blank');
    reportWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Azure Log Analysis Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
                h1 { color: #0078d4; border-bottom: 2px solid #0078d4; padding-bottom: 10px; }
                h2 { color: #0078d4; margin-top: 30px; }
                table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
                th { background: #0078d4; color: white; }
                tr:nth-child(even) { background: #f9f9f9; }
                .meta { color: #666; font-size: 0.9em; }
                .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }
                .stat-card { background: #f0f8ff; padding: 15px; border-radius: 8px; text-align: center; }
                .stat-value { font-size: 24px; font-weight: bold; color: #0078d4; }
                .stat-label { color: #666; font-size: 0.85em; }
                @media print { body { margin: 20px; } }
            </style>
        </head>
        <body>
            <h1>🔍 Azure Log Analysis Report</h1>
            <p class="meta">Generated: ${new Date().toLocaleString()}</p>
            
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-value">${data.length}</div>
                    <div class="stat-label">Total Records</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${columns.length}</div>
                    <div class="stat-label">Columns</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${stats.numericStats.length}</div>
                    <div class="stat-label">Numeric Fields</div>
                </div>
            </div>
            
            ${stats.numericStats.length > 0 ? `
                <h2>📊 Numeric Analysis</h2>
                <table>
                    <tr><th>Column</th><th>Min</th><th>Max</th><th>Average</th><th>Sum</th></tr>
                    ${stats.numericStats.map(s => `
                        <tr>
                            <td>${s.column}</td>
                            <td>${s.min.toFixed(2)}</td>
                            <td>${s.max.toFixed(2)}</td>
                            <td>${s.avg.toFixed(2)}</td>
                            <td>${s.sum.toFixed(2)}</td>
                        </tr>
                    `).join('')}
                </table>
            ` : ''}
            
            ${stats.categoryStats.map(cat => `
                <h2>📋 ${cat.column} Distribution</h2>
                <table>
                    <tr><th>Value</th><th>Count</th><th>Percentage</th></tr>
                    ${cat.values.slice(0, 15).map(v => `
                        <tr>
                            <td>${v.value}</td>
                            <td>${v.count}</td>
                            <td>${((v.count / data.length) * 100).toFixed(1)}%</td>
                        </tr>
                    `).join('')}
                </table>
            `).join('')}
            
            <h2>📝 Data Preview (First 20 Records)</h2>
            <table>
                <tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr>
                ${data.slice(0, 20).map(row => `
                    <tr>${columns.map(c => `<td>${String(row[c] ?? '').substring(0, 50)}</td>`).join('')}</tr>
                `).join('')}
            </table>
            
            <script>window.print();</script>
        </body>
        </html>
    `);
    reportWindow.document.close();
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
