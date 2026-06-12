---
title: Server | OpenCode
type: note
created: 2026-05-11T19:47
updated: 2026-05-11T19:47
---

# Server | OpenCode

## Page 1

Server
Interact with opencode server over HTTP.
Interact with opencode server over HTTP.
The opencode serve command runs a headless HTTP server that exposes an OpenAPI endpoint that an opencode client
can use.
opencode serve [--port <number>] [--hostname <string>] [--cors <origin>]
Flag Description Default
--port Port to listen on 4096
--hostname Hostname to listen on 127.0.0.1
--mdns Enable mDNS discovery false
--mdns-domain Custom domain name for mDNS service opencode.local
--cors Additional browser origins to allow []
--cors can be passed multiple times:
opencode serve --cors http://localhost:5173 --cors https://app.example.com
Set OPENCODE_SERVER_PASSWORD to protect the server with HTTP basic auth. The username defaults to opencode, or set
OPENCODE_SERVER_USERNAME to override it. This applies to both opencode serve and opencode web.
OPENCODE_SERVER_PASSWORD=your-password opencode serve
When you run opencode it starts a TUI and a server. Where the TUI is the client that talks to the server. The server exposes
an OpenAPI 3.1 spec endpoint. This endpoint is also used to generate an SDK.
Tip
Use the opencode server to interact with opencode programmatically.
This architecture lets opencode support multiple clients and allows you to interact with opencode programmatically.
You can run opencode serve to start a standalone server. If you have the opencode TUI running, opencode serve will
start a new server.
When you start the TUI it randomly assigns a port and hostname. You can instead pass in the --hostname and --port flags.
Then use this to connect to its server.
The /tui endpoint can be used to drive the TUI through the server. For example, you can prefill or run a prompt. This setup
is used by the OpenCode IDE plugins.
The server publishes an OpenAPI 3.1 spec that can be viewed at:
http://<hostname>:<port>/doc
For example, http://localhost:4096/doc. Use the spec to generate clients or inspect request and response types. Or view
it in a Swagger explorer.
The opencode server exposes the following APIs.
Method Path Description Response
GET /global/health Get server health and version { healthy: true, version: string }
GET /global/event Get global events (SSE stream) Event stream
Method Path Description Response

---

## Page 2

GET /project List all projects Project[]
GET /project/current Get the current project Project
Method Path Description Response
GET /path Get the current path Path
GET /vcs Get VCS info for the current project VcsInfo
Method Path Description Response
POST /instance/dispose Dispose the current instance boolean
Method Path Description Response
GET /config Get config info Config
PATCH /config Update config Config
List providers and default { providers: Provider[], default: { [key: string]:
GET /config/providers
models string } }
Method Path Description Response
{ all: Provider[], default: {...}, connected:
GET /provider List all providers
string[] }
Get provider authentication
GET /provider/auth { [providerID: string]: ProviderAuthMethod[] }
methods
Authorize a provider using
POST /provider/{id}/oauth/authorize ProviderAuthAuthorization
OAuth
Handle OAuth callback for a
POST /provider/{id}/oauth/callback boolean
provider
Method Path Description Notes
GET /session List all sessions Returns Session[]
body: { parentID?, title? }, returns
POST /session Create a new session
Session
Get session status for all Returns { [sessionID: string]:
GET /session/status
sessions SessionStatus }
GET /session/:id Get session details Returns Session
Delete a session and all
DELETE /session/:id Returns boolean
its data
Update session
PATCH /session/:id body: { title? }, returns Session
properties
Get a session’s child
GET /session/:id/children Returns Session[]
sessions
Get the todo list for a
GET /session/:id/todo Returns Todo[]
session
Analyze app and create body: { messageID, providerID,
POST /session/:id/init
AGENTS.md modelID }, returns boolean
Fork an existing session
POST /session/:id/fork body: { messageID? }, returns Session
at a message
POST /session/:id/abort Abort a running session Returns boolean
POST /session/:id/share Share a session Returns Session
DELETE /session/:id/share Unshare a session Returns Session
Get the diff for this
GET /session/:id/diff query: messageID?, returns FileDiff[]
session
body: { providerID, modelID }, returns
POST /session/:id/summarize Summarize the session
boolean
body: { messageID, partID? }, returns
POST /session/:id/revert Revert a message
boolean
Restore all reverted
POST /session/:id/unrevert Returns boolean
messages
Respond to a permission body: { response, remember? }, returns
POST /session/:id/permissions/:permissionID
request boolean

---

## Page 3

Method Path Description Notes
List messages in a
GET /session/:id/message query: limit?, returns { info: Message, parts: Part[]}[]
session
Send a message and body: { messageID?, model?, agent?, noReply?, system?,
POST /session/:id/message
wait for response tools?, parts }, returns { info: Message, parts: Part[]}
GET /session/:id/message/:messageID Get message details Returns { info: Message, parts: Part[]}
Send a message
POST /session/:id/prompt_async asynchronously (no body: same as /session/:id/message, returns 204 No Content
wait)
Execute a slash body: { messageID?, agent?, model?, command, arguments
POST /session/:id/command
command }, returns { info: Message, parts: Part[]}
Run a shell body: { agent, model?, command }, returns { info:
POST /session/:id/shell
command Message, parts: Part[]}
Method Path Description Response
GET /command List all commands Command[]
Method Path Description Response
/find?pattern=
Array of match objects with path, lines, line_number,
GET Search for text in files
<pat> absolute_offset, submatches
Find files and directories
/find/file?
GET string[] (paths)
query=<q> by name
/find/symbol?
GET Find workspace symbols Symbol[]
query=<q>
/file?path=
GET List files and directories FileNode[]
<path>
/file/content?
GET Read a file FileContent
path=<p>
Get status for tracked
GET /file/status File[]
files
/find/file query parameters
query (required) — search string (fuzzy match)
type (optional) — limit results to "file" or "directory"
directory (optional) — override the project root for the search
limit (optional) — max results (1–200)
dirs (optional) — legacy flag ("false" returns only files)
Method Path Description Response
GET /experimental/tool/ids List all tool IDs ToolIDs
GET /experimental/tool?provider=<p>&model=<m> List tools with JSON schemas for a model ToolList
Method Path Description Response
GET /lsp Get LSP server status LSPStatus[]
GET /formatter Get formatter status FormatterStatus[]
GET /mcp Get MCP server status { [name: string]: MCPStatus }
POST /mcp Add MCP server dynamically body: { name, config }, returns MCP status object
Method Path Description Response
GET /agent List all available agents Agent[]
Method Path Description Response
POST /log Write log entry. Body: { service, level, message, extra? } boolean
Method Path Description Response
POST /tui/append-prompt Append text to the prompt boolean
POST /tui/open-help Open the help dialog boolean

---

## Page 4

POST /tui/open-sessions Open the session selector boolean
POST /tui/open-themes Open the theme selector boolean
POST /tui/open-models Open the model selector boolean
POST /tui/submit-prompt Submit the current prompt boolean
POST /tui/clear-prompt Clear the prompt boolean
POST /tui/execute-command Execute a command ({ command }) boolean
POST /tui/show-toast Show toast ({ title?, message, variant }) boolean
GET /tui/control/next Wait for the next control request Control request object
POST /tui/control/response Respond to a control request ({ body }) boolean
Method Path Description Response
PUT /auth/:id Set authentication credentials. Body must match provider schema boolean
Method Path Description Response
GET /event Server-sent events stream. First event is server.connected, then bus events Server-sent events stream
Method Path Description Response
GET /doc OpenAPI 3.1 specification HTML page with OpenAPI spec