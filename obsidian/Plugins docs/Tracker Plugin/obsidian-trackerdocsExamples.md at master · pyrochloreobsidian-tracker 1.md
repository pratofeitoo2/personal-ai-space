---
title: obsidian-tracker/docs/Examples.md at master · pyrochlore/obsidian-tracker
source: https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/FinanceTracker.md
author:
  - "[[denissok]]"
published:
created: 2025-12-07
description: A plugin tracks occurrences and numbers in your notes - obsidian-tracker/docs/Examples.md at master · pyrochlore/obsidian-tracker
tags:
  - clippings
---
[Skip to content](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/#start-of-content)

[Open in github.dev](https://github.dev/) [Open in a new github.dev tab](https://github.dev/) [Open in codespace](https://github.com/codespaces/new/pyrochlore/obsidian-tracker/tree/master?resume=1)

## Latest commit

[Updated examples with start and end dates so that](https://github.com/pyrochlore/obsidian-tracker/commit/37c2b60c8dcaab5418631e02a5d9f4c059e6243f)

[37c2b60](https://github.com/pyrochlore/obsidian-tracker/commit/37c2b60c8dcaab5418631e02a5d9f4c059e6243f) ·

## Finance Tracker

```
searchType: tag
searchTarget: finance
folder: diary
accum: true
endDate: 2021-01-31
line:
    title: Finance
    yAxisLabel: USD
    lineWidth: 4
```

```
searchType: tag
searchTarget: finance/bank1
folder: diary
accum: true
endDate: 2021-01-31
line:
    title: Bank1
    yAxisLabel: USD
```

```
searchType: tag
searchTarget: finance/bank2
folder: diary
accum: true
endDate: 2021-03-15
line:
    title: Bank2
    yAxisLabel: USD
    fillGap: true
```

Please also check those search targets in markdown files under folder 'diary'.