# Charts Cheat-sheets

This single document contains four concise cheat-sheets in Markdown format:

- Obsidian Tracker (pyrochlore/obsidian-tracker)
- Obsidian Charts plugin (chart codeblocks in Obsidian)
- Chart.js (official library — common options and examples)
- Mapping: Chart.js options ↔ Obsidian Charts YAML

---

**Notes**
- These cheat-sheets are condensed from the official docs and repository documentation.
- Use the examples as templates; adapt `searchType`, `searchTarget`, and chart options to your data.


## 1) Obsidian Tracker Cheat-sheet

Purpose: collect occurrences and numeric values from notes and render as charts (line, bar, pie, month, bullet) or text summaries.

Basic usage

- Place a fenced code block with language `tracker` (YAML-like key: value pairs) in an Obsidian note, then view in Preview mode.
- Minimum required parameters: `searchType`, `searchTarget`, and at least one output container (`line`, `bar`, `summary`, `bullet`, `month`, or `pie`).

Quick template

```yaml
```tracker
searchType: tag
searchTarget: meditation
line:
  title: "Meditation"
  lineColor: '#69b3a2'
```
```

Primary root parameters

- `searchType` (required): tag | frontmatter | wiki | text | dvField | table | fileMeta | task
- `searchTarget` (required): target(s) to match (comma-separated for multiple targets)
- `folder`: root path to search (default: vault root)
- `file`, `specifiedFilesOnly`, `fileContainsLinkedFiles`, `fileMultiplierAfterLink`
- `dateFormat` (default `YYYY-MM-DD`) — uses Moment.js format or `iso-8601`
- `startDate`, `endDate` (accept relative dates)
- `datasetName` (names for datasets)
- `separator` (for multi-value targets inside a field)
- `constValue`, `ignoreAttachedValue`, `ignoreZeroValue`, `accum`, `stack`, `penalty`, `valueShift`
- `fitPanelWidth`, `aspectRatio`, `margin`, `fixedScale`

Output containers

- `line`, `bar` — charts with many per-chart options (colors, axes labels, ticks, legend, showLegend)
- `summary` — text output using `template` with expressions
- `bullet` — bullet (gauge-like) chart
- `month` — month view (circle/annotation) with thresholds and streaks
- `pie` — pie/donut chart

Common `line` / `bar` options

- `title`, `xAxisLabel`, `yAxisLabel`, `xAxisTickInterval`, `yAxisTickInterval`
- `yMin`, `yMax`, `reverseYAxis`
- `allowInspectData` (hover values), `showLegend`, `legendPosition`, `legendOrientation`
- `lineColor`, `lineWidth`, `showPoint`, `pointSize`, `fillGap`
- `barColor`, `xAxisPadding`

Month view highlights (`month`)

- `mode`: circle | annotation
- `threshold` and `thresholdType` (GreaterThan | LessThan)
- `showCircle`, `showStreak`, `initMonth`, `showAnnotation`, `showTodayRing`
- color controls: `circleColor`, `circleColorByValue`, `circleColorByStreak`

Data conversion & advanced options

- `textValueMap`: convert text/emoji values to numbers (supports regex keys)
- `shiftOnlyValueLargerThan`: threshold for `valueShift` application
- `dateFormatPrefix` / `dateFormatSuffix`: regex patterns for date extraction
- `specifiedFilesOnly`: true to only search specified files
- `fileContainsLinkedFiles`: include files with links
- `fileMultiplierAfterLink`: multiply values after links

Expressions (1.9.0+)

- Use `{{...}}` to embed expressions in `summary.template`, `bullet.value`, `pie.data` or `pie.label`.
- Functions: `dataset(index)`, `sum(dataset)`, `average(dataset)`, `maxStreak(dataset)`, `first()`, `last()`, `min()`, `max()`, `normalize()`, `setMissingValues()` etc.
- Operators supported: `+ - * / %`.
- Example: `template: "Total: {{sum()::0.2f}}"` (formatting using printf style)
- `first()` — returns first value in dataset
- `last()` — returns last value in dataset

Search types quick reference

