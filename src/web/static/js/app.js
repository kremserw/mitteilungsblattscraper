/**
 * JKU MTB Analyzer - Frontend JavaScript
 */

// ===== Status Polling =====

let statusPollInterval = null;

function updateStatus() {
    fetch('/api/tasks/status')
        .then(r => r.json())
        .then(data => {
            const statusDot = document.querySelector('.status-dot');
            const statusText = document.querySelector('.status-text');
            const logContent = document.querySelector('.log-content');
            const progressFill = document.querySelector('.progress-fill');
            
            // Update buttons
            document.querySelectorAll('.btn:not(.no-disable)').forEach(btn => {
                btn.disabled = data.running;
            });
            
            // Update status indicator
            if (statusDot) {
                statusDot.classList.remove('running', 'success', 'error');
                if (data.running) {
                    statusDot.classList.add('running');
                } else if (data.error) {
                    statusDot.classList.add('error');
                } else if (data.logs.length > 0) {
                    statusDot.classList.add('success');
                }
            }
            
            // Update status text
            if (statusText) {
                if (data.running) {
                    statusText.textContent = data.task || 'Running...';
                } else if (data.error) {
                    statusText.textContent = 'Error';
                } else {
                    statusText.textContent = 'Idle';
                }
            }
            
            // Update logs
            if (logContent) {
                const wasAtBottom = logContent.scrollHeight - logContent.scrollTop <= logContent.clientHeight + 10;
                
                logContent.innerHTML = data.logs.map(log => {
                    let cls = 'log-line';
                    if (log.includes('ERROR') || log.includes('✗')) cls += ' error';
                    else if (log.includes('✓') || log.includes('complete') || log.includes('✅')) cls += ' success';
                    else if (log.includes('📡') || log.includes('📥') || log.includes('🤖')) cls += ' info';
                    return `<div class="${cls}">${escapeHtml(log)}</div>`;
                }).join('');
                
                if (wasAtBottom) {
                    logContent.scrollTop = logContent.scrollHeight;
                }
            }
            
            // Update progress bar
            if (progressFill && data.total > 0) {
                const pct = Math.round((data.progress / data.total) * 100);
                progressFill.style.width = pct + '%';
            }
            
            // Update sync phases if present
            const syncPhases = document.getElementById('sync-phases');
            if (syncPhases && data.task) {
                syncPhases.style.display = 'flex';
                const task = data.task.toLowerCase();
                
                ['scan', 'scrape', 'analyze'].forEach(phase => {
                    const el = document.getElementById('phase-' + phase);
                    if (el) {
                        el.classList.remove('active', 'done');
                        if (task.includes(phase)) {
                            el.classList.add('active');
                        } else if (
                            (phase === 'scan' && (task.includes('scrape') || task.includes('analyze'))) ||
                            (phase === 'scrape' && task.includes('analyze'))
                        ) {
                            el.classList.add('done');
                        }
                    }
                });
            }
            
            // Stop polling when task completes
            if (!data.running && statusPollInterval) {
                clearInterval(statusPollInterval);
                statusPollInterval = null;
            }
        })
        .catch(err => console.error('Status update failed:', err));
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== Task Actions =====

function startTask(task, edition) {
    let url = '/api/tasks/' + task;
    
    if (edition) {
        url += '?edition=' + encodeURIComponent(edition);
    } else {
        // Add date filters if present
        const dateFrom = document.getElementById('date-from');
        const dateTo = document.getElementById('date-to');
        const params = new URLSearchParams();
        
        if (dateFrom && dateFrom.value) {
            params.append('date_from', dateFrom.value);
        }
        if (dateTo && dateTo.value) {
            params.append('date_to', dateTo.value);
        }
        if (params.toString()) {
            url += '?' + params.toString();
        }
    }
    
    fetch(url, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.started) {
                // Start polling for status
                if (!statusPollInterval) {
                    statusPollInterval = setInterval(updateStatus, 1000);
                }
                updateStatus();
            } else {
                alert(data.error || 'Failed to start task');
            }
        })
        .catch(err => {
            alert('Error: ' + err.message);
        });
}

function syncAll() {
    fetch('/api/tasks/sync', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.started) {
                if (!statusPollInterval) {
                    statusPollInterval = setInterval(updateStatus, 1000);
                }
                updateStatus();
            } else {
                alert(data.error || 'Failed to start sync');
            }
        })
        .catch(err => {
            alert('Error: ' + err.message);
        });
}

function resetEdition(editionId) {
    fetch('/api/editions/' + editionId + '/reset', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.reset) {
                location.reload();
            } else {
                alert(data.error || 'Failed to reset edition');
            }
        })
        .catch(err => {
            alert('Error: ' + err.message);
        });
}

// ===== Role Description =====

