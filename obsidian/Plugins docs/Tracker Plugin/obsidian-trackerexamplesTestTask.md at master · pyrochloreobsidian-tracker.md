---
title: obsidian-tracker/examples/TestTask.md at master · pyrochlore/obsidian-tracker
source: https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestTask.md
author:
  - "[[denissok]]"
published:
created: 2025-12-07
description: A plugin tracks occurrences and numbers in your notes - obsidian-tracker/examples/TestTask.md at master · pyrochlore/obsidian-tracker
tags:
  - clippings
---
[Skip to content](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/#start-of-content)

[Open in github.dev](https://github.dev/) [Open in a new github.dev tab](https://github.dev/) [Open in codespace](https://github.com/codespaces/new/pyrochlore/obsidian-tracker/tree/master?resume=1)

## Latest commit

[Updated examples with start and end dates so that](https://github.com/pyrochlore/obsidian-tracker/commit/37c2b60c8dcaab5418631e02a5d9f4c059e6243f)

[37c2b60](https://github.com/pyrochlore/obsidian-tracker/commit/37c2b60c8dcaab5418631e02a5d9f4c059e6243f) ·

## Test Task

## Summary

### All Tasks

Collect all tasks matched `searchTarget`

```
searchType: task
searchTarget: Say I love you
folder: diary
summary:
    template: "Total count: {{sum()}}"
```

### All Tasks

Collect all tasks matched `searchTarget`

```
searchType: task.all
searchTarget: Say I love you
folder: diary
summary:
    template: "Total count: {{sum()}}"
```

### Task Done

Collect all tasks done matched `searchTarget`

```
searchType: task.done
searchTarget: Say I love you
folder: diary
summary:
    template: "How many days I said: {{sum()}}"
```

Collect all tasks not-done matched `searchTarget`

```
searchType: task.notdone
searchTarget: Say I love you
folder: diary
summary:
    template: "How many days I didn't say: {{sum()}}"
```

## Month View

See tasks done in month view

```
searchType: task.done
searchTarget: Say I love you
folder: diary
datasetName: Love
endDate: 2021-01-31
month:
    color: tomato
    headerMonthColor: orange
    todayRingColor: orange
    selectedRingColor: steelblue
    showSelectedValue: false
```

task.done and task.notdone

```
searchType: task.done, task.notdone
searchTarget: Say I love you, Say I love you
folder: diary
datasetName: Good Lover, Bad Lover
endDate: 2021-01-31
month:
    color: tomato
    headerMonthColor: orange
    todayRingColor: orange
    selectedRingColor: steelblue
    showSelectedValue: false
```