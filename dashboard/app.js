/**
 * AI SQL Studio - Frontend Application
 * Clean modular JavaScript with async/await
 */

// ============================================
// Global State
// ============================================
const state = {
    currentDatabase: null,
    isConnected: false,
    tables: [],
    currentResults: null,
    dataTable: null,
    chart: null,
    editor: null
};

// ============================================
// API Base URL
// ============================================
const API_BASE = '/api';

// ============================================
// Initialization
// ============================================
document.addEventListener('DOMContentLoaded', async () => {
    initCodeMirror();
    initEventListeners();
    await loadDatabases();
});

// Initialize CodeMirror
function initCodeMirror() {
    state.editor = CodeMirror.fromTextArea(document.getElementById('sqlEditor'), {
        mode: 'text/x-sql',
        theme: 'dracula',
        lineNumbers: true,
        lineWrapping: true
    });
}

// Initialize event listeners
function initEventListeners() {
    // Database selector
    document.getElementById('databaseSelect').addEventListener('change', handleDatabaseChange);
    
    // Generate SQL button
    document.getElementById('generateBtn').addEventListener('click', handleGenerateSql);
    
    // Run Query button
    document.getElementById('runQueryBtn').addEventListener('click', handleRunQuery);
    
    // Copy SQL button
    document.getElementById('copySqlBtn').addEventListener('click', handleCopySql);
    
    // Export button
    document.getElementById('exportBtn').addEventListener('click', handleExportCsv);
    
    // Tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => handleTabSwitch(btn.dataset.tab));
    });
    
    // Chart controls
    document.getElementById('updateChartBtn').addEventListener('click', updateChart);
    document.getElementById('chartType').addEventListener('change', updateChart);
}

// ============================================
// API Functions
// ============================================

// Load databases from MySQL
async function loadDatabases() {
    showLoading(true, 'Loading databases...');
    
    try {
        const response = await fetch(`${API_BASE}/databases`);
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('databaseSelect');
            data.databases.forEach(db => {
                const option = document.createElement('option');
                option.value = db;
                option.textContent = db;
                select.appendChild(option);
            });
        } else {
            showToast(data.error || 'Failed to load databases', 'error');
        }
    } catch (error) {
        showToast('Backend is offline', 'error');
    } finally {
        showLoading(false);
    }
}

// Connect to database
async function handleDatabaseChange(event) {
    const dbName = event.target.value;
    
    if (!dbName) {
        updateConnectionStatus(false, null);
        return;
    }
    
    showLoading(true, `Connecting to ${dbName}...`);
    
    try {
        const response = await fetch(`${API_BASE}/connect?db=${dbName}`);
        const data = await response.json();
        
        if (data.success) {
            state.currentDatabase = dbName;
            state.isConnected = true;
            updateConnectionStatus(true, dbName);
            await loadTables(dbName);
            showToast(`Connected to ${dbName}`, 'success');
        } else {
            state.isConnected = false;
            updateConnectionStatus(false, dbName);
            showToast(data.error || 'Connection failed', 'error');
        }
    } catch (error) {
        state.isConnected = false;
        updateConnectionStatus(false, dbName);
        showToast('Connection error', 'error');
    } finally {
        showLoading(false);
    }
}

// Load tables for a database
async function loadTables(dbName) {
    try {
        const response = await fetch(`${API_BASE}/tables?db=${dbName}`);
        const data = await response.json();
        
        if (data.success) {
            state.tables = data.tables;
            renderTablesList(data.tables);
        } else {
            showToast(data.error || 'Failed to load tables', 'error');
        }
    } catch (error) {
        showToast('Failed to load tables', 'error');
    }
}

// Load table data when clicked
async function loadTableData(tableName) {
    if (!state.currentDatabase) {
        showToast('Please connect to a database first', 'error');
        return;
    }
    
    showLoading(true, `Loading ${tableName}...`);
    
    try {
        const response = await fetch(`${API_BASE}/table-data?db=${state.currentDatabase}&name=${tableName}&limit=100`);
        const data = await response.json();
        
        if (data.success) {
            state.currentResults = data.data;
            displayResults(data.data, data.columns);
            document.getElementById('resultsSection').classList.remove('hidden');
            showToast(`Loaded ${data.count} rows from ${tableName}`, 'success');
        } else {
            showToast(data.error || 'Failed to load table data', 'error');
        }
    } catch (error) {
        showToast('Failed to load table data', 'error');
    } finally {
        showLoading(false);
    }
}

// Generate SQL from natural language
async function handleGenerateSql() {
    const query = document.getElementById('queryInput').value.trim();
    
    if (!query) {
        showToast('Please enter a query', 'error');
        return;
    }
    
    if (!state.isConnected) {
        showToast('Please connect to a database first', 'error');
        return;
    }
    
    showLoading(true, 'Generating SQL...');
    
    try {
        const response = await fetch(`${API_BASE}/generate-sql`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: query,
                database: state.currentDatabase
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            state.editor.setValue(data.sql);
            document.getElementById('sqlSection').classList.remove('hidden');
            document.getElementById('runQueryBtn').disabled = false;
            showToast('SQL generated successfully', 'success');
        } else {
            showToast(data.error || 'Failed to generate SQL', 'error');
        }
    } catch (error) {
        showToast('Failed to generate SQL', 'error');
    } finally {
        showLoading(false);
    }
}

