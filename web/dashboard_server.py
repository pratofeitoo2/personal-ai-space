# DEPRECATED — Use the new web app (web/app.py) instead.
# This file is kept for reference only.
# Run: cd personal-ai-space && python -c "from web.app import create_app; create_app().run(host='0.0.0.0', port=5001, debug=True)"
#
#!/usr/bin/env python3
"""
Personal AI Dashboard Server
A Flask-based dashboard for visualizing personal AI data from SQLite database.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, send_file, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database path
DB_PATH = Path(__file__).parent / "engine" / "db" / "self" / "self.db"

def get_db_connection():
    """Create a read-only database connection."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def dict_from_row(row):
    """Convert a sqlite3.Row to a dictionary."""
    return dict(row) if row else None

# API Routes
@app.route('/api/profile')
def get_profile():
    """Get profile data."""
    try:
        conn = get_db_connection()
        profile = conn.execute('SELECT * FROM profile LIMIT 1').fetchone()
        conn.close()
        if profile:
            return jsonify(dict_from_row(profile))
        return jsonify({'error': 'Profile not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/habits')
def get_habits():
    """Get all habits."""
    try:
        conn = get_db_connection()
        habits = conn.execute('SELECT * FROM habits').fetchall()
        conn.close()
        return jsonify([dict_from_row(h) for h in habits])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/traits')
def get_traits():
    """Get all traits."""
    try:
        conn = get_db_connection()
        traits = conn.execute('SELECT * FROM traits').fetchall()
        conn.close()
        return jsonify([dict_from_row(t) for t in traits])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/goals')
def get_goals():
    """Get all goals."""
    try:
        conn = get_db_connection()
        goals = conn.execute('SELECT * FROM goals').fetchall()
        conn.close()
        return jsonify([dict_from_row(g) for g in goals])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/activities')
def get_activities():
    """Get recent activities from observations and behaviors."""
    try:
        conn = get_db_connection()
        
        # Get observations
        observations = conn.execute('''
            SELECT 
                'observation' as type,
                obs_type as description,
                strftime('%Y-%m-%d %H:%M', observed_at) as date,
                'completed' as status
            FROM observations 
            ORDER BY observed_at DESC 
            LIMIT 10
        ''').fetchall()
        
        # Get behaviors
        behaviors = conn.execute('''
            SELECT 
                'behavior' as type,
                behavior_type || ': ' || response as description,
                strftime('%Y-%m-%d %H:%M', observed_date) as date,
                CASE WHEN effectiveness > 0.7 THEN 'completed' ELSE 'pending' END as status
            FROM behaviors 
            ORDER BY observed_date DESC 
            LIMIT 10
        ''').fetchall()
        
        conn.close()
        
        # Combine and sort
        activities = [dict_from_row(o) for o in observations] + [dict_from_row(b) for b in behaviors]
        activities.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        return jsonify(activities[:20])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/observations')
def get_observations():
    """Get recent observations."""
    try:
        conn = get_db_connection()
        observations = conn.execute('''
            SELECT 
                id,
                obs_type as type,
                data as content,
                observed_at as timestamp
            FROM observations 
            ORDER BY observed_at DESC 
            LIMIT 20
        ''').fetchall()
        conn.close()
        return jsonify([dict_from_row(o) for o in observations])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/habits-chart')
def get_habits_chart():
    """Get habits data for chart visualization."""
    try:
        conn = get_db_connection()
        habits = conn.execute('''
            SELECT habit_name, total_completions 
            FROM habits 
            ORDER BY total_completions DESC
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'labels': [h['habit_name'] for h in habits],
            'completions': [h['total_completions'] for h in habits]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/traits-chart')
def get_traits_chart():
    """Get traits data for radar chart visualization."""
    try:
        conn = get_db_connection()
        traits = conn.execute('''
            SELECT trait_name, confidence_score 
            FROM traits 
            WHERE confidence_score IS NOT NULL 
            ORDER BY confidence_score DESC 
            LIMIT 8
        ''').fetchall()
        conn.close()
        
        return jsonify({
            'labels': [t['trait_name'] for t in traits],
            'scores': [t['confidence_score'] or 0 for t in traits]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def serve_dashboard():
    """Serve the dashboard HTML."""
    return send_file('dashboard.html')

if __name__ == '__main__':
    print(f"Dashboard server starting...")
    print(f"Database: {DB_PATH}")
    print(f"Open http://0.0.0.0:5001 in your browser (accessible on your network)")
    app.run(debug=True, host='0.0.0.0', port=5001)