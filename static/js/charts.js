// Charts and Dashboard Data Loader

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    loadLeaderboardData();
});

async function loadDashboardData() {
    try {
        const data = await apiRequest('/api/student/analytics', 'GET');
        const user = data.user_details;
        
        // Update top stats cards
        document.getElementById('stat-total-attempted').innerText = user.total_attempted;
        document.getElementById('stat-total-correct').innerText = user.total_correct;
        document.getElementById('stat-overall-percentage').innerText = `${user.overall_percentage}%`;
        document.getElementById('stat-bookmarks-count').innerText = data.bookmarked_count;
        
        // Update details subtitles
        document.getElementById('stat-registered-date').innerText = `Registered: ${formatDateString(user.created_at)}`;
        document.getElementById('stat-total-wrong').innerText = `Wrong: ${user.total_wrong}`;
        document.getElementById('stat-last-login').innerText = `Last Login: ${formatDateString(user.last_login)}`;
        
        // Update main category progress bars and values
        document.getElementById('val-score-aptitude').innerText = `${user.aptitude_score}%`;
        document.getElementById('bar-score-aptitude').style.width = `${user.aptitude_score}%`;
        
        document.getElementById('val-score-reasoning').innerText = `${user.reasoning_score}%`;
        document.getElementById('bar-score-reasoning').style.width = `${user.reasoning_score}%`;
        
        document.getElementById('val-score-programming').innerText = `${user.programming_score}%`;
        document.getElementById('bar-score-programming').style.width = `${user.programming_score}%`;
        
        // Update programming language progress bars and values
        document.getElementById('val-score-python').innerText = `${user.python_score}%`;
        document.getElementById('bar-score-python').style.width = `${user.python_score}%`;
        
        document.getElementById('val-score-java').innerText = `${user.java_score}%`;
        document.getElementById('bar-score-java').style.width = `${user.java_score}%`;
        
        document.getElementById('val-score-c').innerText = `${user.c_score}%`;
        document.getElementById('bar-score-c').style.width = `${user.c_score}%`;
        
        document.getElementById('val-score-cpp').innerText = `${user.cpp_score}%`;
        document.getElementById('bar-score-cpp').style.width = `${user.cpp_score}%`;
        
        document.getElementById('val-score-javascript').innerText = `${user.javascript_score}%`;
        document.getElementById('bar-score-javascript').style.width = `${user.javascript_score}%`;
        
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
            } else {
                bookmarksBtn.disabled = true;
                bookmarksBtn.className = 'btn btn-secondary btn-sm';
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

function formatDateString(str) {
    if (!str) return 'N/A';
    try {
        const d = new Date(str.replace(' ', 'T'));
        if (isNaN(d.getTime())) return str;
        return d.toLocaleDateString(undefined, {month: 'short', day: 'numeric'}) + ' ' + d.toLocaleTimeString(undefined, {hour: '2-digit', minute:'2-digit'});
    } catch(e) {
        return str;
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
                    <i class="fas fa-info-circle fa-lg"></i> No test attempts yet. Click "Start Mock Test" to begin.
                </td>
            </tr>
        `;
        return;
    }
    
    history.forEach(row => {
        const tr = document.createElement('tr');
        const difficultyClass = row.difficulty === 'Easy' ? 'success' : (row.difficulty === 'Medium' ? 'warning' : 'danger');
        const subcatText = row.subcategory ? ` (${row.subcategory})` : '';
        
        tr.innerHTML = `
            <td>${row.test_date}</td>
            <td><span class="badge badge-info">${row.category}${subcatText}</span></td>
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
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: ['#6366f1', '#f59e0b', '#10b981'],
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
}

function renderEmptyCharts() {
    const pContainer = document.getElementById('progress-chart').parentNode;
    const rContainer = document.getElementById('radar-chart').parentNode;
    
    pContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary)">No progress data yet</div>`;
    rContainer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--text-secondary)">Take tests to build performance logs</div>`;
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
