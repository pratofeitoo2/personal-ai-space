---
title: Chart from Table
author:
  - "[[Charts Plugin]]"
created: 2025-12-02
description: Modifiers - Charts Plugin
tags:
  - clippings
---
[Charts Plugin](https://charts.phib.ro/Meta/Charts/Charts+Documentation)

*Introduced in Version 3.3.0*

![cOB2ZyB.gif](https://i.imgur.com/cOB2ZyB.gif)

1. Add a Block ID (`^name`) to your Table:
	```md
	|       | Test1 | Test2 | Test3 |
	| ----- | ----- | ----- | ----- |
	| Data1 | 1     | 2     | 3.33  |
	| Data2 | 3     | 2     | 1     |
	| Data3 | 6.7   | 4     | 2     |
	^table
	```
2. Add the same `id` to your Chart Codeblock
	```md
	\`\`\`chart
	type: bar
	id: <blockId>
	layout: rows
	width: 80%
	beginAtZero: true
	\`\`\`
	```
3. (If you want to link a Table from a different File, also include the Filename in the `file` attribute)
	```md
	\`\`\`chart
	type: bar
	id: <blockId>
	file: <Filename>
	layout: rows
	width: 80%
	beginAtZero: true
	\`\`\`
	```
4. Choose the column or row oriented layout using the `layout` attribute. Options are `rows` or `columns`.
5. (Optional) Select the Columns or Rows with the `select` attribute. E.g. to only show Row `Data2` add `select: [Data2]`

## Replace Table with Chart

You can select a whole Markdown-Table and run the Command "Create Chart from Table" to replace it with a Chart.

Chart from Table

Interactive graph

Replace Table with Chart