// Run SQL query
async function handleRunQuery() {
    const sql = state.editor.getValue().trim();
    
    if (!sql) {
        showToast('No SQL to execute', 'error');
        return;
    }
    
    if (!state.isConnected) {
        showToast('Please connect to a database first', 'error');
        return;
    }
    
    showLoading(true, 'Executing query...');
    
    try {
        const response = await fetch(`${API_BASE}/run-query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                sql: sql,
                database: state.currentDatabase
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            state.currentResults = data.results;
            displayResults(data.results, data.columns);
            document.getElementById('resultsSection').classList.remove('hidden');
            showToast(`Query executed! ${data.row_count} rows returned.`, 'success');
        } else {
            showToast(data.error || 'Query execution failed', 'error');
        }
    } catch (error) {
        showToast('Query execution failed', 'error');
    } finally {
        showLoading(false);
    }
}

// ============================================
// UI Helper Functions
// ============================================

// Update connection status indicator
function updateConnectionStatus(connected, dbName) {
    const statusEl = document.getElementById('connectionStatus');
    const dotEl = document.getElementById('statusDot');
    const textEl = document.getElementById('statusText');
    
    if (connected) {
        statusEl.classList.remove('status-disconnected');
        statusEl.classList.add('status-connected');
        dotEl.classList.remove('bg-red-500');
        dotEl.classList.add('bg-green-500');
        textEl.textContent = dbName;
        textEl.classList.remove('text-red-400');
        textEl.classList.add('text-green-400');
    } else {
        statusEl.classList.remove('status-connected');
        statusEl.classList.add('status-disconnected');
        dotEl.classList.remove('bg-green-500');
        dotEl.classList.add('bg-red-500');
        textEl.textContent = 'Disconnected';
        textEl.classList.remove('text-green-400');
        textEl.classList.add('text-red-400');
    }
}

// Render tables list in sidebar
function renderTablesList(tables) {
    const container = document.getElementById('tablesList');
    
    if (!tables || tables.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500 text-sm py-4">No tables found</div>';
        return;
    }
    
    container.innerHTML = tables.map(table => `
        <div class="sidebar-item p-3 rounded-lg" onclick="loadTableData('${table}')">
            <div class="flex items-center gap-3">
                <i class="fas fa-table text-indigo-400"></i>
                <span class="text-sm">${table}</span>
            </div>
        </div>
    `).join('');
}

// Display results using DataTables.js
function displayResults(results, columns) {
    if (!results || results.length === 0) {
        showToast('No results found', 'info');
        return;
    }

    // Fall back to keys from the first row if backend didn't send columns
    if (!columns || columns.length === 0) {
        columns = Object.keys(results[0]);
    }
    
    // Destroy existing DataTable
    if ($.fn.DataTable.isDataTable('#dataTable')) {
        $('#dataTable').DataTable().clear().destroy();
    }

    // Clear any previous thead/tbody to avoid "Incorrect column count" on re-init
    $('#dataTable').empty();

    // Ensure header column count matches the configured columns
    const headerHtml = `<thead><tr>${columns.map(col => `<th>${formatColumnName(col)}</th>`).join('')}</tr></thead>`;
    $('#dataTable').append(headerHtml);
    
    // Build DataTable
    state.dataTable = $('#dataTable').DataTable({
        data: results,
        columns: columns.map(col => ({ 
            data: col,
            render: (data) => data === null ? '<span class="text-gray-500">NULL</span>' : data
        })),
        responsive: true,
        pageLength: 25,
        lengthMenu: [10, 25, 50, 100],
        order: [[0, 'asc']],
        dom: '<"flex justify-between items-center mb-4"l<"flex gap-2"f>>t<"flex justify-between items-center mt-4"ip>'
    });
    
    // Update row count
    document.getElementById('rowCount').textContent = `(${results.length} rows)`;
    
    // Display JSON
    document.getElementById('jsonOutput').textContent = JSON.stringify(results, null, 2);
    
    // Setup chart axis selectors
    setupChartSelectors(columns, results);
    
    // Auto-generate chart
    generateChart();
}

// Setup chart axis dropdowns
function setupChartSelectors(columns, results) {
    const xSelect = document.getElementById('xAxisSelect');
    const ySelect = document.getElementById('yAxisSelect');
    
    xSelect.innerHTML = '';
    ySelect.innerHTML = '';
    
    // Find numeric and categorical columns
    const numericCols = columns.filter(col => typeof results[0][col] === 'number');
    const categoricalCols = columns.filter(col => typeof results[0][col] === 'string');
    
    // Add categorical columns to X axis
    categoricalCols.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = formatColumnName(col);
        xSelect.appendChild(option);
    });
    
    // Add numeric columns to Y axis
    numericCols.forEach(col => {
        const option = document.createElement('option');
        option.value = col;
        option.textContent = formatColumnName(col);
        ySelect.appendChild(option);
    });
    
    // If no numeric columns, add count option
    if (numericCols.length === 0) {
        const option = document.createElement('option');
        option.value = 'count';
        option.textContent = 'Row Count';
        ySelect.appendChild(option);
    }
}

// Generate chart based on selected columns
function generateChart() {
    if (!state.currentResults || state.currentResults.length === 0) return;
    
    const chartType = document.getElementById('chartType').value;
    const xCol = document.getElementById('xAxisSelect').value;
    const yCol = document.getElementById('yAxisSelect').value;
    
    if (!xCol || !yCol) return;
    
    const ctx = document.getElementById('resultChart').getContext('2d');
    
    // Destroy existing chart
    if (state.chart) {
        state.chart.destroy();
    }
    
    // Prepare data
    const labels = state.currentResults.slice(0, 15).map(r => r[xCol]);
    let data;
    
    if (yCol === 'count') {
        // Count occurrences
        const counts = {};
        state.currentResults.forEach(r => {
            const key = r[xCol];
            counts[key] = (counts[key] || 0) + 1;
        });
        data = Object.values(counts).slice(0, 15);
    } else {
        data = state.currentResults.slice(0, 15).map(r => r[yCol]);
    }
    
    // Create chart
    state.chart = new Chart(ctx, {
        type: chartType,
        data: {
            labels: labels,
            datasets: [{
                label: yCol === 'count' ? 'Count' : formatColumnName(yCol),
                data: data,
                backgroundColor: getChartColors(chartType, data.length),
                borderColor: 'rgba(99, 102, 241, 1)',
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
                    labels: { color: '#a1a1aa' }
                }
            },
            scales: {
                x: {
                    ticks: { color: '#a1a1aa' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                },
                y: {
                    ticks: { color: '#a1a1aa' },
                    grid: { color: 'rgba(255, 255, 255, 0.1)' }
                }
            }
        }
    });
}

// Update chart when button clicked
function updateChart() {
    generateChart();
}

// Get chart colors
function getChartColors(type, count) {
    const baseColors = [
        'rgba(99, 102, 241, 0.6)',
        'rgba(139, 92, 246, 0.6)',
        'rgba(168, 85, 247, 0.6)',
        'rgba(192, 132, 252, 0.6)',
        'rgba(232, 121, 249, 0.6)',
        'rgba(249, 168, 212, 0.6)',
        'rgba(244, 114, 182, 0.6)',
        'rgba(236, 72, 153, 0.6)',
        'rgba(217, 70, 239, 0.6)',
        'rgba(190, 24, 93, 0.6)'
    ];
    
    if (type === 'pie' || type === 'doughnut') {
        return baseColors.slice(0, count);
    }
    return baseColors[0];
}

// Format column name
function formatColumnName(col) {
    return col.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Handle tab switching
function handleTabSwitch(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
        btn.classList.toggle('bg-white/5', btn.dataset.tab !== tabName);
    });
    
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.getElementById(`${tabName}View`).classList.remove('hidden');
}

// Copy SQL to clipboard
function handleCopySql() {
    const sql = state.editor.getValue();
    navigator.clipboard.writeText(sql);
    showToast('SQL copied to clipboard!', 'success');
}

// Export to CSV
function handleExportCsv() {
    if (!state.currentResults || state.currentResults.length === 0) {
        showToast('No data to export', 'error');
        return;
    }
    
    const columns = Object.keys(state.currentResults[0]);
    const csvContent = [
        columns.join(','),
        ...state.currentResults.map(row => 
            columns.map(col => {
                const val = row[col];
                return typeof val === 'string' ? `"${val}"` : val;
            }).join(',')
        )
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `query_results_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    
    showToast('CSV exported!', 'success');
}

// Show/hide loading
function showLoading(show, message = 'Please wait') {
    document.getElementById('loadingSection').classList.toggle('hidden', !show);
    document.getElementById('loadingMessage').textContent = message;
    
    const generateBtn = document.getElementById('generateBtn');
    const runBtn = document.getElementById('runQueryBtn');
    
    generateBtn.disabled = show;
    runBtn.disabled = show || !state.editor?.getValue();
}

// Show toast notification
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    
    const colors = {
        success: 'bg-green-500/20 border-green-500/50 text-green-400',
        error: 'bg-red-500/20 border-red-500/50 text-red-400',
        info: 'bg-blue-500/20 border-blue-500/50 text-blue-400'
    };
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    toast.className = `toast glass-card px-4 py-3 flex items-center gap-3 ${colors[type]} border`;
    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" class="ml-4 hover:opacity-70">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.remove(), 5000);
}

// Make functions globally available for inline onclick
window.loadTableData = loadTableData;