- `tag`: matches `#tag` or `#tag:value` (value after colon, no space)
- `frontmatter`: `key: value` in YAML frontmatter
- `wiki`: wiki links (`[[Page]]`)
- `text`: plain text or regex (wrap regex in single quotes; use named group `?<value>` to extract a value)
- `dvField`: Dataview inline fields (`key:: value`)
- `table`: read a table in a file using `filePath[tableIndex][colIndex]` syntax
- `fileMeta`: `cDate`, `mDate`, `size`, `numWords`, `numChars`, `numSentences`
- `task`: supports `task`, `task.all`, `task.done`, `task.notdone`

Examples

- Track occurrences of `#meditation`:
```yaml
```tracker
searchType: tag
searchTarget: meditation
bar:
  title: Meditation
```
```

- Track weight from frontmatter:
```yaml
```tracker
searchType: frontmatter
searchTarget: weight
line:
  title: Weight
```
```

- Use text regex to extract steps:
```yaml
```tracker
searchType: text
searchTarget: 'walked\s+(?<value>[0-9]+)\s+steps'
line:
  title: Steps
```
```

Where to find more

- Examples folder in the plugin repo: `examples/` — contains many full tracker blocks and sample data.


## 2) Obsidian Charts Plugin Cheat-sheet

Purpose: create charts in Obsidian using a fenced `chart` codeblock with YAML properties. (Plugin renders chart using Chart.js behind the scenes.)

Basic template

```yaml
```chart
type: "line"
labels: ["2025-11-01","2025-11-02"]
series:
  - title: "Series A"
    data: [10, 12]
  - title: "Series B"
    data: [7, 9]
```
```

Notes

- Use YAML-style indentation carefully in Obsidian; pasting may alter indentation.
- `title` is optional but recommended.
- The graphical Chart Creator (Command Palette or hotkey) can help build basic charts.
- The plugin integrates Chart.js, so any Chart.js option can be passed via `options`.

Common `type` values

- `line`, `bar`, `pie`, `doughnut`, `radar`, `polarArea`, `bubble`, `scatter`, `mixed`, `sankey`

Key fields

- `type`: chart type
- `labels`: array of labels for X axis (not used for sankey)
- `series`: array of series objects with `title` and `data`
- `options` (optional advanced Chart.js options may be placed under `options:` following Chart.js config)

Obsidian Charts-specific options

- `width`: CSS width (e.g., "60%", "300px", "100%")
- `legend`: true/false to show/hide legend
- `legendPosition`: top, left, bottom, right
- `legendOrientation`: horizontal, vertical
- `fill`: true for area charts (fills under line)
- `tension`: number (0-1) controls curve smoothness for line charts
- `transparency`: float [0, 1] for chart opacity
- `fitPanelWidth`: true to fit container width
- `time`: format for time/date axes
- `aspectRatio`: number for width:height ratio

Axis control options

- `xTitle` / `yTitle`: labels for x and y axes
- `indexAxis`: "x" or "y" — switch to horizontal bar chart
- `beginAtZero`: true/false — start axis at zero
- `xReverse` / `yReverse`: true/false — reverse axis direction
- `xAxisTickInterval` / `yAxisTickInterval`: number of pixels between ticks
- `xAxisTickLabelFormat` / `yAxisTickLabelFormat`: format for tick labels (supports regex patterns)
- `xAxisPadding`: padding on x-axis

Data modifiers

- `spanGaps`: true to connect points with missing data
- `bestFit`: true to display trendline
- `bestFitTitle`: custom label for trendline
- `stacked`: true to stack datasets (for bar and line charts)

Theming & Colors

- Theme color support: plugin can use Obsidian UI/theme colors
- Per-series `backgroundColor` and `borderColor` in series definition
- Image export: configurable format (PNG, JPG) and quality

### Obsidian Charts Plugin — Examples

1) Per-series colors and mixed types
```yaml
```chart
type: "bar"
labels: ["Mon","Tue","Wed"]
series:
  - title: "Sales"
    data: [12, 19, 3]
```
```

- Mixed chart (two types)
```yaml
```chart
labels: ["Q1","Q2","Q3"]
series:
  - title: "Revenue"
    data: [100,120,140]
    type: "bar"
  - title: "Growth"
    data: [5,7,9]
    type: "line"
```
```

Advanced: include Chart.js `options`

- You can often include `options:` in the YAML to pass through Chart.js configuration (scales, plugins, animation settings). The exact support depends on the plugin implementation and YAML parsing. Example:

```yaml
```chart
type: "line"
labels: ["Jan","Feb"]
series:
  - title: "A"
    data: [1,2]
options:
  plugins:
    legend:
      display: true
