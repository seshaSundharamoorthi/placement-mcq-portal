// Live Mock Test Engine

let questions = [];
let currentIndex = 0;
let answers = {};
let bookmarks = new Set();
let timerInterval = null;
let secondsRemaining = 0;

// URL parameters
const urlParams = new URLSearchParams(window.location.search);
const category = urlParams.get('category') || 'All';
const difficulty = urlParams.get('difficulty') || 'All';
const limit = parseInt(urlParams.get('limit')) || 10;
const timerParam = urlParams.get('timer') || 'none';
const viewMode = urlParams.get('view') || 'single';
const bookmarksOnly = urlParams.get('bookmarks') === 'true';

document.addEventListener('DOMContentLoaded', () => {
    loadTestQuestions();
});

async function loadTestQuestions() {
    let url = `/api/questions/test?limit=${limit}`;
    if (bookmarksOnly) {
        url += '&bookmarks=true';
    } else {
        if (category) url += `&category=${encodeURIComponent(category)}`;
        if (difficulty) url += `&difficulty=${encodeURIComponent(difficulty)}`;
    }

    try {
        const data = await apiRequest(url, 'GET');
        questions = data.questions;
        
        if (questions.length === 0) {
            document.getElementById('loading-spinner').innerHTML = `
                <div style="padding: 40px; text-align: center;">
                    <i class="fas fa-exclamation-circle fa-3x" style="color: var(--warning-color);"></i>
                    <h3 style="margin-top: 16px;">No Questions Found</h3>
                    <p style="color: var(--text-secondary); margin-bottom: 24px;">No questions matched your selection criteria.</p>
                    <a href="/test/setup" class="btn btn-primary">Go Back to Setup</a>
                </div>
            `;
            return;
        }

        // Initialize state
        questions.forEach(q => {
            if (q.bookmarked) {
                bookmarks.add(q.id);
            }
        });

        // Hide Spinner and Show Panels
        document.getElementById('loading-spinner').style.display = 'none';
        document.getElementById('test-content').style.display = 'block';
        document.getElementById('sidebar-wrapper').style.display = 'flex';

        // Setup Timer
        if (timerParam !== 'none') {
            const minutes = parseInt(timerParam);
            if (!isNaN(minutes)) {
                secondsRemaining = minutes * 60;
                document.getElementById('timer-wrapper').style.display = 'block';
                startTimer();
            }
        }

        // Render Sidebar Nav Grid
        renderSidebarNav();

        // Render Test
        renderTestLayout();

    } catch (err) {
        document.getElementById('loading-spinner').innerHTML = `
            <div style="padding: 40px; text-align: center; color: var(--danger-color);">
                <i class="fas fa-times-circle fa-3x"></i>
                <h3 style="margin-top: 16px;">Error Loading Questions</h3>
                <p>${err.message}</p>
                <a href="/test/setup" class="btn btn-secondary" style="margin-top: 20px;">Try Again</a>
            </div>
        `;
    }
}

function startTimer() {
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        secondsRemaining--;
        updateTimerDisplay();
        
        if (secondsRemaining <= 60) {
            document.getElementById('timer-display').classList.add('warning');
        }
        
        if (secondsRemaining <= 0) {
            clearInterval(timerInterval);
            showToast('Time is up! Submitting your answers...', 'warning');
            submitTestAnswers(true); // Auto submit
        }
    }, 1000);
}

function updateTimerDisplay() {
    const mins = Math.floor(secondsRemaining / 60);
    const secs = secondsRemaining % 60;
    const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    document.getElementById('timer-display').innerText = formatted;
}

