// personal-ai-space/web/static/js/dashboard.js
// Dashboard and panel data loaders

async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
}

async function loadDashboard() {
    const el = document.getElementById('dashboard-content');
    try {
        const [tasks, habits, calendar, jobs] = await Promise.all([
            fetchJSON('/api/tasks/summary'),
            fetchJSON('/api/habits/streaks'),
            fetchJSON('/api/calendar/today'),
            fetchJSON('/api/jobs/pipeline'),
        ]);

        const totalTasks = tasks.reduce((s, p) => s + p.total, 0);
        const completedTasks = tasks.reduce((s, p) => s + p.completed, 0);
        const activeHabits = habits.length;
        const avgStreak = habits.length ? (habits.reduce((s, h) => s + h.current_streak, 0) / habits.length).toFixed(1) : 0;
        const todayEvents = calendar.length;
        const totalApps = jobs.reduce((s, j) => s + j.count, 0);

        el.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Tasks</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${completedTasks}/${totalTasks}</p>
                    <p class="text-xs text-gray-400">completed</p>
                </div>
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Habits</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${activeHabits}</p>
                    <p class="text-xs text-gray-400">avg streak: ${avgStreak} days</p>
                </div>
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Calendar</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${todayEvents}</p>
                    <p class="text-xs text-gray-400">events today</p>
                </div>
                <div class="card p-6">
                    <h3 class="text-sm font-medium text-gray-500 dark:text-gray-400">Job Applications</h3>
                    <p class="text-3xl font-bold text-gray-900 dark:text-white">${totalApps}</p>
                    <p class="text-xs text-gray-400">total applications</p>
                </div>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="card p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Habit Streaks</h3>
                    <canvas id="streaksChart" height="200"></canvas>
                </div>
                <div class="card p-6">
                    <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Job Pipeline</h3>
                    <canvas id="pipelineChart" height="200"></canvas>
                </div>
            </div>
        `;

        if (habits.length) {
            new Chart(document.getElementById('streaksChart'), {
                type: 'bar',
                data: {
                    labels: habits.map(h => h.habit_name),
                    datasets: [{ label: 'Streak (days)', data: habits.map(h => h.current_streak), backgroundColor: '#3b82f6' }]
                },
                options: { responsive: true, plugins: { legend: { display: false } } }
            });
        }
        if (jobs.length) {
            new Chart(document.getElementById('pipelineChart'), {
                type: 'doughnut',
                data: {
                    labels: jobs.map(j => j.status),
                    datasets: [{ data: jobs.map(j => j.count), backgroundColor: ['#94a3b8', '#3b82f6', '#f59e0b', '#10b981', '#ef4444'] }]
                },
                options: { responsive: true }
            });
        }
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error loading dashboard: ${e.message}</div>`;
    }
}

