from __future__ import annotations

from typing import Optional, List, Dict
from datetime import datetime
from fastmcp import FastMCP

from personal_ai_space.engine.db.db_manager import DatabaseManager

mcp = FastMCP("appointment-mcp")

@mcp.tool()
def get_appointments(
    date_range: Optional[str] = None,
    limit: int = 20
) -> List[Dict]:
    """Get appointments from the calendar.
    
    Args:
        date_range: Date range filter (YYYY-MM-DD to YYYY-MM-DD)
        limit: Maximum number of appointments to return
    
    Returns:
        List of appointment dictionaries
    """
    db = DatabaseManager('tasks.db')  # Calendar is in tasks.db per codemap
    
    query = """
        SELECT id, title, start_time, end_time, location, description
        FROM calendar_events
        WHERE 1=1
    """
    params = []
    
    if date_range:
        start_date, end_date = date_range.split(" to ")
        query += " AND start_time >= ? AND end_time <= ?"
        params.extend([start_date, end_date])
    
    query += " ORDER BY start_time ASC LIMIT ?"
    params.append(limit)
    
    results = db.execute(query, params)
    
    return [
        {
            "id": row[0],
            "title": row[1],
            "start_time": row[2],
            "end_time": row[3],
            "location": row[4],
            "description": row[5]
        }
        for row in results
    ]

@mcp.tool()
def create_appointment(
    title: str,
    start_time: str,
    end_time: str,
    location: Optional[str] = None,
    description: Optional[str] = None
) -> Dict:
    """Create a new appointment.
    
    Args:
        title: Appointment title
        start_time: Start time (ISO format)
        end_time: End time (ISO format)
        location: Location (optional)
        description: Description (optional)
    
    Returns:
        Dictionary with appointment_id and success status
    """
    db = DatabaseManager('tasks.db')
    
    query = """
        INSERT INTO calendar_events 
        (title, start_time, end_time, location, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    params = [
        title,
        start_time,
        end_time,
        location,
        description,
        datetime.now().isoformat()
    ]
    
    appointment_id = db.execute(query, params, return_id=True)
    
    return {
        "success": True,
        "appointment_id": appointment_id,
        "message": "Appointment created successfully"
    }

@mcp.tool()
def get_appointment_details(appointment_id: str) -> Optional[Dict]:
    """Get detailed information about an appointment.
    
    Args:
        appointment_id: ID of the appointment
    
    Returns:
        Appointment dictionary or None if not found
    """
    db = DatabaseManager('tasks.db')
    
    query = """
        SELECT id, title, start_time, end_time, location, description, created_at
        FROM calendar_events WHERE id = ?
    """
    
    result = db.execute(query, [appointment_id])
    row = result.fetchone()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "title": row[1],
        "start_time": row[2],
        "end_time": row[3],
        "location": row[4],
        "description": row[5],
        "created_at": row[6]
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")