---
tags:
  - moc
  - self
created: 2026-06-12
---

# MOC - Self

Digital twin — your goals, habits, relationships, and personal data.

## Profile
- [[02 - Self/Profile/Paulo Rezende|Paulo Rezende]]
- [[02 - Self/Profile/Personality|Personality]]

## Goals
```dataview
TABLE status, progress, target_date
FROM "02 - Self/Goals"
SORT target_date ASC
```

## Habits
```dataview
TABLE habit_name, category, frequency, current_streak
FROM "02 - Self/Habits"
SORT habit_name ASC
```

## Needs
```dataview
TABLE name, category, priority, status
FROM "02 - Self/Needs"
SORT priority ASC
```

## Relationships
```dataview
TABLE Name, email, birth_date
FROM "02 - Self/Relationships"
WHERE file.name != "People.base"
SORT Name ASC
```

## Documents
- Healthcare
- Kids
- Military
- Work Card
- Birth Certificate
- Voter Registration

## Related MOCs
- [[Home]]
- [[04 - Career/MOC - Career|Career]]
