---
tags:
  - moc
  - career
created: 2026-06-12
---

# MOC - Career

Professional development — resumes, cover letters, certificates, and job tracking.

## Resumes
```dataview
TABLE language, focus
FROM "04 - Career/Resumes"
SORT file.name ASC
```

## Cover Letters
```dataview
TABLE file.link as "Letter"
FROM "04 - Career/Cover Letters"
SORT file.name ASC
```

## Profiles
```dataview
TABLE file.link as "Profile"
FROM "04 - Career/Profiles"
SORT file.name ASC
```

## Certificates
```dataview
TABLE file.link as "Certificate"
FROM "04 - Career/Certificates"
SORT file.name ASC
```

## Job Board
![[Job Board.base]]

## Interviews
```dataview
TABLE company, position, date, format
FROM "04 - Career/Interviews"
SORT date DESC
```

## Related MOCs
- [[Home]]
- [[02 - Self/MOC - Self|Self]]
