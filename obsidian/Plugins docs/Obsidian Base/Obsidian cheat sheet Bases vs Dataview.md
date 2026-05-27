---
title: "Obsidian cheat sheet: Bases vs Dataview"
author:
  - "[[Len]]"
created: 2025-12-05
description: "Obsidian cheat sheet: Bases vs Dataview when to use which, and copy-paste snippets to get results fast. Pick the tool that fits the job Use Bases when… You want a clickable table/cards UI you can …"
tags:
  - clippings
updated: 2025-12-05T22:08
---
[Sitemap](https://medium.com/sitemap/sitemap.xml)[Write](https://medium.com/new-story?source=post_page---top_nav_layout_nav-----------------------------------------)

![](https://miro.medium.com/v2/resize:fit:640/format:webp/1*U2BAh7iaUth5jLwT3r3stA.png)

## when to use which, and copy-paste snippets to get results fast.

## Pick the tool that fits the job

**Use Bases when…**

- You want a **clickable table/cards UI** you can **edit inline** (checkboxes, dates, selects).
- You prefer **point-and-click filters/sorts** and reusable views you can embed in dashboards.
- You’re building “operational” boards: tasks, reading lists, project pipelines, teaching trackers.

**Use Dataview when…**

- You want **queries** in your notes: powerful filtering, grouping, summaries, rollups.
- You need **derived columns** and ad-hoc reports (counts, group by, custom fields) with quick text edits.
- You’re fine with a **read-only view** (you edit notes, not cells) — unless you go deeper with `dataviewjs`.

**Best of both:** Keep all data in the same **frontmatter properties**; build **interactive boards** with Bases and **reports/analytics** with Dataview.

## Setup (1 minute)

**Bases (core plugin)**

- Settings → Core plugins → enable **Bases**.

**Dataview (community plugin)**

- Settings → Community plugins → Browse → install **Dataview** → enable.
- Use **DQL** code blocks (` ```dataview `) or **DataviewJS** (` ```dataviewjs `).

## Shared data model (works for both)

Put consistent properties at the top of notes:

```c
---
type: reading
title: The Structure of Scientific Revolutions
author: Thomas Kuhn
status: to-read       # to-read | reading | finished
added: 2025-09-26
---
```
```c
---
type: task
task: Submit conference abstract
deadline: 2025-10-10
priority: high       # high | medium | low
done: false
---
```
```c
---
type: research
paper_title: Graph Neural Networks Survey
topic: machine learning
summarized: false
notes_link: [[GNN Notes]]
---
```

Keep property names **lowercase + short** (`status`, `deadline`, `topic`). Same properties feed both tools.

## The same use cases, side-by-side

## Become a member to read this story, and all of Medium.

Len put this story behind our paywall, so it’s only available to read with a paid Medium membership, which comes with a host of benefits:

Access all member-only stories on Medium

Get unlimited access to programming stories from industry leaders

Become an expert in your areas of interest

Get in-depth articles answering thousands of programming questions

Grow your career or build a new one

![Steve Yegge](https://miro.medium.com/v2/resize:fill:128:128/1*OrBdZ2GUUicWcT6x8KSYZg.png)

Steve Yegge

ex-Geoworks, ex-Amazon, ex-Google, and ex-Grab

![Carlos Arguelles](https://miro.medium.com/v2/resize:fill:128:128/1*CM27oO9pXETXjs2M9_dUFg.jpeg)

Carlos Arguelles

Sr. Staff Engineer

Google

![Tony Yiu](https://miro.medium.com/v2/resize:fill:128:128/2*CSDritfpmHLYxn63arD9sQ.jpeg)

Tony Yiu

Director

Nasdaq

![Brandeis Marshall](https://miro.medium.com/v2/resize:fill:128:128/1*qLWny7soUL4K4lqhX1wQVw.png)

Brandeis Marshall

CEO

DataedX

![Austin Starks](https://miro.medium.com/v2/resize:fill:128:128/1*dfww62lW8x8sVZNbLx5aCA.jpeg)

Austin Starks

Software Engineer and Entrepreneur

![Camille Fournier](https://miro.medium.com/v2/resize:fill:128:128/1*J2fWNTyPbgEhIyvVIjHAXg.jpeg)

Camille Fournier

Head of Engineering

JPMorgan Chase

[Upgrade](https://medium.com/plans?subscribeToUserId=&susiEntry=post_paywall&source=upgrade_membership---post_limit--225b08f5bcf2---------------------------------------)

I'm a Ph.D. student with a passion for data science and programming, specializing in Python. My writing explores the intersection of academia and technology.

## Responses (1)

To respond to this story,  
get the free Medium app.

[Continue in app](https://medium.com/@lennart.dde/225b08f5bcf2)

[![A button that says 'Download on the App Store', and if clicked it will lead you to the iOS App store](https://miro.medium.com/v2/resize:fit:240/1*Crl55Tm6yDNMoucPo1tvDg.png)](https://itunes.apple.com/app/medium-everyones-stories/id828256236?pt=698524&mt=8&ct=post_page&source=post_page---post_responses--225b08f5bcf2---------------------------------------)

[![A button that says 'Get it on, Google Play', and if clicked it will lead you to the Google Play store](https://miro.medium.com/v2/resize:fit:240/1*W_RAPQ62h0em559zluJLdQ.png)](https://play.google.com/store/apps/details?id=com.medium.reader&referrer=utm_source%3Dpost_page&source=post_page---post_responses--225b08f5bcf2---------------------------------------)

```c
dude i need your update on league. you still playing it or did u completely threw it outta your life
```

## More from Len

## Recommended from Medium

[

See more recommendations

](https://medium.com/?source=post_page---read_next_recirc--225b08f5bcf2---------------------------------------)