function renderSidebarNav() {
    const navGrid = document.getElementById('question-nav-grid');
    navGrid.innerHTML = '';
    
    questions.forEach((q, idx) => {
        const btn = document.createElement('button');
        btn.className = 'nav-q-btn';
        btn.id = `nav-q-${idx}`;
        btn.innerText = idx + 1;
        
        // Navigation click
        btn.onclick = () => {
            if (viewMode === 'single') {
                jumpToQuestion(idx);
            } else {
                // Scroll to target question in grid mode
                const element = document.getElementById(`q-card-${idx}`);
                if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        };
        
        navGrid.appendChild(btn);
    });
    updateNavStatus();
}

function updateNavStatus() {
    questions.forEach((q, idx) => {
        const btn = document.getElementById(`nav-q-${idx}`);
        if (!btn) return;
        
        // Remove classes
        btn.className = 'nav-q-btn';
        
        if (viewMode === 'single' && idx === currentIndex) {
            btn.classList.add('current');
        }
        
        if (answers[q.id]) {
            btn.classList.add('answered');
        }
        
        if (bookmarks.has(q.id)) {
            btn.classList.add('bookmarked');
        }
    });
}

function renderTestLayout() {
    const wrapper = document.getElementById('question-wrapper');
    wrapper.innerHTML = '';
    
    if (viewMode === 'single') {
        document.getElementById('navigation-controls').style.display = 'flex';
        renderSingleQuestion();
    } else {
        document.getElementById('navigation-controls').style.display = 'none';
        renderGridQuestions();
    }
}

function renderSingleQuestion() {
    const wrapper = document.getElementById('question-wrapper');
    const q = questions[currentIndex];
    
    // Previous and Next button disabled states
    document.getElementById('prev-btn').disabled = (currentIndex === 0);
    document.getElementById('next-btn').innerHTML = (currentIndex === questions.length - 1) 
        ? 'Finish <i class="fas fa-flag-checkered"></i>' 
        : 'Next <i class="fas fa-arrow-right"></i>';
        
    // Update Bookmark Button state
    const bookmarkBtn = document.getElementById('bookmark-btn');
    if (bookmarks.has(q.id)) {
        bookmarkBtn.innerHTML = '<i class="fas fa-bookmark"></i> Bookmarked';
        bookmarkBtn.className = 'btn btn-primary';
        bookmarkBtn.style.background = 'var(--warning-color)';
        bookmarkBtn.style.boxShadow = 'none';
        bookmarkBtn.style.border = 'none';
    } else {
        bookmarkBtn.innerHTML = '<i class="far fa-bookmark"></i> Bookmark Question';
        bookmarkBtn.className = 'btn btn-outline';
        bookmarkBtn.style.background = 'transparent';
        bookmarkBtn.style.borderColor = 'var(--warning-color)';
        bookmarkBtn.style.color = 'var(--warning-color)';
    }

    const qPanel = document.createElement('div');
    qPanel.className = 'question-panel glass-panel animate-fade-in';
    qPanel.id = `q-card-${currentIndex}`;
    
    const difficultyClass = q.difficulty === 'Easy' ? 'success' : (q.difficulty === 'Medium' ? 'warning' : 'danger');
    
    qPanel.innerHTML = `
        <div class="question-meta">
            <span class="badge badge-info">${q.category}</span>
            <span class="badge badge-${difficultyClass}">Diff: ${q.difficulty}</span>
        </div>
        <div class="question-text">
            <span style="color: var(--accent-color); font-weight: 800;">Q${currentIndex + 1}.</span> ${escapeHTML(q.question)}
        </div>
        <div class="options-container">
            <button onclick="selectOption(${q.id}, 'A')" class="option-btn ${answers[q.id] === 'A' ? 'selected' : ''}" id="opt-${q.id}-A">
                <span class="option-letter">A</span>
                <span class="option-text">${escapeHTML(q.option_a)}</span>
            </button>
            <button onclick="selectOption(${q.id}, 'B')" class="option-btn ${answers[q.id] === 'B' ? 'selected' : ''}" id="opt-${q.id}-B">
                <span class="option-letter">B</span>
                <span class="option-text">${escapeHTML(q.option_b)}</span>
            </button>
            <button onclick="selectOption(${q.id}, 'C')" class="option-btn ${answers[q.id] === 'C' ? 'selected' : ''}" id="opt-${q.id}-C">
                <span class="option-letter">C</span>
                <span class="option-text">${escapeHTML(q.option_c)}</span>
            </button>
            <button onclick="selectOption(${q.id}, 'D')" class="option-btn ${answers[q.id] === 'D' ? 'selected' : ''}" id="opt-${q.id}-D">
                <span class="option-letter">D</span>
                <span class="option-text">${escapeHTML(q.option_d)}</span>
            </button>
        </div>
    `;
    
    wrapper.appendChild(qPanel);
    updateNavStatus();
}

function renderGridQuestions() {
    const wrapper = document.getElementById('question-wrapper');
    
    questions.forEach((q, idx) => {
        const qPanel = document.createElement('div');
        qPanel.className = 'question-panel glass-panel';
        qPanel.id = `q-card-${idx}`;
        qPanel.style.marginBottom = '32px';
        
        const difficultyClass = q.difficulty === 'Easy' ? 'success' : (q.difficulty === 'Medium' ? 'warning' : 'danger');
        
        qPanel.innerHTML = `
            <div class="question-meta">
                <div style="display: flex; gap: 8px;">
                    <span class="badge badge-info">${q.category}</span>
                    <span class="badge badge-${difficultyClass}">Diff: ${q.difficulty}</span>
                </div>
                <button onclick="toggleGridBookmark(${q.id}, ${idx})" class="btn" style="padding: 4px 10px; font-size: 0.8rem; border: 1px solid var(--warning-color); color: var(--warning-color); background: ${bookmarks.has(q.id) ? 'var(--warning-light)' : 'transparent'}">
                    <i class="${bookmarks.has(q.id) ? 'fas' : 'far'} fa-bookmark"></i>
                </button>
            </div>
            <div class="question-text">
                <span style="color: var(--accent-color); font-weight: 800;">Q${idx + 1}.</span> ${escapeHTML(q.question)}
            </div>
            <div class="options-container">
                <button onclick="selectOption(${q.id}, 'A', ${idx})" class="option-btn ${answers[q.id] === 'A' ? 'selected' : ''}" id="opt-${q.id}-A">
                    <span class="option-letter">A</span>
                    <span class="option-text">${escapeHTML(q.option_a)}</span>
                </button>
                <button onclick="selectOption(${q.id}, 'B', ${idx})" class="option-btn ${answers[q.id] === 'B' ? 'selected' : ''}" id="opt-${q.id}-B">
                    <span class="option-letter">B</span>
                    <span class="option-text">${escapeHTML(q.option_b)}</span>
                </button>
                <button onclick="selectOption(${q.id}, 'C', ${idx})" class="option-btn ${answers[q.id] === 'C' ? 'selected' : ''}" id="opt-${q.id}-C">
                    <span class="option-letter">C</span>
                    <span class="option-text">${escapeHTML(q.option_c)}</span>
                </button>
                <button onclick="selectOption(${q.id}, 'D', ${idx})" class="option-btn ${answers[q.id] === 'D' ? 'selected' : ''}" id="opt-${q.id}-D">
                    <span class="option-letter">D</span>
                    <span class="option-text">${escapeHTML(q.option_d)}</span>
                </button>
            </div>
        `;
        wrapper.appendChild(qPanel);
    });
    updateNavStatus();
}

function selectOption(questionId, option, qIndex = null) {
    answers[questionId] = option;
    
    // Update view selection
    const buttons = document.querySelectorAll(`[id^="opt-${questionId}-"]`);
    buttons.forEach(btn => btn.classList.remove('selected'));
    document.getElementById(`opt-${questionId}-${option}`).classList.add('selected');
    
    updateNavStatus();
}

function navigateQuestion(direction) {
    if (direction === 1 && currentIndex === questions.length - 1) {
        confirmSubmitTest();
        return;
    }
    
    currentIndex += direction;
    if (currentIndex < 0) currentIndex = 0;
    if (currentIndex >= questions.length) currentIndex = questions.length - 1;
    
    renderSingleQuestion();
}

function jumpToQuestion(index) {
    currentIndex = index;
    renderSingleQuestion();
}

async function toggleCurrentBookmark() {
    const q = questions[currentIndex];
    await toggleBookmarkRequest(q.id);
}

async function toggleGridBookmark(qid, idx) {
    await toggleBookmarkRequest(qid);
    renderTestLayout();
}

async function toggleBookmarkRequest(qid) {
    try {
        const data = await apiRequest('/api/bookmarks/toggle', 'POST', { question_id: qid });
        if (data.bookmarked) {
            bookmarks.add(qid);
            showToast('Question bookmarked for revision!', 'success');
        } else {
            bookmarks.delete(qid);
            showToast('Bookmark removed.', 'info');
        }
        updateNavStatus();
    } catch (err) {
        // error toast shown by apiRequest
    }
}

function confirmSubmitTest() {
    const answeredCount = Object.keys(answers).length;
    const unanswered = questions.length - answeredCount;
    
    let confirmMsg = 'Are you sure you want to submit your test?';
    if (unanswered > 0) {
        confirmMsg = `You have ${unanswered} unanswered questions. Are you sure you want to submit?`;
    }
    
    if (confirm(confirmMsg)) {
        submitTestAnswers(false);
    }
}

async function submitTestAnswers(autoSubmit = false) {
    if (timerInterval) {
        clearInterval(timerInterval);
    }
    
    // Disable buttons to prevent duplicate submission
    const submitBtn = document.querySelector('.btn-danger');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const res = await apiRequest('/api/test/submit', 'POST', {
            answers,
            category: bookmarksOnly ? 'Bookmarked Practice' : category,
            difficulty: bookmarksOnly ? 'Mix' : difficulty
        });
        
        if (res.success) {
            showToast('Assessment submitted successfully!', 'success');
            setTimeout(() => {
                window.location.href = `/test/result/${res.result_id}`;
            }, 800);
        }
    } catch (err) {
        if (submitBtn) submitBtn.disabled = false;
        // error handled by apiRequest
    }
}

function escapeHTML(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
