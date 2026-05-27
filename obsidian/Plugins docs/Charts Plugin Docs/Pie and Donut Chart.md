---
title: Pie and Donut Chart
author:
  - "[[Charts Plugin]]"
created: 2025-12-02
description: Modifiers - Charts Plugin
tags:
  - clippings
---
[Charts Plugin](https://charts.phib.ro/Meta/Charts/Charts+Documentation)

The Doughnut and Pie Chart work in the same way.

## Example

### Pie Chart

```yaml
\`\`\`chart
    type: pie
    labels: [Monday,Tuesday,Wednesday,Thursday,Friday]
    series:
        - title: Title 1
        data: [1,2,3,4,5]
        - title: Title 2
        data: [5,4,3,2,1]
    width: 40%
    labelColors: true
\`\`\`
```

The above example Code will render a *Pie Chart*, a `width` Modifier is already added, since this Chart would be way to big otherwise. The Property `labelColors` is also set to `true`, which is the desired behaviour most of the time.

![Pie Chart Example Image](https://github.com/phibr0/obsidian-charts/raw/master/images/piechart.png)

### Doughnut Chart

```yaml
\`\`\`chart
    type: doughnut
    labels: [Monday,Tuesday,Wednesday,Thursday,Friday]
    series:
        - title: Title 1
        data: [1,2,3,4,5]
        - title: Title 2
        data: [5,4,3,2,1]
    width: 40%
    labelColors: true
\`\`\`
```

![Doughnut Chart Example Image](https://github.com/phibr0/obsidian-charts/raw/master/images/doughnutchart.png)

## Advanced

*See [Modifiers](https://charts.phib.ro/Meta/Charts/Modifiers) for advanced configuration.*

Pie and Donut Chart

Interactive graph

Example

Pie Chart

Doughnut Chart

Advanced