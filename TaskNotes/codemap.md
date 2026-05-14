# TaskNotes/

## Responsibility
Task note view templates — defines the presentation layer for task management views (agenda, calendar, kanban, mini-calendar, relationships, and default task list). Each `.base` file contains a view configuration template.

## Structure
- `Views/` — View template definitions (6 base templates)

## View Types
- **agenda**: Chronological task agenda view
- **calendar**: Calendar-based task scheduling view
- **kanban**: Kanban board workflow view
- **mini-calendar**: Compact calendar widget
- **relationships**: Task-relationship linking view
- **tasks**: Default task list view

## Integration Points
- **Consumed by**: Task management UI
- **Related to**: `personal-ai-space/command/tasks/active_tasks.json` (runtime task data)
