---
company: Company Name                   # TEXT → companies.name (required)
company_website: https://example.com    # TEXT → companies.website
company_industry: Tech                  # TEXT → companies.industry
position: Job Title                     # TEXT → applications.job_title (required)
url: https://example.com/careers/xxx    # TEXT → applications.job_url
description: Full job description       # TEXT → applications.job_description
salary: $100k-$130k                     # TEXT → applications.salary_range
location: Remote / City, State          # TEXT → applications.location
remote: true                            # BOOL → applications.remote
status: saved                           # TEXT → applications.status
                                        #   (saved, applied, screening, interview,
                                        #    offer, rejected, withdrawn, accepted)
applied: 2026-05-20                     # DATE → applications.applied_date
notes: Optional notes about this role   # TEXT merged with body text

interviews:                             # LIST → interviews table
  - round: 1
    type: phone                         # (phone, video, technical, onsite, case,
                                        #  panel, take_home, cultural, other)
    scheduled: 2026-05-20T10:00:00     # DATETIME → interviews.scheduled_at
    duration: 45                        # INT minutes → interviews.duration_minutes
    interviewer: Name                   # TEXT → interviews.interviewer_name
    interviewer_role: Title             # TEXT → interviews.interviewer_role
    feedback: Went well                 # TEXT → interviews.feedback
    notes: Notes about this round       # TEXT → interviews.notes

contacts:                               # LIST → contacts table
  - name: Contact Name                 # TEXT → contacts.name (required)
    role: Engineering Manager           # TEXT → contacts.role
    email: name@company.com            # TEXT → contacts.email
    linkedin: https://linkedin.com/in/  # TEXT → contacts.linkedin
    phone: +1 555-0000                  # TEXT → contacts.phone
    notes: Met at conference            # TEXT → contacts.notes
---

Write your application notes here. This body text gets stored in
applications.notes alongside the frontmatter `notes` field.

Use this space for:
- Research notes about the company
- Preparation notes for interviews
- Follow-up reminders
- Salary negotiation strategy
- Any other context you want to keep
