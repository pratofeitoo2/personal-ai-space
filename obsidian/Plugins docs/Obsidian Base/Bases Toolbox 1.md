---
title: Bases Toolbox
author:
created: 2025-12-05
description:
tags:
  - clippings
updated: 2025-12-05T21:35
---
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