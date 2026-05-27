---
title: Obsidian Charts - Custom Colors Fix
tags:
  - charts
  - customization
  - colors
created: 2025-12-02
---

# 🎨 Fixing Custom Colors in Obsidian Charts Plugin

## The Problem
You were trying to use **Chart.js syntax** for colors in the Obsidian Charts plugin, which uses a simplified YAML format. The Obsidian Charts plugin does NOT support Chart.js's `datasets:` and `backgroundColor:` properties.

### ❌ **WRONG** - Chart.js Syntax
```yaml
```chart
type: "bar"
labels: [...]
series:
  - title: "Data"
    data: [...]
datasets:
  0:
    backgroundColor: ["#FF6B6B", "#4ECDC4", "#45B7D1"]
```
```

## The Solution

The Obsidian Charts plugin uses **Chart.js under the hood**, but with a simplified YAML interface. There are **two ways** to apply multiple colors:

### ✅ **OPTION 1: Single Color Per Series** (Simplest)

Use `backgroundColor` for each series:

```yaml
```chart
type: "bar"
labels: ["Label 1", "Label 2", "Label 3"]
series:
  - title: "Series 1"
    data: [10, 20, 30]
    backgroundColor: "#FF6B6B"
xTitle: "X Axis Label"
yTitle: "Y Axis Label"
width: "90%"
```
```

### ✅ **OPTION 2: Multiple Colors Per Bar** (Stacked Approach)

To get **different colors for each bar**, create **one series per bar** with zeros elsewhere, then use `stacked: true`:

```yaml
```chart
type: "bar"
labels: ["Q1", "Q2", "Q3", "Q4"]
series:
  - title: "Category A"
    data: [100, 0, 0, 0]
    backgroundColor: "#FF6B6B"
  - title: "Category B"
    data: [0, 150, 0, 0]
    backgroundColor: "#4ECDC4"
  - title: "Category C"
    data: [0, 0, 200, 0]
    backgroundColor: "#45B7D1"
  - title: "Category D"
    data: [0, 0, 0, 175]
    backgroundColor: "#FFA07A"
stacked: true
xTitle: "Quarters"
yTitle: "Amount (R$)"
legend: true
legendPosition: top
width: "90%"
```
```

**Result**: Each bar has a different color, with a legend showing what each color represents.

## Quick Reference

| Property | Usage | Example |
|----------|-------|---------|
| Color per series | `backgroundColor: "#RRGGBB"` | One series = one color |
| Multiple colors per bar | `stacked: true` + multiple series | Each bar gets a unique series color |
| Axis titles | `xTitle: "..."` / `yTitle: "..."` | Top-level properties |
| Horizontal bars | `indexAxis: "y"` | Top-level property |
| Chart width | `width: "90%"` | Top-level property |
| Legend | `legend: true/false` | Top-level, default is `true` |
| Legend position | `legendPosition: top/bottom/left/right` | Where to place the legend |

## Why You Were Seeing Only One Color

**Root Cause**: The Obsidian Charts plugin **doesn't support per-element colors via a `colors` array**. It only recognizes:

1. **`backgroundColor`** (one color per series)
2. **CSS variables** (`--chart-color-1`, `--chart-color-2`, etc.) set at the note level
3. **Multiple series with stacking** to simulate multi-colored bars

Your original syntax used `colors: [...]` which the plugin ignored, so it fell back to the default theme color.

## Example: Bar Chart with Custom Colors

```yaml
```chart
type: "bar"
labels: ["Q1", "Q2", "Q3", "Q4"]
series:
  - title: "Revenue"
    data: [100000, 150000, 200000, 175000]
    colors: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A"]
xTitle: "Quarters"
yTitle: "Amount (R$)"
legend: true
width: "90%"
```
```

## Colors Applied

The following color palette was used in your charts (based on your original config):

- `#FF6B6B` - Coral Red
- `#4ECDC4` - Turquoise
- `#45B7D1` - Sky Blue
- `#FFA07A` - Light Salmon
- `#98D8C8` - Mint Green
- `#F7DC6F` - Golden Yellow
- `#BB8FCE` - Lavender
- `#85C1E2` - Light Blue

## Where to Learn More

📖 **Obsidian Charts Documentation**:
- See `/SYSTEM/Charts/Charts Plugin Docs/` for:
  - `Modifiers.md` - All available top-level modifiers
  - `Bar Chart.md` - Bar chart specifics
  - `Customization.md` - Color and styling options
  - `charts_cheatsheets.md` - Quick reference

## Common Pitfalls to Avoid

❌ **DON'T** use Chart.js syntax with `datasets:`, `options:`, `scales:`, `plugins:`  
✅ **DO** use simplified Obsidian syntax with `colors:`, `xTitle:`, `yTitle:`, `legend:`, `indexAxis:`

---

*Last updated: 2025-12-02*
