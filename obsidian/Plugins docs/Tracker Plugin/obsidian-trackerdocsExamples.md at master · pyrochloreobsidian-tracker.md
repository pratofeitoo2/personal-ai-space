---
title: obsidian-tracker/docs/Examples.md at master · pyrochlore/obsidian-tracker
source: https://github.com/pyrochlore/obsidian-tracker/blob/master/docs/Examples.md
author:
  - "[[pnyro]]"
published:
created: 2025-12-07
description: A plugin tracks occurrences and numbers in your notes - obsidian-tracker/docs/Examples.md at master · pyrochlore/obsidian-tracker
tags:
  - clippings
---
[Open in github.dev](https://github.dev/) [Open in a new github.dev tab](https://github.dev/) [Open in codespace](https://github.com/codespaces/new/pyrochlore/obsidian-tracker/tree/master?resume=1)

[fix: spelling error in Examples.md](https://github.com/pyrochlore/obsidian-tracker/commit/a51905f27c3977f5f47559494e7c25d1a9a56f29)

[a51905f](https://github.com/pyrochlore/obsidian-tracker/commit/a51905f27c3977f5f47559494e7c25d1a9a56f29) ·

## Examples

We provide a simplified table of use cases and full examples including data.

Check where (Location) and what (Target to Track) is your target and find the settings (Tracker) you need.

| Location | Target to Track | Tracker | Get (O)ccurrences/(V)alues |
| --- | --- | --- | --- |
| content | #meditation | searchType: tag   searchTarget: meditation | O |
| frontmatter | \---   tags: meditation   \--- | searchType: tag   searchTarget: meditation | O |
| content | #weight:60.5kg | searchType: tag   searchTarget: weight | V |
| content | #finance/bank1/transfer:100USD | searchType: tag   searchTarget: finance/bank1/transfer | V |
| content | #finance/bank1/transfer:100USD   #finance/bank1/income:80USD   #finance/bank1/outcome:-120USD | searchType: tag   searchTarget: finance/bank1 | V |
| content | #blood-pressure:180/120 | searchType: tag   searchTarget: blood-pressure\[0\], blood-pressure\[1\] | V |
| content | dvTarget:: 20.5 | searchType: dvField   searchTarget: dvTarget | V |
| content | dvTarget:: 20.5/30.5 | searchType: dvField   searchTarget: dvTarget\[0\], dvTarget\[1\] | V |
| content | dvTarget:: 20.5, 30.5 | searchType: dvField   searchTarget: dvTarget\[0\], dvTarget\[1\]   separator: 'comma' | V |
| frontmatter | \---   mood: 10   \--- | searchType: frontmatter   searchTarget: mood | V |
| frontmatter | \---   bp: 184.4/118.8   \--- | searchType: frontmatter   searchTarget: bp\[0\], bp\[1\] | V |
| frontmatter | \---   bp: 184.4, 118.8   \--- | searchType: frontmatter   searchTarget: bp\[0\], bp\[1\]   separator: 'comma' | V |
| frontmatter | \---   bp: \[184.4, 118.8\]   \--- | searchType: frontmatter   searchTarget: bp\[0\], bp\[1\] | V |
| frontmatter | \---   clock-in: 10:45   clock-out: 20:51   \--- | searchType: frontmatter   searchTarget: clock-in, clock-out | V |
| content | \[\[journal\]\] | searchType: wiki   searchTarget: journal | O |
| content | ⭐ | searchType: text   searchTarget: ⭐ | O |
| content | love | searchType: text   searchTarget: love | O |
| content | [test@gmail.com](https://github.com/pyrochlore/obsidian-tracker/blob/master/docs/)   [test@hotmail.com](https://github.com/pyrochlore/obsidian-tracker/blob/master/docs/) | searchType: text   searchTarget: '.+\\@.+\\..+' | O |
| content | #weightlifting: 50 | searchType: text   searchTarget: 'weightlifting: (?\[\\-\]?\[0-9\]+\[\\.\]\[0-9\]+\|\[\\-\]?\[0-9\]+)' | V |
| content | I walked 10000 steps today. | searchType: text   searchTarget: 'walked\\s+(?\[0-9\]+)\\s+steps' | V |
| content | myvalues 1/2/3 | searchType: text   searchTarget: 'myvalues\\s+(?\[0-9\]+)/(\[0-9\]+)/(\[0-9\]+), myvalues\\s+(\[0-9\]+)/(?\[0-9\]+)/(\[0-9\]+), myvalues\\s+(\[0-9\]+)/(\[0-9\]+)/(?\[0-9\]+)' | V |
| table content | { a table filled with dates and values }   [example table](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/data/Tables.md) | searchType: table   searchTarget: filePath\[0\]\[0\], filePath\[0\]\[1\] | V |
| table content | { a table filled with dates and values }   [example table](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/data/Tables.md) | searchType: table   searchTarget: filePath\[1\]\[0\], filePath\[1\]\[1\]\[0\], filePath\[1\]\[1\]\[1\] | V |
| file meta | meta data from files   (size, cDate, mDate, numWords, numChars, numSentences) | searchType: fileMeta   searchTarget: size | V |
| content | \- \[x\] Say love   \- \[ \] Say love | searchType:task   searchTarget: Say love | O |
| content | \- \[x\] Say love | searchType:task.done   searchTarget: Say love | O |
| content | \- \[ \] Say love | searchType: task.notdone   searchTarget: Say love | O |

## Full examples

Full tracker code blocks can be found in folder [examples](https://github.com/pyrochlore/obsidian-tracker/tree/master/examples) and the corresponding notes (data) can be found under folder ' [diary](https://github.com/pyrochlore/obsidian-tracker/tree/master/examples/diary) ' and ' [data](https://github.com/pyrochlore/obsidian-tracker/tree/master/examples/data) '.

List of all examples

- [Bloodpressure Tracker](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/BloodPressureTracker.md)
- [Error Messages](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/ErrorMessages.md)
- [Finance Tracker](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/FinanceTracker.md)
- [Habit Tracker](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/HabitTracker.md)
- [Star Tracker](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/StarTracker.md)
- [Bar Chart](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestBarChart.md)
- [Axis Interval and Format](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestAxisIntervalAndFormat.md)
- [Bullet Chart](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestBullet.md)
- [Calendar](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestCalendar.md)
- [Date Formats](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestDateFormats.md)
- [Dataview Inline Field](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestDvField.md)
- [Expression](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestExpression.md)
- [File Meta](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestFileMeta.md)
- [Legends](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestLegends.md)
- [Multiple Targets / Multiple Values](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestMultipleTargetsMultipleValues.md)
- [Pie Chart](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestPieChart.md)
- [Scaling and Positioning](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestScalingAndPositioning.md)
- [Specified Files](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestSpecifiedFiles.md)
- [Summary](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestSummary.md)
- [Table](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestTable.md)
- [Task](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestTask.md)
- [Text-value Map/Mood Tracker](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestTextValueMap.md)
- [Time Values](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestTimeValues.md)
- [Word Counting](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestWordCounting.md)
- [X Dataset](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestXDataset.md)
- [Regular Expression](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/TestRegex.md)
- [Weight Tracker](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/WeightTracker.md)
- [Wiki](https://github.com/pyrochlore/obsidian-tracker/blob/master/examples/WikiTracker.md)