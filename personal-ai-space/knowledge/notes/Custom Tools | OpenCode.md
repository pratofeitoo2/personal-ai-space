---
title: Custom Tools | OpenCode
type: note
created: 2026-05-11T19:47
updated: 2026-05-11T19:47
---

# Custom Tools | OpenCode

## Page 1

Custom Tools
Create tools the LLM can call in opencode.
Create tools the LLM can call in opencode.
Custom tools are functions you create that the LLM can call during conversations. They work alongside opencode’s built-in tools
like read, write, and bash.
Tools are defined as TypeScript or JavaScript files. However, the tool definition can invoke scripts written in any language —
TypeScript or JavaScript is only used for the tool definition itself.
They can be defined:
Locally by placing them in the .opencode/tools/ directory of your project.
Or globally, by placing them in ~/.config/opencode/tools/.
The easiest way to create tools is using the tool() helper which provides type-safety and validation.
.opencode/tools/database.ts
import { tool } from "@opencode-ai/plugin"
description: "Query the project database",
query: tool.schema.string().describe("SQL query to execute"),
// Your database logic here
return `Executed query: ${args.query}`
The filename becomes the tool name. The above creates a database tool.
You can also export multiple tools from a single file. Each export becomes a separate tool with the name
<filename>_<exportname>:
.opencode/tools/math.ts
import { tool } from "@opencode-ai/plugin"
export const add = tool({
description: "Add two numbers",
a: tool.schema.number().describe("First number"),
b: tool.schema.number().describe("Second number"),
return args.a + args.b
export const multiply = tool({
description: "Multiply two numbers",
a: tool.schema.number().describe("First number"),
b: tool.schema.number().describe("Second number"),
return args.a * args.b
This creates two tools: math_add and math_multiply.
Custom tools are keyed by tool name. If a custom tool uses the same name as a built-in tool, the custom tool takes precedence.
For example, this file replaces the built-in bash tool:
.opencode/tools/bash.ts
import { tool } from "@opencode-ai/plugin"
description: "Restricted bash wrapper",
command: tool.schema.string(),
return `blocked: ${args.command}`

---

## Page 2

Note
Prefer unique names unless you intentionally want to replace a built-in tool. If you want to disable a built in tool but not override
it, use permissions.
You can use tool.schema, which is just Zod, to define argument types.
query: tool.schema.string().describe("SQL query to execute")
You can also import Zod directly and return a plain object:
description: "Tool description",
param: z.string().describe("Parameter description"),
async execute(args, context) {
// Tool implementation
Tools receive context about the current session:
.opencode/tools/project.ts
import { tool } from "@opencode-ai/plugin"
description: "Get project information",
async execute(args, context) {
// Access context information
const { agent, sessionID, messageID, directory, worktree } = context
return `Agent: ${agent}, Session: ${sessionID}, Message: ${messageID}, Directory: ${directory}, Worktree: ${worktree}`
Use context.directory for the session working directory. Use context.worktree for the git worktree root.
You can write your tools in any language you want. Here’s an example that adds two numbers using Python.
First, create the tool as a Python script:
Then create the tool definition that invokes it:
.opencode/tools/python-add.ts
import { tool } from "@opencode-ai/plugin"
description: "Add two numbers using Python",
a: tool.schema.number().describe("First number"),
b: tool.schema.number().describe("Second number"),
async execute(args, context) {
const script = path.join(context.worktree, ".opencode/tools/add.py")
const result = await Bun.$`python3 ${script} ${args.a} ${args.b}`.text()
Here we are using the Bun.$ utility to run the Python script.