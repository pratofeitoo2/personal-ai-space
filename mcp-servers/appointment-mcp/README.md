# Appointment MCP Server

MCP server for calendar and appointment access in Personal AI Powerhouse.

## Endpoints
- `get_appointments(date_range, limit)`
- `create_appointment(title, start_time, end_time, location, description)`
- `get_appointment_details(appointment_id)`

## Usage
```bash
appointment-mcp  # Start server
opencode run "What appointments do I have today?" --mcp appointment-mcp
```