```
```


## 3) Chart.js Cheat-sheet (common config)

Core usage (browser)

- Include Chart.js via CDN or npm and create a canvas element.

Basic JS example

```js
const ctx = document.getElementById('myChart').getContext('2d');
const myChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Jan','Feb','Mar'],
    datasets: [{
      label: 'Series A',
      data: [10, 20, 15],
      fill: false,
      borderColor: 'rgb(75, 192, 192)'
    }]
  },
  options: {
    responsive: true,
    plugins: { legend: { display: true }},
    scales: { x: { display: true }, y: { beginAtZero: true }}
  }
});
```

Important options

- `type`: 'line' | 'bar' | 'pie' | 'doughnut' | 'radar' | 'polarArea' | 'bubble' | 'scatter'
- `data.labels`: x-axis labels
- `data.datasets`: array of datasets (label, data, backgroundColor, borderColor, borderWidth, yAxisID)
- `options.responsive`: true/false
- `options.maintainAspectRatio` / `aspectRatio`
- `options.plugins.legend`: `display`, `position`, `labels` styling
- `options.plugins.tooltip`: `mode`, `callbacks` for custom labels
- `options.scales`: configure axes (`x`, `y`, multiple axes with IDs)
- `animations`: per-property animation settings (duration, easing)

Scale & axes examples

- Linear y-axis with min/max and ticks formatting
```js
options: {
  scales: {
    y: {
      min: 0,
      max: 100,
      ticks: { callback: v => v + ' units' }
    }
  }
}
```

Multiple datasets & axes

- Assign `yAxisID` to datasets and define axes in `options.scales`.

Decimation & performance

- Use `parsing: false` when providing pre-parsed data arrays of {x,y} objects.
- Use decimation plugin or `decimation` option to sample large datasets.
- Tree-shaking: import only the controllers/elements you need if using ESM build.

Plugins

- Chart.js supports plugins (built-in and third-party) for annotations, zoom, datalabels.
- Configure under `options.plugins.<pluginId>`.

Formatting callbacks

- Tooltips and ticks support callback functions for custom text formatting.


## 4) Mapping: Chart.js options ↔ Obsidian Charts YAML

Overview: Obsidian's Charts plugin accepts a simplified YAML code block that maps conceptually to Chart.js `type`, `data.labels` and `data.datasets`. For advanced `options`, the plugin may accept an `options:` object passed as YAML which maps directly to Chart.js `options`.

Common mappings

- `type` → Chart.js `type`
- `labels` → Chart.js `data.labels`
- `series` (array)
  - `title` → dataset `label`
  - `data` → dataset `data`
  - `type` (optional per-series) → dataset `type` (for mixed charts)
  - `backgroundColor`, `borderColor` may be set in `series` or via `options`
- Obsidian `options:` → Chart.js `options` (scales/plugins/animations)

Example: set y-axis min/max via YAML

```yaml
```chart
type: "line"
labels: ["Jan","Feb","Mar"]
series:
  - title: "A"
    data: [10,20,15]
options:
  scales:
    y:
      min: 0
      max: 30
```
```

Limitations & tips

- Obsidian YAML indentation must be exact; use the graphical creator if unsure.
- Some plugin implementations may sanitize or limit which Chart.js options are allowed — test complex `options` blocks.
- For very large datasets prefer pre-parsed x/y arrays and set `parsing: false` if the plugin exposes that option.

---

## Additional Examples

Below are several ready-to-copy examples grouped by tool. Watch indentation when pasting into Obsidian; use Preview mode to render Tracker blocks.

### Obsidian Tracker — Examples

1) Weight tracker (frontmatter values)

```yaml
```tracker
searchType: frontmatter
searchTarget: weight
line:
  title: "Weight (kg)"
  yAxisLabel: "kg"
```
```

Notes: Add `weight: 70.2` in your note frontmatter to record a measurement.

2) Blood pressure (multiple values per tag)

In your daily note content: `#blood-pressure:180/120`

Tracker block:

```yaml
```tracker
searchType: tag
searchTarget: blood-pressure[0], blood-pressure[1]
line:
  title: "Blood Pressure"
  lineColor: '#e76f51, #2a9d8f'
  yAxisLabel: 'mmHg'
```
```

3) Finance transfers using nested tag path

Note content example: `#finance/bank1/transfer:100USD`

