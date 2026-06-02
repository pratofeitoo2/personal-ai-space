import { createServer } from 'node:http';
import { Database } from 'better-sqlite3';
import { URL } from 'node:url';

// Initialize database connection
const db = new Database('/Users/paulorezende/Documents/Personal_AI_powerhouse updated/personal-ai-space/engine/db/self/self.db');

// Dashboard server port
const PORT = 8080;

// Helper function to send JSON response
function sendJson(res: any, status: number, data: any) {
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(data));
}

// Helper function to send HTML response
function sendHtml(res: any, status: number, html: string) {
  res.writeHead(status, { 'Content-Type': 'text/html' });
  res.end(html);
}

// Main dashboard HTML template
function getDashboardHtml() {
  return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal AI Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .chart-container {
            position: relative;
            height: 300px;
            width: 100%;
        }
        .skeleton {
            background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
            border-radius: 0.5rem;
        }
        @keyframes loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">Personal AI Dashboard</h1>
            <p class="mt-2 text-gray-600">Real-time insights from your personal AI system</p>
        </header>

        <!-- Stats Cards -->
        <div class="grid gap-6 mb-8 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
            <!-- Profile Stats -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Profile</h3>
                <div id="profile-stats" class="space-y-2">
                    <div class="skeleton h-4 w-32"></div>
                    <div class="skeleton h-4 w-24"></div>
                    <div class="skeleton h-4 w-28"></div>
                </div>
            </div>

            <!-- Habits Stats -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Habits</h3>
                <div id="habits-stats" class="space-y-2">
                    <div class="skeleton h-4 w-40"></div>
                    <div class="skeleton h-4 w-32"></div>
                    <div class="skeleton h-4 w-36"></div>
                </div>
            </div>

            <!-- Traits Stats -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Traits</h3>
                <div id="traits-stats" class="space-y-2">
                    <div class="skeleton h-4 w-40"></div>
                    <div class="skeleton h-4 w-36"></div>
                    <div class="skeleton h-4 w-32"></div>
                </div>
            </div>

            <!-- Goals Stats -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Goals</h3>
                <div id="goals-stats" class="space-y-2">
                    <div class="skeleton h-4 w-32"></div>
                    <div class="skeleton h-4 w-28"></div>
                    <div class="skeleton h-4 w-36"></div>
                </div>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="grid gap-6 mb-8">
            <div class="lg:col-span-2">
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">Habits Progress</h3>
                    <div class="chart-container">
                        <canvas id="habitsChart"></canvas>
                    </div>
                </div>
            </div>

            <div class="lg:col-span-2">
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-medium text-gray-900 mb-4">Traits Analysis</h3>
                    <div class="chart-container">
                        <canvas id="traitsChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Filters -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h3 class="text-lg font-medium text-gray-900 mb-4">Filters</h3>
            <div class="flex flex-wrap gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Time Range</label>
                    <select id="timeRange" class="border rounded px-3 py-2 w-32 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        <option value="week">Last Week</option>
                        <option value="month" selected>Last Month</option>
                        <option value="quarter">Last Quarter</option>
                        <option value="year">Last Year</option>
                        <option value="all">All Time</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Category</label>
                    <select id="categoryFilter" class="border rounded px-3 py-2 w-40 focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        <option value="all" selected>All Categories</option>
                        <option value="produtividade">Productivity</option>
                        <option value="carreira">Career</option>
                        <option value="bem-estar">Well-being</option>
                        <option value="aprendizado">Learning</option>
                    </select>
                </div>
                <button id="applyFilters" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                    Apply Filters
                </button>
            </div>
        </div>

        <!-- Data Tables -->
        <div class="grid gap-6">
            <!-- Recent Activities -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Recent Activities</h3>
                <div id="recent-activities" class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200" id="activitiesTableBody">
                            <tr>
                                <td colspan="4" class="px-6 py-4 text-center text-gray-500">Loading...</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Observations -->
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Recent Observations</h3>
                <div id="observations" class="space-y-3">
                    <div class="skeleton h-8 w-64"></div>
                    <div class="skeleton h-8 w-48"></div>
                    <div class="skeleton h-8 w-56"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Chart.js instances
        let habitsChart = null;
        let traitsChart = null;

        // Load initial data
        document.addEventListener('DOMContentLoaded', () => {
            loadDashboardData();
            loadCharts();
        });

        // Load dashboard data
        async function loadDashboardData() {
            try {
                // Load profile data
                const profileResponse = await fetch('/api/profile');
                const profileData = await profileResponse.json();
                updateProfileStats(profileData);

                // Load habits data
                const habitsResponse = await fetch('/api/habits');
                const habitsData = await habitsResponse.json();
                updateHabitsStats(habitsData);

                // Load traits data
                const traitsResponse = await fetch('/api/traits');
                const traitsData = await traitsResponse.json();
                updateTraitsStats(traitsData);

                // Load goals data
                const goalsResponse = await fetch('/api/goals');
                const goalsData = await goalsResponse.json();
                updateGoalsStats(goalsData);

                // Load recent activities
                const activitiesResponse = await fetch('/api/activities');
                const activitiesData = await activitiesResponse.json();
                updateRecentActivities(activitiesData);

                // Load observations
                const observationsResponse = await fetch('/api/observations');
                const observationsData = await observationsResponse.json();
                updateObservations(observationsData);
            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }

        // Update profile stats
        function updateProfileStats(data) {
            const container = document.getElementById('profile-stats');
            if (container && data) {
                container.innerHTML = `
                    <div><span class="font-medium">Name:</span> ${data.name || 'N/A'}</div>
                    <div><span class="font-medium">Age:</span> ${data.age || 'N/A'}</div>
                    <div><span class="font-medium">Timezone:</span> ${data.timezone || 'N/A'}</div>
                    <div><span class="font-medium">Work Style:</span> ${data.work_style || 'N/A'}</div>
                `;
            }
        }

        // Update habits stats
        function updateHabitsStats(data) {
            const container = document.getElementById('habits-stats');
            if (container && data) {
                const activeHabits = data.filter(h => h.status === 'active').length;
                const totalCompletions = data.reduce((sum, h) => sum + (h.total_completions || 0), 0);
                const avgStreak = data.reduce((sum, h) => sum + (h.current_streak || 0), 0) / data.length || 0;

                container.innerHTML = `
                    <div><span class="font-medium">Active Habits:</span> ${activeHabits}/${data.length}</div>
                    <div><span class="font-medium">Total Completions:</span> ${totalCompletions}</div>
                    <div><span class="font-medium">Avg Current Streak:</span> ${avgStreak.toFixed(1)}</div>
                `;
            }
        }

        // Update traits stats
        function updateTraitsStats(data) {
            const container = document.getElementById('traits-stats');
            if (container && data) {
                const highConfidence = data.filter(t => (t.confidence_score || 0) > 0.7).length;
                const avgConfidence = data.reduce((sum, t) => sum + (t.confidence_score || 0), 0) / data.length || 0;

                container.innerHTML = `
                    <div><span class="font-medium">Total Traits:</span> ${data.length}</div>
                    <div><span class="font-medium">High Confidence (>0.7):</span> ${highConfidence}</div>
                    <div><span class="font-medium">Avg Confidence:</span> ${avgConfidence.toFixed(2)}</div>
                `;
            }
        }

        // Update goals stats
        function updateGoalsStats(data) {
            const container = document.getElementById('goals-stats');
            if (container && data) {
                const activeGoals = data.filter(g => g.status === 'active').length;
                const completedGoals = data.filter(g => g.status === 'completed').length;
                const avgProgress = data.reduce((sum, g) => sum + (g.progress || 0), 0) / data.length || 0;

                container.innerHTML = `
                    <div><span class="font-medium">Active Goals:</span> ${activeGoals}</div>
                    <div><span class="font-medium">Completed Goals:</span> ${completedGoals}</div>
                    <div><span class="font-medium">Avg Progress:</span> ${avgProgress.toFixed(1)}%</div>
                `;
            }
        }

        // Load charts data
        async function loadCharts() {
            try {
                // Load habits chart data
                const habitsChartResponse = await fetch('/api/habits-chart');
                const habitsChartData = await habitsChartResponse.json();
                renderHabitsChart(habitsChartData);

                // Load traits chart data
                const traitsChartResponse = await fetch('/api/traits-chart');
                const traitsChartData = await traitsChartResponse.json();
                renderTraitsChart(traitsChartData);
            } catch (error) {
                console.error('Error loading charts:', error);
            }
        }

        // Render habits chart
        function renderHabitsChart(data) {
            const ctx = document.getElementById('habitsChart').getContext('2d');
            if (habitsChart) {
                habitsChart.destroy();
            }
            habitsChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Completions',
                        data: data.completions,
                        backgroundColor: 'rgba(59, 130, 246, 0.5)',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Habits Completion Count'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            }
                        }
                    }
                }
            });
        }

        // Render traits chart
        function renderTraitsChart(data) {
            const ctx = document.getElementById('traitsChart').getContext('2d');
            if (traitsChart) {
                traitsChart.destroy();
            }
            traitsChart = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Confidence Scores',
                        data: data.scores,
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Traits Confidence Analysis'
                        }
                    },
                    scales: {
                        r: {
                            suggestedMin: 0,
                            suggestedMax: 1
                        }
                    }
                }
            });
        }

        // Update recent activities table
        function updateRecentActivities(data) {
            const tbody = document.getElementById('activitiesTableBody');
            if (tbody && data) {
                if (data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">No recent activities</td></tr>';
                    return;
                }

                tbody.innerHTML = data.map(activity => `
                    <tr>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${activity.type}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${activity.description}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${activity.date}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm">${activity.status === 'completed' ? 
                            '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Completed</span>' : 
                            '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">Pending</span>'}</td>
                    </tr>
                `).join('');
            }
        }

        // Update observations
        function updateObservations(data) {
            const container = document.getElementById('observations');
            if (container && data) {
                if (data.length === 0) {
                    container.innerHTML = '<p class="text-gray-500">No recent observations</p>';
                    return;
                }

                container.innerHTML = data.map(obs => `
                    <div class="border-l-4 border-blue-500 pl-4 mb-3">
                        <p class="text-sm text-gray-700">${obs.content}</p>
                        <p class="text-xs text-gray-500">${new Date(obs.timestamp).toLocaleString()}</p>
                    </div>
                `).join('');
            }
        }

        // Filter functionality
        document.getElementById('applyFilters')?.addEventListener('click', () => {
            const timeRange = document.getElementById('timeRange')?.value;
            const category = document.getElementById('categoryFilter')?.value;
            
            // In a real implementation, we would filter the data based on these values
            console.log('Applying filters:', { timeRange, category });
            // For now, we'll just reload the data
            loadDashboardData();
            loadCharts();
        });

        // Auto-refresh every 30 seconds
        setInterval(() => {
            loadDashboardData();
            loadCharts();
        }, 30000);
    </script>