async function loadTasks() {
    const el = document.getElementById('tasks-content');
    try {
        const tasks = await fetchJSON('/api/tasks/?due=active&limit=50');
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Tasks</h2>
            <div class="space-y-3">
                ${tasks.map(t => `
                    <div class="card p-4 flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <span class="priority-badge priority-${t.priority}">${t.priority}</span>
                            <span class="text-gray-900 dark:text-white">${t.title}</span>
                            <span class="text-xs text-gray-400">${t.project_name || ''}</span>
                        </div>
                        <div class="flex items-center space-x-3">
                            <span class="text-xs text-gray-500">${t.due_date || 'No due date'}</span>
                            <button onclick="completeTask('${t.id}')" class="text-green-500 hover:text-green-700">&#10003;</button>
                        </div>
                    </div>
                `).join('')}
                ${tasks.length === 0 ? '<p class="text-gray-500 dark:text-gray-400">No pending tasks</p>' : ''}
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

async function completeTask(taskId) {
    await fetch(`/api/tasks/${taskId}/complete`, { method: 'POST' });
    loadTasks();
}

async function loadHabits() {
    const el = document.getElementById('habits-content');
    try {
        const [habits, atRisk] = await Promise.all([
            fetchJSON('/api/habits/today'),
            fetchJSON('/api/habits/at-risk'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Habits</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4">Today</h3>
                    <div class="space-y-3">
                        ${habits.map(h => `
                            <div class="flex items-center justify-between p-3 rounded-lg ${h.today_status === 'completed' ? 'bg-green-50 dark:bg-green-900/20' : 'bg-gray-50 dark:bg-slate-700'}">
                                <div>
                                    <span class="font-medium text-gray-900 dark:text-white">${h.habit_name}</span>
                                    <span class="text-xs text-gray-400 ml-2">streak: ${h.current_streak}</span>
                                </div>
                                ${h.today_status === 'completed'
                                    ? '<span class="text-green-500">Done</span>'
                                    : `<button onclick="completeHabit('${h.id}')" class="text-gray-400 hover:text-green-500">&#x25CB;</button>`
                                }
                            </div>
                        `).join('')}
                    </div>
                </div>
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4 text-yellow-600">At Risk</h3>
                    <div class="space-y-3">
                        ${atRisk.map(h => `
                            <div class="p-3 rounded-lg bg-yellow-50 dark:bg-yellow-900/20">
                                <span class="font-medium text-yellow-800 dark:text-yellow-200">${h.habit_name}</span>
                                <span class="text-xs text-yellow-600 ml-2">streak: ${h.current_streak}</span>
                                <span class="text-xs text-yellow-500 ml-2">last: ${h.last_completed || 'never'}</span>
                            </div>
                        `).join('')}
                        ${atRisk.length === 0 ? '<p class="text-green-500">All habits on track!</p>' : ''}
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

async function completeHabit(habitId) {
    await fetch(`/api/habits/${habitId}/complete`, { method: 'POST' });
    loadHabits();
}

async function loadCalendar() {
    const el = document.getElementById('calendar-content');
    try {
        const [today, week] = await Promise.all([
            fetchJSON('/api/calendar/today'),
            fetchJSON('/api/calendar/week'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Calendar</h2>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4">Today</h3>
                    <div class="space-y-3">
                        ${today.map(e => `
                            <div class="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                                <span class="font-medium text-blue-800 dark:text-blue-200">${e.event_name}</span>
                                <span class="text-xs text-blue-600 ml-2">${e.event_time} (${e.duration_hours}h)</span>
                            </div>
                        `).join('')}
                        ${today.length === 0 ? '<p class="text-gray-500">No events today</p>' : ''}
                    </div>
                </div>
                <div class="card p-6">
                    <h3 class="text-lg font-medium mb-4">This Week</h3>
                    <div class="space-y-3">
                        ${week.map(e => `
                            <div class="p-3 rounded-lg bg-gray-50 dark:bg-slate-700">
                                <span class="font-medium text-gray-900 dark:text-white">${e.event_name}</span>
                                <span class="text-xs text-gray-500 ml-2">${e.event_date} ${e.event_time}</span>
                            </div>
                        `).join('')}
                        ${week.length === 0 ? '<p class="text-gray-500">No upcoming events</p>' : ''}
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

async function loadJobs() {
    const el = document.getElementById('jobs-content');
    try {
        const [apps, pipeline] = await Promise.all([
            fetchJSON('/api/jobs/?limit=20'),
            fetchJSON('/api/jobs/pipeline'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Job Applications</h2>
            <div class="card p-6 mb-6">
                <h3 class="text-lg font-medium mb-4">Pipeline</h3>
                <div class="flex flex-wrap gap-4">
                    ${pipeline.map(p => `
                        <div class="text-center">
                            <div class="text-2xl font-bold text-gray-900 dark:text-white">${p.count}</div>
                            <div class="text-xs text-gray-500">${p.status}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="card p-6">
                <h3 class="text-lg font-medium mb-4">Recent Applications</h3>
                <div class="space-y-3">
                    ${apps.map(a => `
                        <div class="p-3 rounded-lg bg-gray-50 dark:bg-slate-700">
                            <div class="font-medium text-gray-900 dark:text-white">${a.job_title}</div>
                            <div class="text-sm text-gray-500">${a.company_name || 'Unknown'} · ${a.status} · ${a.location || 'N/A'}</div>
                        </div>
                    `).join('')}
                    ${apps.length === 0 ? '<p class="text-gray-500">No applications yet</p>' : ''}
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

async function loadAutomations() {
    const el = document.getElementById('automations-content');
    try {
        const [status, state] = await Promise.all([
            fetchJSON('/api/automations/status'),
            fetchJSON('/api/automations/state'),
        ]);
        el.innerHTML = `
            <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Automations</h2>
            <div class="card p-6">
                <h3 class="text-lg font-medium mb-4">Last Runs</h3>
                <div class="space-y-3">
                    ${Object.entries(state.last_runs || {}).map(([rule, time]) => `
                        <div class="flex justify-between p-3 rounded-lg bg-gray-50 dark:bg-slate-700">
                            <span class="font-medium text-gray-900 dark:text-white">${rule}</span>
                            <span class="text-xs text-gray-500">${time}</span>
                        </div>
                    `).join('')}
                    ${Object.keys(state.last_runs || {}).length === 0 ? '<p class="text-gray-500">No runs recorded</p>' : ''}
                </div>
            </div>
        `;
    } catch (e) {
        el.innerHTML = `<div class="text-red-500">Error: ${e.message}</div>`;
    }
}

let chatInitialized = false;
function initChat() {
    if (chatInitialized) return;
    chatInitialized = true;
    const el = document.getElementById('chat-content');
    el.innerHTML = `
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Chat</h2>
        <div class="card p-6">
            <div id="chat-messages" class="space-y-4 mb-4 h-96 overflow-y-auto"></div>
            <div class="flex space-x-2">
                <input id="chat-input" type="text" placeholder="Ask me anything..."
                    class="flex-1 p-3 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-gray-900 dark:text-white"
                    onkeypress="if(event.key==='Enter')sendChat()">
                <button onclick="sendChat()" class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Send</button>
            </div>
        </div>
    `;
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';

    const messages = document.getElementById('chat-messages');
    messages.innerHTML += `<div class="text-right"><span class="inline-block p-3 rounded-lg bg-blue-100 dark:bg-blue-900 text-gray-900 dark:text-white">${msg}</span></div>`;

    try {
        const resp = await fetch('/api/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg }),
        });
        const data = await resp.json();
        messages.innerHTML += `<div><span class="inline-block p-3 rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-900 dark:text-white">${data.message || data.error || 'No response'}</span></div>`;
    } catch (e) {
        messages.innerHTML += `<div><span class="inline-block p-3 rounded-lg bg-red-100 text-red-700">Error: ${e.message}</span></div>`;
    }
    messages.scrollTop = messages.scrollHeight;
}