```yaml
```tracker
searchType: tag
searchTarget: finance/bank1/transfer
line:
  title: "Transfers"
  yAxisLabel: "USD"
```
```

4) Regex extract (steps)

```yaml
```tracker
searchType: text
searchTarget: 'walked\s+(?<value>[0-9]+)\s+steps'
line:
  title: "Steps"
  lineColor: '#4cc9f0'
```
```

5) Dataview inline field (dvField)

Note: Use `steps:: 1234` in a note.

```yaml
```tracker
searchType: dvField
searchTarget: steps
line:
  title: "Steps (dvField)"
```
```

6) Month view with thresholds & streaks (calendar)

```yaml
```tracker
searchType: tag
searchTarget: study
month:
  mode: circle
  threshold: 1
  thresholdType: GreaterThan
  showStreak: true
  showTodayRing: true
```
```

7) Table example (read specific table columns)

```yaml
```tracker
searchType: table
searchTarget: examples/data/Tables.md[0][0], examples/data/Tables.md[0][1]
line:
  title: "Table data example"
```
```

8) Text-to-value mapping with textValueMap

```yaml
```tracker
searchType: text
searchTarget: 'mood: (\w+)'
textValueMap:
  happy: 5
  good: 4
  neutral: 3
  bad: 2
  sad: 1
bar:
  title: "Daily Mood"
```
```

9) Tracker with specified files only

```yaml
```tracker
searchType: frontmatter
searchTarget: weight
file: "Health/Daily.md,Health/Weekly.md"
specifiedFilesOnly: true
line:
  title: "Weight Tracking"
  showPoint: true
```
```

10) Calendar with streak intensity and today ring

```yaml
```tracker
searchType: tag
searchTarget: exercise
folder: "Health"
month:
  mode: circle
  threshold: 1
  thresholdType: GreaterThan
  showStreak: true
  circleColorByStreak: true
  showTodayRing: true
  initMonth: 2025-11
```
```

11) Expression example with first() and last()

```yaml
```tracker
searchType: frontmatter
searchTarget: steps
summary:
  template: "First: {{first()::0f}} | Last: {{last()::0f}} | Total: {{sum()::0f}} steps"
```
```

12) Stacked bar chart with multiple datasets

```yaml
```tracker
searchType: frontmatter
searchTarget: work, personal, hobby
stack: true
bar:
  title: "Time Distribution"
  barColor: ['#e74c3c', '#3498db', '#2ecc71']
```
```


### Obsidian Charts Plugin — Examples

1) Per-series colors and mixed types

```yaml
```chart
labels: ["Jan","Feb","Mar"]
series:
  - title: "Revenue"
    data: [100,120,140]
    type: "bar"
    backgroundColor: '#264653'
  - title: "Growth"
    data: [5,7,9]
    type: "line"
    borderColor: '#e76f51'
    fill: false
options:
  plugins:
    legend:
      position: top
```
```

2) Donut chart with inner radius and labels

```yaml
```chart
type: "doughnut"
labels: ["A","B","C"]
series:
  - title: "Share"
    data: [0.5,0.3,0.2]
options:
  cutout: '50%'
  plugins:
    legend:
      position: right
```
```

3) Tooltip formatting via options (if supported by plugin)

```yaml
```chart
type: "bar"
labels: ["Q1","Q2"]
series:
  - title: "Sales"
    data: [12000, 15000]
options:
  plugins:
    tooltip:
      callbacks:
        label: "function(context) { return '$' + context.parsed.y.toLocaleString(); }"
```
```


### Obsidian Charts Plugin — Obsidian-Specific Examples

1) Responsive width and aspect ratio

```yaml
```chart
type: "line"
width: "80%"
fitPanelWidth: true
aspectRatio: 2
labels: ["Jan","Feb","Mar","Apr"]
series:
  - title: "Revenue"
    data: [100, 120, 140, 160]
```
```

2) Axis control with titles and reversed axes

```yaml
```chart
type: "bar"
indexAxis: "y"
xTitle: "Sales ($)"
yTitle: "Regions"
labels: ["North","South","East","West"]
series:
  - title: "Q1"
    data: [50, 40, 60, 35]
xReverse: false
beginAtZero: true
```
```

3) Stacked bar chart

```yaml
```chart
type: "bar"
stacked: true
labels: ["Jan","Feb","Mar"]
series:
  - title: "Product A"
    data: [30, 40, 35]
  - title: "Product B"
    data: [20, 30, 25]
  - title: "Product C"
    data: [10, 15, 12]
