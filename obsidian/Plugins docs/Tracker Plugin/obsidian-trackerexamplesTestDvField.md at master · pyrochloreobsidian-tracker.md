---
title: obsidian-tracker/examples/TestDvField.md at master · pyrochlore/obsidian-tracker
source: https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestDvField.md
author:
  - "[[pyrochlore]]"
published:
created: 2025-12-07
description: A plugin tracks occurrences and numbers in your notes - obsidian-tracker/examples/TestDvField.md at master · pyrochlore/obsidian-tracker
tags:
  - clippings
---
[Open in github.dev](https://github.dev/) [Open in a new github.dev tab](https://github.dev/) [Open in codespace](https://github.com/codespaces/new/pyrochlore/obsidian-tracker/tree/master?resume=1)

[Fix using separator '\\,'](https://github.com/pyrochlore/obsidian-tracker/commit/59477f728dae2185f217efa97a252bac45bfe177)

[59477f7](https://github.com/pyrochlore/obsidian-tracker/commit/59477f728dae2185f217efa97a252bac45bfe177) ·

## Test dvField

Simple inline field

```
searchType: dvField
searchTarget: dataviewTarget
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
line:
    title: dvField
    lineColor: green
```

Field with a space

```
searchType: dvField
searchTarget: Make Progress
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
line:
    title: dvField
    lineColor: yellow
```

Field with a dash line

```
searchType: dvField
searchTarget: Make-Progress
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
line:
    title: dvField
    lineColor: red
```

Extract the first value from multiple values

```
searchType: dvField
searchTarget: dataviewTarget1[0]
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
line:
    title: dvField
    lineColor: blue
```

Multiple values separated by '/' (default)

```
searchType: dvField
searchTarget: dataviewTarget1[0], dataviewTarget1[1]
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
line:
    title: dvField
    lineColor: green, red
```

Multiple values seprated by 'comma'

```
searchType: dvField
searchTarget: dataviewTarget3[0], dataviewTarget3[1]
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
separator: 'comma'
line:
    title: dvField
    lineColor: green, red
```

Multiple values seprated by ','

```
searchType: dvField
searchTarget: dataviewTarget3[0], dataviewTarget3[1]
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
separator: '\,'
line:
    title: dvField
    lineColor: green, red
```

Use custom multiple value separator

```
searchType: dvField
searchTarget: dataviewTarget2[0], dataviewTarget2[1]
separator: '@'
folder: diary
startDate: 2021-01-01
endDate: 2021-01-31
line:
    title: dvField
    lineColor: green, red
```

Please also check those search targets in markdown files under folder 'diary'.