# Personal AI Dashboard

A stunning live dashboard for visualizing personal AI data from the SQLite database.

## Features

- **Real-time Data**: Live updates every 30 seconds
- **Interactive Charts**: Bar charts for habits, radar charts for traits
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Clean Animations**: Smooth transitions and hover effects
- **Filter System**: Time range and category filters
- **Auto-refresh**: Dashboard updates automatically

## Quick Start

### 1. Setup Virtual Environment

```bash
cd personal-ai-space
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the Dashboard

```bash
python dashboard_server.py
```

### 3. Open in Browser

Open http://127.0.0.1:5000 in your web browser.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard HTML page |
| `GET /api/profile` | User profile data |
| `GET /api/habits` | All habits with stats |
| `GET /api/traits` | Personality traits |
| `GET /api/goals` | Goals and progress |
| `GET /api/activities` | Recent activities |
| `GET /api/observations` | Recent observations |
| `GET /api/habits-chart` | Habits data for charts |
| `GET /api/traits-chart` | Traits data for radar chart |

## Dashboard Components

### Stats Cards
- **Profile**: Name, age, timezone, work style
- **Habits**: Active habits, completions, streaks
- **Traits**: Total traits, confidence scores
- **Goals**: Active/completed goals, progress

### Charts
- **Habits Progress**: Bar chart showing completion counts
- **Traits Analysis**: Radar chart showing confidence scores

### Filters
- **Time Range**: Last Week, Month, Quarter, Year, All Time
- **Category**: Productivity, Career, Well-being, Learning

### Data Tables
- **Recent Activities**: Observations and behaviors
- **Recent Observations**: Latest system observations

## Technical Details

### Architecture
- **Backend**: Python Flask server
- **Database**: SQLite (read-only access)
- **Frontend**: HTML with Tailwind CSS, Chart.js, HTMX
- **Animations**: CSS keyframes with staggered delays

### Database Schema
The dashboard reads from 12 tables:
- `profile` - User profile information
- `habits` - Habit tracking data
- `habit_logs` - Habit completion logs
- `traits` - Personality traits with confidence scores
- `needs` - Personal needs assessment
- `behaviors` - Behavioral patterns
- `relationships` - Social connections
- `goals` - Goals and progress tracking
- `observations` - System observations
- `documents` - Personal documents
- `session_signals` - Session behavioral signals
- `session_metadata` - Session statistics

### Performance
- Database queries are optimized for read-only access
- Charts load asynchronously
- Auto-refresh prevents stale data
- Skeleton loading states for better UX

## Customization

### Adding New Charts
1. Add API endpoint in `dashboard_server.py`
2. Create chart component in `dashboard.html`
3. Update JavaScript to fetch and render data

### Modifying Styles
Edit the `<style>` section in `dashboard.html`:
- Animations: Modify `@keyframes` rules
- Colors: Update Tailwind classes
- Layout: Adjust grid and flexbox properties

### Database Changes
If schema changes:
1. Update API queries in `dashboard_server.py`
2. Modify data mapping in JavaScript functions
3. Update chart configurations if needed

## Troubleshooting

### Database Connection Error
Ensure the database file exists at:
```
engine/db/self/self.db
```

### Port Already in Use
Change the port in `dashboard_server.py`:
```python
app.run(debug=True, host='127.0.0.1', port=5001)  # Change port
```

### Missing Dependencies
Reinstall requirements:
```bash
pip install -r requirements.txt
```

## Development

### Running in Development Mode
The server runs in debug mode by default, which:
- Auto-reloads on code changes
- Provides detailed error messages
- Enables debugger PIN

### Production Deployment
For production, use a WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 dashboard_server:app
```

## License

This dashboard is part of the Personal AI Powerhouse project.