legend: true
legendPosition: top
```
```

4) Line chart with tension and spanGaps

```yaml
```chart
type: "line"
tension: 0.4
spanGaps: true
labels: ["Week 1","Week 2","Week 3","Week 4","Week 5"]
series:
  - title: "Completion %"
    data: [25, 40, null, 60, 75]
yTitle: "Percentage (%)"
beginAtZero: true
```
```

5) Chart with trendline (bestFit)

```yaml
```chart
type: "scatter"
bestFit: true
bestFitTitle: "Trend"
series:
  - title: "Data Points"
    data: [{x: 1, y: 10}, {x: 2, y: 15}, {x: 3, y: 12}, {x: 4, y: 20}]
xTitle: "Time"
yTitle: "Value"
```
```

6) Custom axis tick intervals and labels

```yaml
```chart
type: "line"
xAxisTickInterval: 50
yAxisTickInterval: 100
labels: ["0","50","100","150","200"]
series:
  - title: "Performance"
    data: [10, 50, 120, 180, 220]
xTitle: "Distance (m)"
yTitle: "Time (s)"
```
```

7) Semi-transparent chart with custom width

```yaml
```chart
type: "pie"
width: "50%"
transparency: 0.8
labels: ["Red","Blue","Green","Yellow"]
series:
  - title: "Distribution"
    data: [30, 25, 20, 25]
legend: true
legendPosition: right
```
```


## 3) Obsidian Charts + DataviewJS Integration

Purpose: Create dynamic charts that query your vault using DataviewJS, then render with Obsidian Charts plugin.

DataviewJS allows you to query notes and generate chart-ready data. This is more powerful than static charts as it can pull real-time data from your vault.

Basic pattern

```js
```dataviewjs
// Query all pages with a weight property
const pages = dv.pages('#health').where(p => p.weight);

// Extract dates and values
const labels = pages.map(p => p.file.frontmatter.date);
const data = pages.map(p => p.weight);

// Return chart data (rendered by Obsidian Charts plugin)
dv.el('div', `
\`\`\`chart
type: line
labels: ${JSON.stringify(labels)}
series:
  - title: Weight
    data: ${JSON.stringify(data)}
yTitle: Weight (kg)
\`\`\`
`);
```
```

Key benefits

- Query data dynamically with DQL filters and conditions
- Combine data from multiple files or tags
- Calculate derived metrics (sums, averages, counts)
- Refresh automatically when notes change

Common DQL queries for charts

- `dv.pages('#tag')` — get pages with a tag
- `.where(p => p.property > value)` — filter by condition
- `.map(p => p.property)` — extract specific field
- `.groupBy(p => p.category)` — group by field
- `.sort(p => p.date, 'desc')` — sort results

Advanced: dynamic dashboard example

```js
```dataviewjs
const data = dv.pages('tag: #expense')
  .groupBy(p => p.category)
  .map(g => ({ 
    category: g.key, 
    total: g.rows.reduce((sum, row) => sum + row.amount, 0) 
  }));

dv.el('div', `
\`\`\`chart
type: pie
labels: ${JSON.stringify(data.map(d => d.category))}
series:
  - title: Expenses by Category
    data: ${JSON.stringify(data.map(d => d.total))}
legend: true
\`\`\`
`);
```
```

---

## 4) Chart.js — Core Concepts

### Chart.js — Core Concepts

Chart.js uses a hierarchical options system with multiple levels:
- **Chart level:** applies to entire chart
- **Dataset level:** applies to specific dataset (e.g., individual line color)
- **Element level:** configure points, bars, arcs
- **Scale level:** manipulate axes (x, y, y2, etc.)
- **Plugin level:** configuration for plugins (legend, tooltip, annotation)
- **Animation level:** control animations at various scopes

**Global vs. Local Options**

Set global defaults for all charts:
```js
Chart.defaults.interaction.mode = 'nearest';
Chart.defaults.font.size = 12;
```

Override with chart-specific options:
```js
new Chart(ctx, {
  type: 'line',
  data: data,
  options: { interaction: { mode: 'index' } }  // overrides global
});
```

**Common Root-Level Options**

