from __future__ import annotations

from typing import Optional, List, Dict
from datetime import datetime
from fastmcp import FastMCPApp

# Import your existing database manager
from personal_ai_space.engine.db.db_manager import DatabaseManager

mcp = FastMCPApp(
    "task-management-mcp",
    instructions=(
        "MCP interface to the Personal AI Powerhouse task management system. "
        "Manage tasks, projects, and workflows."
    ),
)

@mcp.tool()
def list_tasks(
    due_date: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20
) -> List[Dict]:
    """List tasks from the tasks database.
    
    Args:
        due_date: Filter by due date (YYYY-MM-DD)
        status: Filter by status (pending, completed, etc.)
        limit: Maximum number of tasks to return
    
    Returns:
        List of task dictionaries with id, title, status, due_date
    """
    db = DatabaseManager('tasks.db')
    
    query = "SELECT id, title, status, due_date FROM tasks WHERE 1=1"
    params = []
    
    if due_date:
        query += " AND due_date = ?"
        params.append(due_date)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY due_date ASC LIMIT ?"
    params.append(limit)
    
    results = db.execute(query, params)
    
    return [
        {
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "due_date": row[3]
        }
        for row in results
    ]

@mcp.tool()
def create_task(
    title: str,
    description: str = "",
    due_date: Optional[str] = None,
    project_id: Optional[str] = None
) -> Dict:
    """Create a new task in the tasks database.
    
    Args:
        title: Task title
        description: Task description
        due_date: Due date (YYYY-MM-DD)
        project_id: Associated project ID
    
    Returns:
        Dictionary with task_id and success status
    """
    db = DatabaseManager('tasks.db')
    
    query = """
        INSERT INTO tasks (title, description, due_date, project_id, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
    """
    
    params = [
        title,
        description,
        due_date,
        project_id,
        datetime.now().isoformat()
    ]
    
    task_id = db.execute(query, params, return_id=True)
    
    return {
        "success": True,
        "task_id": task_id,
        "message": "Task created successfully"
    }

@mcp.tool()
def update_task_status(
    task_id: str,
    new_status: str
) -> Dict:
    """Update the status of an existing task.
    
    Args:
        task_id: ID of the task to update
        new_status: New status (pending, completed, cancelled, etc.)
    
    Returns:
        Dictionary with success status
    """
    db = DatabaseManager('tasks.db')
    
    query = "UPDATE tasks SET status = ? WHERE id = ?"
    result = db.execute(query, [new_status, task_id])
    
    return {
        "success": result.rowcount > 0,
        "updated_rows": result.rowcount,
        "message": "Task updated" if result.rowcount > 0 else "Task not found"
    }

@mcp.tool()
def get_task_details(task_id: str) -> Optional[Dict]:
    """Get detailed information about a specific task.
    
    Args:
        task_id: ID of the task
    
    Returns:
        Task dictionary or None if not found
    """
    db = DatabaseManager('tasks.db')
    
    query = """
        SELECT id, title, description, status, due_date, project_id, created_at, updated_at
        FROM tasks WHERE id = ?
    """
    
    result = db.execute(query, [task_id])
    row = result.fetchone()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "title": row[1],
        "description": row[2],
        "status": row[3],
        "due_date": row[4],
        "project_id": row[5],
        "created_at": row[6],
        "updated_at": row[7]
    }

if __name__ == "__main__":
    # Test the endpoint
    mcp.run(transport="stdio")