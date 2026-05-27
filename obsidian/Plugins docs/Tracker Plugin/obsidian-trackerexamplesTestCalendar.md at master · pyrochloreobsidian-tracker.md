---
title: obsidian-tracker/examples/TestCalendar.md at master · pyrochlore/obsidian-tracker
source: https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestCalendar.md
author:
  - "[[Lokesh-Bharath]]"
published:
created: 2025-12-07
description: A plugin tracks occurrences and numbers in your notes - obsidian-tracker/examples/TestCalendar.md at master · pyrochlore/obsidian-tracker
tags:
  - clippings
---
[Open in github.dev](https://github.dev/) [Open in a new github.dev tab](https://github.dev/) [Open in codespace](https://github.com/codespaces/new/pyrochlore/obsidian-tracker/tree/master?resume=1)

[Added a new field to allow increasing intensity of circle color with …](https://github.com/pyrochlore/obsidian-tracker/commit/2ee63575b5c99959cab93475534d5698b993ab66)

[2ee6357](https://github.com/pyrochlore/obsidian-tracker/commit/2ee63575b5c99959cab93475534d5698b993ab66) ·

## Test Calendar

## Single target

### Minimum setup

1. Use default colors only
2. Use parameter `datasetName` to set the title name

```
searchType: tag
searchTarget: meditation
datasetName: Meditation
folder: diary
endDate: 2021-01-31
month:
```

### Colorized

1. Click "<" to see data in previous month
2. Click ">" to see data in next month
3. Click "◦" to see data in current month

```
searchType: tag
searchTarget: exercise-pushup
datasetName: PushUp
folder: diary
endDate: 2021-01-31
month:
    startWeekOn: 'Sun'
    threshold: 40
    color: tomato
    headerMonthColor: orange
    dimNotInMonth: false
    todayRingColor: orange
    selectedRingColor: steelblue
    showSelectedValue: true
```

### Colorized

```
searchType: tag
searchTarget: meditation
datasetName: Meditation
folder: diary
endDate: 2021-01-31
month:
    startWeekOn: 'Sun'
    color: steelblue
    headerMonthColor: green
    selectedRingColor: orange
```

Use parameters `circleColorByValue`, `yMin`, and `yMax`, to color the circles based on the values

```
searchType: tag
searchTarget: exercise-pushup
datasetName: PushUp
folder: diary
endDate: 2021-01-31
month:
    startWeekOn:
    threshold: 10
    color: green
    headerMonthColor: orange
    dimNotInMonth: false
    todayRingColor: orange
    selectedRingColor: steelblue
    circleColorByValue: true
    yMin: 0
    yMax: 50
    showSelectedValue: true
```

Use parameter circleColorByStreak to increase color intesity with streaklength. This can also be used along with thresholdtype parameter.

```
searchType: tag
searchTarget: exercise-pushup
datasetName: PushUp
folder: diary
endDate: 2021-01-31
month:
    startWeekOn:
    threshold: 30
    color: red
    dimNotInMonth: false
    circleColorByStreak: true
```

Use parameters threshold and thresholdType - "LessThan" to color the circles

```
searchType: tag
searchTarget: exercise-pushup
datasetName: PushUp
folder: diary
endDate: 2021-01-31
month:
    startWeekOn:
    threshold: 40
    thresholdType: LessThan
    color: green
    headerMonthColor: orange
    dimNotInMonth: false
    todayRingColor: orange
    selectedRingColor: steelblue
    showSelectedValue: true
```

```
searchType: tag
searchTarget: exercise-pushup
summary:
    template: "minDate: {{minDate()}}\nminValue: {{min()}}\nmaxDate: {{maxDate()}}\nmaxValue: {{max()}}"
```

### initMonth

Specify the initial month in YYYY-MM format

```
searchType: tag
searchTarget: exercise-pushup
datasetName: PushUp
folder: diary
month:
    startWeekOn:
    threshold: 40
    color: green
    headerMonthColor: orange
    dimNotInMonth: false
    todayRingColor: orange
    selectedRingColor: steelblue
    circleColorByValue: true
    showSelectedValue: true
    initMonth: 2021-01
```

Specify the initial month by relative date

```
searchType: tag
searchTarget: exercise-pushup
datasetName: PushUp
folder: diary
month:
    startWeekOn:
    threshold: 40
    color: green
    headerMonthColor: orange
    dimNotInMonth: false
    todayRingColor: orange
    selectedRingColor: steelblue
    circleColorByValue: true
    showSelectedValue: true
    initMonth: -47M
```

## Multiple targets

1. Use parameter `datasetName` to specify the name of each dataset
2. Use parameter `dataset` to include dataset we are going to view
3. Use parameter `threshold` to specify the level of achievement (affect the streaks)
4. Click the datasetName label in month view to change the target dataset

```
searchType: tag
searchTarget: exercise-pushup, meditation
datasetName: PushUp, Meditation
folder: diary
endDate: 2021-01-31
month:
    dataset: 0, 1
    startWeekOn: 'Sun'
    threshold: 40, 0
    color: green
    headerMonthColor: orange
    dimNotInMonth: false
    todayRingColor: orange
    selectedRingColor: steelblue
    circleColorByValue: true
    showSelectedValue: true
```

## Annotations

One target at a time

```
searchType: tag
searchTarget: exercise-pushup, meditation
datasetName: PushUp, Meditation
folder: diary
endDate: 2021-01-31
month:
    mode: annotation
    startWeekOn: 'Sun'
    threshold: 40, 0
    color: green
    headerMonthColor: orange
    dimNotInMonth: false
    annotation: 💪,🧘‍♂️
    showAnnotationOfAllTargets: false
```

All targets

```
searchType: tag
searchTarget: exercise-pushup, meditation
datasetName: PushUp, Meditation
folder: diary
endDate: 2021-01-31
month:
    mode: annotation
    startWeekOn: 'Sun'
    threshold: 40, 0
    color: green
    headerMonthColor: orange
    dimNotInMonth: false
    annotation: 💪,🧘‍♂️
    showAnnotationOfAllTargets: true
```

Please also check those search targets in markdown files under folder 'diary'.

## Scaling

fitPanelWidth: true Click forward backward months and verify it stays scaled

```
searchType: tag
searchTarget: meditation
datasetName: Meditation
fitPanelWidth: true
folder: diary
endDate: 2021-01-31
month:
```