- `responsive` (true/false) — auto-resize to container
- `maintainAspectRatio` (true/false) — preserve aspect ratio when responsive
- `aspectRatio` (number) — ratio when maintainAspectRatio is true
- `layout` — padding and margin settings
- `interaction.mode` — how tooltips interact (nearest, index, point, dataset, x, y)
- `animation` — animation timing and easing
- `animation.duration` (ms), `animation.easing` (easeInOutQuart, linear, etc.)

**Scriptable & Indexable Options**

Many options accept functions (scriptable) or arrays (indexable):

Scriptable (function based on context):
```js
options: {
  plugins: {
    legend: {
      labels: {
        color: function(ctx) { return ctx.dataset.label === 'Good' ? 'green' : 'red'; }
      }
    }
  }
}
```

Indexable (array with auto-loop):
```js
datasets: [{
  data: [10, 20, 30],
  backgroundColor: ['red', 'green', 'blue']  // cycles if more data points than colors
}]
```

**Font & Text Styling**

Standardized font options across chart:
```js
options: {
  font: {
    family: 'Helvetica, Arial',
    size: 14,
    style: 'normal',  // 'italic', 'oblique', 'normal'
    weight: 'bold'
  },
  plugins: {
    legend: {
      labels: {
        font: { size: 16, weight: 'bold' }  // overrides global font
      }
    }
  }
}
```

**Common Color & Border Options**

Standardized across datasets:
- `backgroundColor` — fill color for bars, pie slices, etc.
- `borderColor` — outline color
- `borderWidth` (number)
- `borderRadius` (number) — rounded corners on bars
- `borderDash` ([skip, space]) — dashed lines
- `fill` (true/false) — fill area under line

### Chart.js — Examples

1) Multiple axes (left and right)

```js
const ctx = document.getElementById('multi').getContext('2d');
const chart = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Jan','Feb','Mar'],
    datasets: [
      { label: 'Revenue', data: [100,150,130], yAxisID: 'y' },
      { label: 'Conversion %', data: [2.4, 3.1, 2.9], type: 'line', yAxisID: 'yRight', borderColor: 'red', fill: false }
    ]
  },
  options: {
    scales: {
      y: { type: 'linear', position: 'left', beginAtZero: true },
      yRight: { type: 'linear', position: 'right', beginAtZero: true }
    }
  }
});
```

2) Scatter & Bubble

Scatter:
```js
new Chart(ctx, { type: 'scatter', data: { datasets: [{ label: 'Scatter', data: [{x:1,y:2},{x:2,y:3}] }] } });
```

Bubble:
```js
new Chart(ctx, { type: 'bubble', data: { datasets: [{ label: 'Bubble', data: [{x:10,y:20,r:5}] }] } });
```

3) Decimation for large datasets

```js
// enable the decimation plugin in options
options: {
  plugins: {
    decimation: { enabled: true, algorithm: 'lttb', samples: 1000 }
  }
}
```

4) Tooltip callback example

```js
options: {
  plugins: {
    tooltip: {
      callbacks: {
        label: function(ctx) { return ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString(); }
      }
    }
  }
}
```

5) Interaction modes and tooltip behavior

```js
// 'nearest' — closest single data point
options: { interaction: { mode: 'nearest' } }

// 'index' — all points at same x-axis value
options: { interaction: { mode: 'index' } }

// 'dataset' — all points in same dataset
options: { interaction: { mode: 'dataset' } }

// 'point' — only if cursor directly over point
options: { interaction: { mode: 'point' } }

// 'x' — all points at same x position
options: { interaction: { mode: 'x' } }

// 'y' — all points at same y position
options: { interaction: { mode: 'y' } }
```

6) Responsive layout with padding and aspect ratio

```js
options: {
  responsive: true,
  maintainAspectRatio: true,
  aspectRatio: 2,  // width:height ratio
  layout: {
    padding: {
      left: 20,
      right: 20,
      top: 10,
      bottom: 10
    }
  }
}
```

7) Animation configuration

```js
options: {
  animation: {
    duration: 750,      // ms
    easing: 'easeInOutQuart',  // easing function
    delay: function(ctx) { return ctx.dataIndex * 50; }  // stagger animation
  }
}
```

8) Per-dataset styling (bar chart with individual colors and borders)

```js
datasets: [{
  label: 'Sales',
  data: [12, 19, 3, 5],
  backgroundColor: ['#264653', '#2a9d8f', '#e9c46a', '#f4a261'],
  borderColor: '#333',
  borderWidth: 2,
  borderRadius: 5,
  hoverBackgroundColor: '#ff6b6b'
}]
```