</body>
</html>
`;
}

// Create HTTP server
const server = createServer((req, res) => {
  const url = new URL(req.url || '', `http://${req.headers.host}`);

  // Handle CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Route handling
  if (req.method === 'GET' && url.pathname === '/') {
    // Serve dashboard HTML
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(getDashboardHtml());
  } 
  else if (req.method === 'GET' && url.pathname === '/api/profile') {
    // Get profile data
    try {
      const profile = db.prepare('SELECT * FROM profile LIMIT 1').get();
      if (profile) {
        sendJson(res, 200, {
          id: profile.id,
          name: profile.name,
          age: profile.age,
          timezone: profile.timezone,
          work_style: profile.work_style,
          energy_peak_hours: profile.energy_peak_hours,
          communication_preference: profile.communication_preference,
          decision_style: profile.decision_style,
          core_values: profile.core_values,
          feedback_preference: profile.feedback_preference,
          goals_current_year: profile.goals_current_year,
          constraints: profile.constraints
        });
      } else {
        sendJson(res, 404, { error: 'Profile not found' });
      }
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else if (req.method === 'GET' && url.pathname === '/api/habits') {
    // Get habits data
    try {
      const habits = db.prepare('SELECT * FROM habits').all();
      sendJson(res, 200, habits);
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else if (req.method === 'GET' && url.pathname === '/api/traits') {
    // Get traits data
    try {
      const traits = db.prepare('SELECT * FROM traits').all();
      sendJson(res, 200, traits);
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else if (req.method === 'GET' && url.pathname === '/api/goals') {
    // Get goals data
    try {
      const goals = db.prepare('SELECT * FROM goals').all();
      sendJson(res, 200, goals);
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else if (req.method === 'GET' && url.pathname === '/api/activities') {
    // Get recent activities (from observations and behaviors)
    try {
      const activities = db.prepare(`
        SELECT 
          'observation' as type,
          obs_type as description,
          strftime('%Y-%m-%d %H:%M', observed_at) as date,
          'completed' as status
        FROM observations 
        ORDER BY observed_at DESC 
        LIMIT 10
        
        UNION ALL
        
        SELECT 
          'behavior' as type,
          behavior_type || ': ' || response as description,
          strftime('%Y-%m-%d %H:%M', observed_date) as date,
          CASE WHEN effectiveness > 0.7 THEN 'completed' ELSE 'pending' END as status
        FROM behaviors 
        ORDER BY observed_date DESC 
        LIMIT 10
        
        ORDER BY date DESC
        LIMIT 20
      `).all();
      
      sendJson(res, 200, activities);
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else if (req.method === 'GET' && url.pathname === '/api/observations') {
    // Get observations
    try {
      const observations = db.prepare(`
        SELECT 
          id,
          obs_type as type,
          data as content,
          observed_at as timestamp
        FROM observations 
        ORDER BY observed_at DESC 
        LIMIT 20
      `).all();
      
      sendJson(res, 200, observations);
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else if (req.method === 'GET' && url.pathname === '/api/habits-chart') {
    // Get habits data for chart
    try {
      const habits = db.prepare('SELECT habit_name, total_completions FROM habits ORDER BY total_completions DESC').all();
      
      sendJson(res, 200, {
        labels: habits.map(h => h.habit_name),
        completions: habits.map(h => h.total_completions)
      });
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else if (req.method === 'GET' && url.pathname === '/api/traits-chart') {
    // Get traits data for chart
    try {
      const traits = db.prepare('SELECT trait_name, confidence_score FROM traits WHERE confidence_score IS NOT NULL ORDER BY confidence_score DESC LIMIT 8').all();
      
      sendJson(res, 200, {
        labels: traits.map(t => t.trait_name),
        scores: traits.map(t => t.confidence_score || 0)
      });
    } catch (error) {
      sendJson(res, 500, { error: 'Database error' });
    }
  }
  else {
    // Not found
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not Found');
  }
});

// Start server
server.listen(PORT, '127.0.0.1', () => {
  console.log(`Dashboard server running at http://127.0.0.1:${PORT}`);
  console.log('Press Ctrl+C to stop');
});

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down dashboard server...');
  server.close(() => {
    console.log('Dashboard server stopped.');
    process.exit(0);
  });
});