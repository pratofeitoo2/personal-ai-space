---
title: Basics
author:
  - "[[Charts Plugin]]"
created: 2025-12-02
description: Modifiers - Charts Plugin
tags:
  - clippings
---
[Charts Plugin](https://charts.phib.ro/Meta/Charts/Charts+Documentation)

To create a Chart within Obsidian a Codeblock of the type `chart` is used. The Properties are set using YAML Syntax. Example:

```yaml
\`\`\`chart
    type: ""
    labels: []
    series:
        - title: ""
        data: []
        - title: ""
        data: []

\`\`\`
```

The `title` Property *can* be omitted, but it is not advised to do so.

Warning

You might **not** be able to copy the Examples directly into Obsidian, the Indentation is probably wrong and Obsidian tries to convert pasted Text to Markdown, which escapes a few important characters.

You can either manually write these Codeblocks **or** use the graphical Creator.

### Graphical Chart Creator

For simple Charts you can use the graphical Chart Creator, you can access it via the Command Palette or you can even set a Hotkey!

![b913e0cec14e6bad57ef0757ce29d288.gif](https://cdn.buymeacoffee.com/uploads/project_updates/2021/04/b913e0cec14e6bad57ef0757ce29d288.gif)

Basics

Interactive graph

Graphical Chart Creator