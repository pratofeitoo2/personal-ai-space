from __future__ import annotations

from typing import Optional, List, Dict
from fastmcp import FastMCP

from personal_ai_space.engine.db.db_manager import DatabaseManager

mcp = FastMCP("project-context-mcp")

@mcp.tool()
def get_project_context(project_id: str) -> Optional[Dict]:
    """Get full context for a project.
    
    Args:
        project_id: ID of the project
    
    Returns:
        Project context dictionary or None if not found
    """
    db = DatabaseManager('tasks.db')  # Projects are in tasks.db
    
    # Get project info
    project_query = """
        SELECT id, name, description, status, created_at, updated_at
        FROM projects WHERE id = ?
    """
    
    project_result = db.execute(project_query, [project_id])
    project_row = project_result.fetchone()
    
    if not project_row:
        return None
    
    # Get related tasks
    tasks_query = """
        SELECT id, title, status FROM tasks WHERE project_id = ?
    """
    tasks_result = db.execute(tasks_query, [project_id])
    
    # Get related knowledge
    knowledge_query = """
        SELECT id, title, type FROM knowledge WHERE project_id = ?
    """
    knowledge_result = db.execute(knowledge_query, [project_id])
    
    return {
        "project": {
            "id": project_row[0],
            "name": project_row[1],
            "description": project_row[2],
            "status": project_row[3],
            "created_at": project_row[4],
            "updated_at": project_row[5]
        },
        "tasks": [
            {
                "id": row[0],
                "title": row[1],
                "status": row[2]
            }
            for row in tasks_result
        ],
        "knowledge_items": [
            {
                "id": row[0],
                "title": row[1],
                "type": row[2]
            }
            for row in knowledge_result
        ]
    }

@mcp.tool()
def update_project_context(
    project_id: str,
    new_data: Dict
) -> Dict:
    """Update project context with new data.
    
    Args:
        project_id: ID of the project
        new_data: Dictionary of updates (description, status, etc.)
    
    Returns:
        Dictionary with success status
    """
    db = DatabaseManager('tasks.db')
    
    if not new_data:
        return {"success": False, "message": "No data provided"}
    
    # Build dynamic update query
    set_clauses = []
    params = []
    
    for key, value in new_data.items():
        if key in ['description', 'status']:  # Whitelist safe fields
            set_clauses.append(f"{key} = ?")
            params.append(value)
    
    if not set_clauses:
        return {"success": False, "message": "No valid fields to update"}
    
    query = f"""
        UPDATE projects
        SET {', '.join(set_clauses)}, updated_at = ?
        WHERE id = ?
    """
    
    params.append(datetime.now().isoformat())
    params.append(project_id)
    
    result = db.execute(query, params)
    
    return {
        "success": result.rowcount > 0,
        "updated_rows": result.rowcount,
        "message": "Project updated" if result.rowcount > 0 else "Project not found"
    }

@mcp.tool()
def list_projects(
    status: Optional[str] = None,
    limit: int = 20
) -> List[Dict]:
    """List all projects with optional filtering.
    
    Args:
        status: Filter by project status
        limit: Maximum number of projects to return
    
    Returns:
        List of project dictionaries
    """
    db = DatabaseManager('tasks.db')
    
    query = """
        SELECT id, name, description, status, created_at
        FROM projects
        WHERE 1=1
    """
    params = []
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    results = db.execute(query, params)
    
    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "status": row[3],
            "created_at": row[4]
        }
        for row in results
    ]

if __name__ == "__main__":
    mcp.run(transport="stdio")