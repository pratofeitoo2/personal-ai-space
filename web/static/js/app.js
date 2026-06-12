// personal-ai-space/web/static/js/app.js
// Main application logic

let currentPanel = 'dashboard';

function showPanel(name) {
    document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    const panel = document.getElementById(`panel-${name}`);
    if (panel) {
        panel.classList.remove('hidden');
        currentPanel = name;
    }

    const btn = document.querySelector(`[data-panel="${name}"]`);
    if (btn) btn.classList.add('active');

    loadPanelData(name);
}

async function loadPanelData(name) {
    switch (name) {
        case 'dashboard': await loadDashboard(); break;
        case 'tasks': await loadTasks(); break;
        case 'habits': await loadHabits(); break;
        case 'calendar': await loadCalendar(); break;
        case 'jobs': await loadJobs(); break;
        case 'chat': initChat(); break;
        case 'automations': await loadAutomations(); break;
    }
}

async function checkDaemonStatus() {
    const el = document.getElementById('daemon-status');
    try {
        const resp = await fetch('/api/engine/health');
        const data = await resp.json();
        if (data.ok) {
            el.textContent = 'Daemon';
            el.className = 'text-xs text-green-500';
        } else {
            el.textContent = 'Offline';
            el.className = 'text-xs text-red-500';
        }
    } catch {
        el.textContent = 'Offline';
        el.className = 'text-xs text-red-500';
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.getElementById('theme-icon').textContent = isDark ? '\u2600' : '\u263E';
}

document.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.documentElement.classList.add('dark');
        document.getElementById('theme-icon').textContent = '\u2600';
    }
    checkDaemonStatus();
    setInterval(checkDaemonStatus, 30000);
    loadPanelData('dashboard');
});
