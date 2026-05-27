---
title: Dataview Integration
author:
  - "[[Charts Plugin]]"
created: 2025-12-02
description: Modifiers - Charts Plugin
tags:
  - clippings
---
[Charts Plugin](https://charts.phib.ro/Meta/Charts/Charts+Documentation)

If you want to use this Plugin in combination with Plugins like Dataview, I recommend using the API. When this Plugin is enabled, you can render a Chart using the following:

```js
window.renderChart(data, element);
```

There are some full Examples:

## Get data from current page



```dataviewjs
const data = dv.current()

const chartData = {
    type: 'bar',
    data: {
        labels: [data.test],
        datasets: [{
            label: 'Grades',
            data: [data.mark],
            backgroundColor: [
                'rgba(255, 99, 132, 0.2)'
            ],
            borderColor: [
                'rgba(255, 99, 132, 1)'
            ],
            borderWidth: 1
        }]
    }
}

window.renderChart(chartData, this.container);

```

or you can use with `charts` Codeblock

```md
\`\`\`dataviewjs
const data = dv.current()

dv.paragraph(\`\\`\\`\\`chart
    type: bar
    labels: [${data.test}]
    series:
    - title: Grades
      data: [${data.mark}]
\\`\\`\\`\`)
\`\`\`
```

## Get data from multi-pages

```md
\`\`\`dataviewjs
const pages = dv.pages('#test')
const testNames = pages.map(p => p.file.name).values
const testMarks = pages.map(p => p.mark).values

const chartData = {
    type: 'bar',
    data: {
        labels: testNames,
        datasets: [{
            label: 'Mark',
            data: testMarks,
            backgroundColor: [
                'rgba(255, 99, 132, 0.2)'
            ],
            borderColor: [
                'rgba(255, 99, 132, 1)'
            ],
            borderWidth: 1,
        }]
    }
}

window.renderChart(chartData, this.container)
\`\`\`
```

The data is the standard [Chart.js](https://www.chartjs.org/docs/latest/) data payload, you can use everything it supports in there.

Warning

Dataviewjs needs to be enabled for this to work properly.

Dataview Integration

Interactive graph

Get data from current page

Get data from multi-pages