9) Line chart with gradient and fill

```js
options: {
  scales: {
    y: { beginAtZero: true, min: 0, max: 100 }
  },
  plugins: {
    filler: {
      propagate: true
    }
  }
},
data: {
  datasets: [{
    label: 'Progress',
    data: [10, 25, 40, 65, 80],
    borderColor: '#264653',
    borderWidth: 3,
    fill: true,
    backgroundColor: 'rgba(38, 70, 83, 0.1)',
    tension: 0.4  // curve smoothness
  }]
}
```

10) Dashed borders and custom styling

```js
datasets: [{
  label: 'Target',
  data: [50, 50, 50],
  borderColor: '#e76f51',
  borderWidth: 2,
  borderDash: [5, 5],      // 5px dash, 5px gap
  fill: false,
  pointStyle: 'triangle',
  pointRadius: 6
}]
```


### Mapping Examples (Chart.js ↔ Obsidian YAML)

1) Map dataset `yAxisID` and scales

Obsidian YAML (per-series `type` and custom `yAxisID` via options):

```yaml
```chart
labels: ["Jan","Feb"]
series:
  - title: "A"
    data: [10,20]
    type: "bar"
  - title: "B"
    data: [1.5,2.2]
    type: "line"
options:
  scales:
    y:
      beginAtZero: true
    yRight:
      position: 'right'
  datasets:
    1:
      yAxisID: 'yRight'
```
```

Note: plugin support for per-dataset options may vary; if unsupported, use Chart.js options directly when the plugin allows raw `options`.


---

## 5) Advanced Features & Tips

### Image Export

Both Obsidian Charts and Chart.js support exporting charts as images:

Obsidian Charts
- Right-click on chart and select "Export as image"
- Configure format (PNG, JPG) and quality in plugin settings
- Supports custom dimensions

Chart.js
```js
const canvas = document.querySelector('canvas');
const image = canvas.toDataURL('image/png');
const link = document.createElement('a');
link.href = image;
link.download = 'chart.png';
link.click();
```

### Performance Tips

- **Large datasets:** Use decimation plugin for thousands of data points
- **Multiple series:** Limit to 5-10 series per chart for readability
- **Animation:** Disable animations (`animation: { duration: 0 }`) on dashboards with many charts
- **Responsive:** Set `maintainAspectRatio: false` for fixed-size containers

### Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| Chart not rendering | Ensure YAML indentation is correct (2 spaces) |
| Data not updating | For Obsidian Charts: refresh preview; For Tracker: check file watchers |
| Legend overlapping chart | Use `legendPosition: 'top'` or `'bottom'` |
| Axes look wrong | Set `beginAtZero: true` and explicit `min`/`max` values |
| Tooltip not showing | Check `interaction.mode` setting; ensure data is numeric |

### Theme Integration

Obsidian Charts can use your vault's theme colors:

```yaml
```chart
type: bar
labels: ["A","B","C"]
series:
  - title: Data
    data: [10, 20, 15]
# Leave backgroundColor empty to use theme colors
```
```

### Combining Tracker + Charts

Common pattern: Use Tracker for data collection, Charts plugin for visualization:

1. Tracker collects data from notes
2. Charts plugin reads Tracker summary output
3. Or use DataviewJS to query tracked data and generate charts

---

References

- Chart.js docs: https://www.chartjs.org/docs/latest/
- Obsidian Charts plugin basics: https://charts.phib.ro/Meta/Charts/Basics
- Obsidian Tracker (pyrochlore): https://github.com/pyrochlore/obsidian-tracker

---

Generated: 2025-11-27
Updated: 2025-11-27 (comprehensive update)

**Latest additions:**
- Chart.js core concepts (configuration structure, global options, scriptable/indexable options)
- Obsidian Charts plugin: axis controls, data modifiers, stacked charts, responsive options
- 7 new Obsidian Charts examples (width, stacking, trendlines, transparency, etc.)
- Obsidian Tracker: advanced parameters (textValueMap, specifiedFilesOnly, colorByStreak, showTodayRing)
- 6 new Tracker examples (text mapping, specified files, calendars, expressions)
- Obsidian Charts + DataviewJS integration for dynamic charts
- Advanced features section: export, performance tips, troubleshooting, theme integration
