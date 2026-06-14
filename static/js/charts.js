// Charts and Dashboard Data Loader

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    loadLeaderboardData();
});

async function loadDashboardData() {
    try {
        const data = await apiRequest('/api/student/analytics', 'GET');
        
        // Update stats
        document.getElementById('stat-total-tests').innerText = data.total_tests;
        document.getElementById('stat-avg-score').innerText = `${data.avg_percentage}%`;
        document.getElementById('stat-strongest').innerText = data.strongest;
        document.getElementById('stat-weakest').innerText = data.weakest;
        
        // Bookmarks status
        const bookmarksDesc = document.getElementById('bookmarks-desc');
        const bookmarksBtn = document.getElementById('btn-practice-bookmarks');
        if (bookmarksDesc && bookmarksBtn) {
            bookmarksDesc.innerText = `${data.bookmarked_count} saved questions`;
            if (data.bookmarked_count > 0) {
                bookmarksBtn.disabled = false;
                bookmarksBtn.className = 'btn btn-primary btn-sm';
                bookmarksBtn.style.background = 'var(--warning-color)';
                bookmarksBtn.style.border = 'none';
            }
        }

        // Render History Table
        renderHistoryTable(data.history);
        
        if (data.total_tests > 0) {
            // Render Charts
            renderProgressChart(data.progress);
            renderRadarChart(data.category_radar);
        } else {
            renderEmptyCharts();
        }

    } catch (err) {
        console.error('Failed to load dashboard data:', err);
    }
}

function startBookmarkPractice() {
    window.location.href = '/test/take?bookmarks=true&limit=10&view=single';
}

function renderHistoryTable(history) {
    const tbody = document.getElementById('history-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (history.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 30px;">
                    <i class="fas fa-info-circle fa-lg"></i> No test attempts yet. Click "Start New Test" to begin.
                </td>
            </tr>
        `;
        return;
    }
    
    history.forEach(row => {
        const tr = document.createElement('tr');
        const difficultyClass = row.difficulty === 'Easy' ? 'success' : (row.difficulty === 'Medium' ? 'warning' : 'danger');
        
        tr.innerHTML = `
            <td>${row.test_date}</td>
            <td><span class="badge badge-info">${row.category}</span></td>
            <td><span class="badge badge-${difficultyClass}">${row.difficulty}</span></td>
            <td><strong>${row.score}/${row.total_questions}</strong></td>
            <td><strong>${row.percentage}%</strong></td>
            <td>
                <div style="display: flex; gap: 8px;">
                    <a href="/test/result/${row.id}" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.8rem;">
                        <i class="fas fa-chart-bar"></i> Details
                    </a>
                    <a href="/test/review/${row.id}" class="btn btn-outline" style="padding: 6px 12px; font-size: 0.8rem; border-color: var(--accent-color); color: var(--accent-color);">
                        <i class="fas fa-search"></i> Mistakes
                    </a>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderProgressChart(progress) {
    const ctx = document.getElementById('progress-chart').getContext('2d');
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    
    const labels = progress.map(p => p.date);
    const scores = progress.map(p => p.percentage);
    
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Test Score (%)',
                data: scores,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                borderWidth: 3,
                tension: 0.3,
                fill: true,
                pointBackgroundColor: '#4f46e5',
                pointHoverRadius: 7
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: isDark ? '#1e293b' : '#f1f5f9' },
                    ticks: { color: isDark ? '#94a3b8' : '#64748b' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: isDark ? '#94a3b8' : '#64748b' }
                }
            }
        }
    });
}

function renderRadarChart(categoryRadar) {
    const ctx = document.getElementById('radar-chart').getContext('2d');
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    
    const labels = Object.keys(categoryRadar);
    const values = Object.values(categoryRadar);
    
    if (labels.length < 3) {
        // Fallback to Bar chart if there aren't enough data points for a radar chart
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: '#10b981',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: isDark ? '#1e293b' : '#f1f5f9' },
                        ticks: { color: isDark ? '#94a3b8' : '#64748b' }
                    },
                    x: { ticks: { color: isDark ? '#94a3b8' : '#64748b' } }
                }
            }
        });
        return;
    }

    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Average Score (%)',
                data: values,
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.2)',
                borderWidth: 2,
                pointBackgroundColor: '#10b981'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: isDark ? '#1e293b' : '#f1f5f9' },
                    grid: { color: isDark ? '#1e293b' : '#f1f5f9' },
                    pointLabels: { color: isDark ? '#94a3b8' : '#64748b', font: { size: 10 } },
                    ticks: { color: isDark ? '#94a3b8' : '#64748b', backdropColor: 'transparent' },
                    min: 0,
                    max: 100
                }
            }
        }
    });
}

function renderEmptyCharts() {
    const pContainer = document.getElementById('progress-chart').parentNode;
    const rContainer = document.getElementById('radar-chart').parentNode;
    
    pContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary)">No progress data yet</div>`;
    rContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary)">Take tests in multiple categories</div>`;
}

async function loadLeaderboardData() {
    const container = document.getElementById('leaderboard-container');
    if (!container) return;
    
    try {
        const data = await apiRequest('/api/leaderboard', 'GET');
        container.innerHTML = '';
        
        if (data.leaderboard.length === 0) {
            container.innerHTML = `<div style="color: var(--text-secondary); text-align: center; padding: 20px;">No entries yet</div>`;
            return;
        }
        
        data.leaderboard.forEach((user, idx) => {
            const item = document.createElement('div');
            item.className = 'leaderboard-item glass-panel';
            
            const rankClass = idx === 0 ? 'rank-1' : (idx === 1 ? 'rank-2' : (idx === 2 ? 'rank-3' : 'rank-other'));
            const medal = idx === 0 ? '🥇' : (idx === 1 ? '🥈' : (idx === 2 ? '🥉' : ''));
            
            item.innerHTML = `
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="leader-rank ${rankClass}">${medal ? '' : idx + 1}</div>
                    <div>
                        <strong style="font-size: 0.95rem;">${escapeHTML(user.name)}</strong>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">${user.tests_taken} tests taken</div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <strong style="color: var(--accent-color); font-size: 1.1rem;">${user.avg_score}%</strong>
                    <div style="font-size: 0.7rem; color: var(--text-secondary);">College Avg</div>
                </div>
            `;
            container.appendChild(item);
        });
    } catch (err) {
        container.innerHTML = `<div style="color: var(--danger-color); font-size: 0.85rem;">Failed to load leaderboard</div>`;
    }
}

function escapeHTML(str) {
    if (!str) return '';
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
