---
title: Table view
author:
  - "[[Obsidian Help]]"
created: 2025-12-05
description: Functions - Obsidian Help
tags:
  - clippings
updated: 2025-12-05T21:57
---
Table is a type of [view](https://help.obsidian.md/bases/views) you can use in [Bases](https://help.obsidian.md/bases).

![Example of a base showing a table view with a list of books](https://publish-01.obsidian.md/access/f786db9fac45774fa4f0d8112e232d67/Attachments/bases-noshadow.png)

Example of a base showing a table view with a list of books

## Settings

Table view settings can be configured in [View settings](https://help.obsidian.md/bases/views#View%20settings).

### Row height

Row height lets you display more information. Choose between **short**, **medium**, **tall**, and **extra tall**.

## Summaries

You can add summaries to a table column to quickly calculate values like totals, averages, or counts for the rows currently visible in the view.

Summaries are tied to the view, not the base. Each view can show different summaries for the same column.

### Add a summary

The summary appears at the bottom of the column. When results are [grouped](https://help.obsidian.md/bases/views#Sort%20and%20group%20results) the summary for each group is displayed at the top of the group.

Once the summary bar is added you can add more summaries for other columns by clicking the summary cell. The summary bar is hidden if all summaries are removed.

### Built-in summaries

The following summaries are available by default. Options may vary depending on the property type.

#### All property types

- **Empty**: count of rows with no value.
- **Filled**: count of rows with a value.
- **Unique**: number of distinct values.

#### Numbers

- **Average**: average of all numeric values.
- **Max**: largest value.
- **Median**: median value.
- **Min**: smallest value.
- **Range**: difference between max and min.
- **Stddev**: standard deviation.
- **Sum**: total of all values.

#### Dates

- **Earliest**: the smallest/oldest date.
- **Latest**: the largest/most recent date.
- **Range**: difference between earliest and latest.

#### Checkbox

- **Checked**: number of rows where the checkbox is on.
- **Unchecked**: number of rows where the checkbox is off.

### Custom summaries

You can define your own summary using a formula:

Custom summaries are useful when you need a calculation that isn’t covered by the built-in options.

## Shortcuts

You can quickly move around a table view using the following mouse and [keyboard shortcuts](https://help.obsidian.md/editing-shortcuts).

- Shift-click creates a cell selection.
- Right-click a cell selection to access additional actions for those files.

| Action | Shortcut | macOS |
| --- | --- | --- |
| Copy the selected cells | `Ctrl+C` | `Cmd+C` |
| Paste the selected cells | `Ctrl+V` | `Cmd+V` |
| Undo changes to properties | `Ctrl+Z` | `Cmd+Z` |
| Redo changes to properties | `Ctrl+Shift+Z` | `Cmd+Shift+Z` |
| Select all cells in the current group | `Ctrl+A` | `Cmd+A` |
| Select all cells in a given direction | `Ctrl+Shift+Arrow` | `Ctrl+Shift+Arrow` |
| Select the column | `Ctrl+Space` |  |
| Select the row | `Shift+Space` |  |
| Focus the current cell — for checkboxes, this toggles the checkbox, for formulas, this opens the formula editor | `Enter` |  |
| Go to the first column | `Home` |  |
| Go to the last column | `End` |  |
| Navigate up and down by page height | `PageUp`,`PageDown` |  |
| Clear the current cell selection | `Esc` |  |
| Clear the current cells | `Backspace` |  |
| Go to the next cell | `Tab` |  |
| Go to the previous cell | `Shift-Tab` |  |