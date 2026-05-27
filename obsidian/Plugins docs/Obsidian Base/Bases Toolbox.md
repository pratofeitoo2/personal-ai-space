---
title: Bases Toolbox
author:
created: 2025-12-05
description:
tags:
  - clippings
updated: 2025-12-05T21:36
---
1. Enter a Dataview TABLE query in the left box
2. Choose whether to place filters in views or globally
3. Click "Convert to Bases" to convert it to Bases YAML
4. The converted YAML will appear in the right box
5. You can also try the Bases YAML examples directly
6. Copy the YAML to create a.base file in Obsidian

### Reference

#### Supported Features

- `TABLE` fields with aliases
- `FROM` source selection (folders, tags)
- `WHERE` conditions (simple AND, OR)
- `SORT` clause with ASC/DESC
- `LIMIT` clause
- `GROUP BY` clause
- Date arithmetic (`date + duration`, `date - duration`)
- Formulas and calculations in fields

#### Filter Groups

Complex filters can be grouped with nested AND/OR logic:

```
filters:
  and:
    - condition1
    - or:
        - condition2
        - condition3
    - and:
        - condition4
        - condition5
```

#### Column Order & Sorting

Bases supports two separate properties for arrangement:

```
# Column order (display order in table)
order:
  - column1
  - column2
  - column3

# Data sorting (how data is ordered)
sort:
  - column: priority
    direction: DESC
  - column: date
    direction: ASC
```

#### Date Functions & Arithmetic

Date expressions and calculations:

- `date(today)` - current date
- `date(tomorrow)` - tomorrow's date
- `date(yesterday)` - yesterday's date
- `date("2024-01-01")` - specific date
- `dur(7 days)` - duration literal
- `date(today) + dur(7 days)` - date arithmetic
- `date(today) - dur(1 week)` - subtract duration
- `due - date(today)` - date difference
- `date.year`, `date.month`, `date.day` - date accessors

#### Filter Functions

- `contains()`
- `not_contains()`
- `containsAny()`
- `containsAll()`
- `startswith()`
- `endswith()`
- `empty()`
- `notEmpty()`
- `if()`
- `inFolder()`
- `linksTo()`
- `not()`
- `tag()`
- `dateBefore()`
- `dateAfter()`
- `dateEquals()`
- `dateNotEquals()`
- `dateOnOrBefore()`
- `dateOnOrAfter()`
- `taggedWith()`

#### File Properties

- `file.name` - file name
- `file.path` - full file path
- `file.folder` - containing folder
- `file.extension` - file extension
- `file.size` - file size
- `file.ctime` - created time
- `file.mtime` - modified time



Drop your.base file here

#### 📋 Changes Made

- ✅ Updated inFolder() to file.inFolder()
- ✅ Updated taggedWith() to file.hasTag()
- ✅ Updated linksTo() to file.hasLink()
- ✅ Updated file.extension to file.ext
- ✅ Updated sort direction to lowercase
- ✅ Updated concat() to + operator for string concatenation
- ✅ Updated join("",...) to + operator for string concatenation
- ✅ Updated join() with separator to + operator

### 🔧 What gets updated?

#### File Functions

- `inFolder(file.file, "folder")` → `file.inFolder("folder")`
- `taggedWith(file.file, "tag")` → `file.hasTag("tag")`
- `linksTo(file.file, "file")` → `file.hasLink("file")`

#### Boolean Operators

- `and` → `&&`
- `or` → `||`
- `not()` → `!()`

#### String Operations

- `concat(a, b, c)` → `a + b + c`
- `join("", a, b)` → `a + b`
- `join(" ", a, b)` → `a + " " + b`
- `array.join("")` → `array`
- `array.join(", ")` → `array.join(", ")`
- `len()` → `length()`
- `empty()` → `isEmpty()`
- `notEmpty()` → `!isEmpty()`

#### Properties & Functions

- `file.extension` → `file.ext`
- `dateFormat()` → `format()`
- `average()` → `average()`

#### Date & Time

- `dateModify(date, "1 day")` → `date + "1 day"`
- `duration("1 day")` → `"1 day"`
- `dateDiff(a, b)` → `a - b`

#### View Configuration

- Sort directions: `ASC/DESC` → `asc/desc`
- Filter syntax updated to new format
- Formula expressions simplified