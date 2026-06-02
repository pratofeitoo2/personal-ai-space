const http = require('http');
const fs = require('fs');
const path = require('path');
const Database = require('better-sqlite3');

// Initialize database connection
const dbPath = path.join(__dirname, 'engine', 'db', 'self', 'self.db');
const db = new Database(dbPath, { readonly: true });

// Dashboard server port
const PORT = 8080;

// Helper function to send JSON response
function sendJson(res, status, data) {
  res.writeHead(status, { 
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type'
  });
  res.end(JSON.stringify(data));
}

// Helper function to send HTML response
function sendHtml(res, status, html) {
  res.writeHead(status, { 
    'Content-Type': 'text/html',
    'Access-Control-Allow-Origin': '*'
  });
  res.end(html);
}

// Create HTTP server
const server = http.createServer((req, res) => {
  const url = new URL(req.url || '', `http://${req.headers.host}`);

  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end();
    return;
  }

  // Route handling
  if (req.method === 'GET' && url.pathname === '/') {
    // Serve dashboard HTML
    try {
      const htmlPath = path.join(__dirname, 'dashboard.html');
      const html = fs.readFileSync(htmlPath, 'utf8');
      sendHtml(res, 200, html);
    } catch (error) {
      res.writeHead(500, { 'Content-Type': 'text/plain' });
      res.end('Error loading dashboard');
    }
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
    db.close();
    console.log('Dashboard server stopped.');
    process.exit(0);
  });
});