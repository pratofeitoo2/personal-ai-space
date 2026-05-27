---
title: Polar Area Chart
author:
  - "[[Charts Plugin]]"
created: 2025-12-02
description: Modifiers - Charts Plugin
tags:
  - clippings
---
[Charts Plugin](https://charts.phib.ro/Meta/Charts/Charts+Documentation)

## Example

```yaml
\`\`\`chart
type: polarArea
labels: [Monday,Tuesday,Wednesday,Thursday,Friday]
series:
    - title: Title 1
    data: [1,2,3,4,5]
    - title: Title 2
    data: [5,4,3,2,1]
labelColors: true
width: 40%
\`\`\`
```

The above example Code will render a *Polar Area Chart*, a `width` Modifier is already added, since this Chart would be way to big otherwise. The Property `labelColors` is also set to `true`, which is the desired behaviour most of the time.  
![Polar Area Chart Example Image](https://github.com/phibr0/obsidian-charts/raw/master/images/polarareachart.png)

## Advanced

*See [Modifiers](https://charts.phib.ro/Meta/Charts/Modifiers) for advanced configuration.*

Polar Area Chart

Interactive graph

Example

Advanced