function saveRoleDescription() {
    const textarea = document.getElementById('role-description');
    const indicator = document.getElementById('save-indicator');
    
    if (!textarea) return;
    
    fetch('/api/settings/role', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role_description: textarea.value })
    })
        .then(r => r.json())
        .then(data => {
            if (data.saved && indicator) {
                indicator.classList.add('visible');
                setTimeout(() => indicator.classList.remove('visible'), 2000);
            } else if (data.error) {
                alert('Failed to save: ' + data.error);
            }
        })
        .catch(err => {
            alert('Error saving: ' + err.message);
        });
}

// ===== Item Actions =====

function markItemRead(itemId) {
    fetch('/api/items/' + itemId + '/read', { method: 'POST' })
        .catch(() => {}); // Ignore errors
}

function analyzePdf(itemId) {
    const btn = event.target;
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = 'Analyzing...';
    
    fetch('/api/items/' + itemId + '/analyze-pdf', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Update the PDF analysis section
                const analysisDiv = document.getElementById('pdf-analysis');
                if (analysisDiv) {
                    // Clean up the analysis text - remove markdown symbols
                    let text = data.analysis || '';
                    // Remove markdown headers
                    text = text.replace(/^#{1,3}\s+/gm, '');
                    // Convert markdown bold to plain text
                    text = text.replace(/\*\*(.+?)\*\*/g, '$1');
                    // Convert markdown bullets to actual bullets
                    text = text.replace(/^[\-\*]\s+/gm, '• ');
                    
                    analysisDiv.innerHTML = '<div class="pdf-analysis" style="white-space: pre-wrap; line-height: 1.6;">' + 
                        escapeHtml(text) + 
                        '</div>';
                }
                btn.textContent = '✓ Analyzed';
            } else {
                alert(data.error || 'Analysis failed');
                btn.textContent = originalText;
                btn.disabled = false;
            }
        })
        .catch(err => {
            alert('Error: ' + err.message);
            btn.textContent = originalText;
            btn.disabled = false;
        });
}

// ===== Server Shutdown =====

function shutdownServer() {
    if (!confirm('Shutdown the server? You will need to restart manually.')) {
        return;
    }
    
    fetch('/api/settings/shutdown', { method: 'POST' })
        .then(() => {
            document.body.innerHTML = '<div class="splash-container">' +
                '<div class="splash-logo">🛑</div>' +
                '<h1>Server Stopped</h1>' +
                '<p class="splash-text">You can close this browser tab.</p>' +
                '</div>';
        })
        .catch(() => {
            document.body.innerHTML = '<div class="splash-container">' +
                '<div class="splash-logo">🛑</div>' +
                '<h1>Server Stopped</h1>' +
                '<p class="splash-text">You can close this browser tab.</p>' +
                '</div>';
        });
}

// ===== Table Sorting =====

function makeSortable(table) {
    const headers = table.querySelectorAll('th');
    
    headers.forEach((th, colIdx) => {
        if (th.textContent.trim()) {
            th.classList.add('sortable');
            th.addEventListener('click', () => sortTable(table, colIdx, th));
        }
    });
}

function sortTable(table, colIdx, th) {
    const tbody = table.querySelector('tbody') || table;
    const rows = Array.from(tbody.querySelectorAll('tr')).filter(r => r.querySelectorAll('td').length > 0);
    
    // Determine sort direction
    const isAsc = th.classList.contains('asc');
    
    // Remove sort classes from all headers
    table.querySelectorAll('th').forEach(h => h.classList.remove('asc', 'desc'));
    
    // Add appropriate class
    th.classList.add(isAsc ? 'desc' : 'asc');
    
    // Sort rows
    rows.sort((a, b) => {
        const aVal = a.querySelectorAll('td')[colIdx]?.textContent.trim() || '';
        const bVal = b.querySelectorAll('td')[colIdx]?.textContent.trim() || '';
        
        // Check for edition ID format (YYYY-N)
        const editionMatch = /^(\d{4})-(\d+)$/;
        const aEdition = aVal.match(editionMatch);
        const bEdition = bVal.match(editionMatch);
        
        if (aEdition && bEdition) {
            // Sort by year first, then by stueck number
            const aYear = parseInt(aEdition[1]);
            const bYear = parseInt(bEdition[1]);
            const aStueck = parseInt(aEdition[2]);
            const bStueck = parseInt(bEdition[2]);
            
            if (aYear !== bYear) {
                return isAsc ? bYear - aYear : aYear - bYear;
            }
            return isAsc ? bStueck - aStueck : aStueck - bStueck;
        }
        
        // Try numeric comparison (for scores, punkt numbers, etc.)
        const aNum = parseFloat(aVal.replace('%', ''));
        const bNum = parseFloat(bVal.replace('%', ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAsc ? bNum - aNum : aNum - bNum;
        }
        
        // String comparison for text columns
        return isAsc 
            ? bVal.localeCompare(aVal)
            : aVal.localeCompare(bVal);
    });
    
    // Reorder rows
    rows.forEach(row => tbody.appendChild(row));
}

// ===== Initialization =====

document.addEventListener('DOMContentLoaded', () => {
    // Initialize sortable tables
    document.querySelectorAll('table').forEach(makeSortable);
    
    // Start status polling if a task might be running
    updateStatus();
});
