# TaskNotes/Views/

## Responsibility
View template definitions for task management — 6 `.base` files that each define a specific view layout for rendering task data in different formats (agenda, calendar, kanban, mini-calendar, relationships, default tasks).

## View Catalog

| Template File | Purpose |
|---------------|---------|
| `agenda-default.base` | Chronological agenda layout for daily/weekly task scheduling |
| `calendar-default.base` | Calendar grid view for task placement on dates |
| `kanban-default.base` | Kanban board with columns for workflow stages |
| `mini-calendar-default.base` | Compact month calendar widget for sidebars |
| `relationships.base` | Task-to-relationship linking and people-associated tasks |
| `tasks-default.base` | Default flat task list view with sorting and filtering |

## Template Format
`.base` files define view layouts using a structured configuration format (likely JSON or DSL). Each template specifies columns, sorting, filtering criteria, and display rendering rules.

## Integration Points
- **Consumed by**: TaskNotes UI renderer
- **Data source**: Task data from `personal-ai-space/command/tasks/active_tasks.json` and `db/tasks.db`
