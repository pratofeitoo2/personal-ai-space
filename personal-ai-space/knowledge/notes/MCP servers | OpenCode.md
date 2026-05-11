---
title: MCP servers | OpenCode
type: note
created: 2026-05-11T19:47
updated: 2026-05-11T19:47
---

# MCP servers | OpenCode

## Page 1

MCP servers
Add local and remote MCP tools.
You can add external tools to OpenCode using the Model Context Protocol, or MCP. OpenCode supports both local and
remote servers.
Once added, MCP tools are automatically available to the LLM alongside built-in tools.
When you use an MCP server, it adds to the context. This can quickly add up if you have a lot of tools. So we
recommend being careful with which MCP servers you use.
Tip
MCP servers add to your context, so you want to be careful with which ones you enable.
Certain MCP servers, like the GitHub MCP server, tend to add a lot of tokens and can easily exceed the context limit.
You can define MCP servers in your OpenCode Config under mcp. Add each MCP with a unique name. You can refer to
that MCP by name when prompting the LLM.
opencode.jsonc
"$schema": "https://opencode.ai/config.json",
"name-of-mcp-server": {
"name-of-other-mcp-server": {
You can also disable a server by setting enabled to false. This is useful if you want to temporarily disable a server
without removing it from your config.
Organizations can provide default MCP servers via their .well-known/opencode endpoint. These servers may be
disabled by default, allowing users to opt-in to the ones they need.
To enable a specific server from your organization’s remote config, add it to your local config with enabled: true:
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://jira.example.com/mcp",
Your local config values override the remote defaults. See config precedence for more details.
Add local MCP servers using type to "local" within the MCP object.
opencode.jsonc
"$schema": "https://opencode.ai/config.json",
"my-local-mcp-server": {
// Or ["bun", "x", "my-mcp-command"]
"command": ["npx", "-y", "my-mcp-command"],
"MY_ENV_VAR": "my_env_var_value",
The command is how the local MCP server is started. You can also pass in a list of environment variables as well.
For example, here’s how you can add the test @modelcontextprotocol/server-everything MCP server.
opencode.jsonc
"$schema": "https://opencode.ai/config.json",
"command": ["npx", "-y", "@modelcontextprotocol/server-everything"],

---

## Page 2

And to use it I can add use the mcp_everything tool to my prompts.
use the mcp_everything tool to add the number 3 and 4
Here are all the options for configuring a local MCP server.
Option Type Required Description
type String Y Type of MCP server connection, must be "local".
command Array Y Command and arguments to run the MCP server.
environment Object Environment variables to set when running the server.
enabled Boolean Enable or disable the MCP server on startup.
timeout Number Timeout in ms for fetching tools from the MCP server. Defaults to 5000 (5 seconds).
Add remote MCP servers by setting type to "remote".
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://my-mcp-server.com",
"Authorization": "Bearer MY_API_KEY"
The url is the URL of the remote MCP server and with the headers option you can pass in a list of headers.
Option Type Required Description
type String Y Type of MCP server connection, must be "remote".
url String Y URL of the remote MCP server.
enabled Boolean Enable or disable the MCP server on startup.
headers Object Headers to send with the request.
oauth Object OAuth authentication configuration. See OAuth section below.
timeout Number Timeout in ms for fetching tools from the MCP server. Defaults to 5000 (5 seconds).
OpenCode automatically handles OAuth authentication for remote MCP servers. When a server requires authentication,
OpenCode will:
1. Detect the 401 response and initiate the OAuth flow
2. Use Dynamic Client Registration (RFC 7591) if supported by the server
3. Store tokens securely for future requests
For most OAuth-enabled MCP servers, no special configuration is needed. Just configure the remote server:
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://mcp.example.com/mcp"
If the server requires authentication, OpenCode will prompt you to authenticate when you first try to use it. If not, you
can manually trigger the flow with opencode mcp auth <server-name>.
If you have client credentials from the MCP server provider, you can configure them:
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://mcp.example.com/mcp",
"clientId": "{env:MY_MCP_CLIENT_ID}",
"clientSecret": "{env:MY_MCP_CLIENT_SECRET}",
"scope": "tools:read tools:execute"

---

## Page 3

You can manually trigger authentication or manage credentials.
Authenticate with a specific MCP server:
opencode mcp auth my-oauth-server
List all MCP servers and their auth status:
Remove stored credentials:
opencode mcp logout my-oauth-server
The mcp auth command will open your browser for authorization. After you authorize, OpenCode will store the tokens
securely in ~/.local/share/opencode/mcp-auth.json.
If you want to disable automatic OAuth for a server (e.g., for servers that use API keys instead), set oauth to false:
opencode.json
"$schema": "https://opencode.ai/config.json",
"my-api-key-server": {
"url": "https://mcp.example.com/mcp",
"Authorization": "Bearer {env:MY_API_KEY}"
Option Type Description
oauth Object | false OAuth config object, or false to disable OAuth auto-detection.
clientId String OAuth client ID. If not provided, dynamic client registration will be attempted.
clientSecret String OAuth client secret, if required by the authorization server.
scope String OAuth scopes to request during authorization.
If a remote MCP server is failing to authenticate, you can diagnose issues with:
# View auth status for all OAuth-capable servers
# Debug connection and OAuth flow for a specific server
opencode mcp debug my-oauth-server
The mcp debug command shows the current auth status, tests HTTP connectivity, and attempts the OAuth discovery flow.
Your MCPs are available as tools in OpenCode, alongside built-in tools. So you can manage them through the OpenCode
config like any other tool.
This means that you can enable or disable them globally.
opencode.json
"$schema": "https://opencode.ai/config.json",
"command": ["bun", "x", "my-mcp-command-foo"]
"command": ["bun", "x", "my-mcp-command-bar"]
We can also use a glob pattern to disable all matching MCPs.
opencode.json
"$schema": "https://opencode.ai/config.json",
"command": ["bun", "x", "my-mcp-command-foo"]
"command": ["bun", "x", "my-mcp-command-bar"]
Here we are using the glob pattern my-mcp* to disable all MCPs.
If you have a large number of MCP servers you may want to only enable them per agent and disable them globally. To do

---

## Page 4

this:
1. Disable it as a tool globally.
2. In your agent config, enable the MCP server as a tool.
opencode.json
"$schema": "https://opencode.ai/config.json",
"command": ["bun", "x", "my-mcp-command"],
The glob pattern uses simple regex globbing patterns:
* matches zero or more of any character (e.g., "my-mcp*" matches my-mcp_search, my-mcp_list, etc.)
? matches exactly one character
All other characters match literally
Note
MCP server tools are registered with server name as prefix, so to disable all tools for a server simply use:
"mymcpservername_*": false
Below are examples of some common MCP servers. You can submit a PR if you want to document other servers.
Add the Sentry MCP server to interact with your Sentry projects and issues.
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://mcp.sentry.dev/mcp",
After adding the configuration, authenticate with Sentry:
This will open a browser window to complete the OAuth flow and connect OpenCode to your Sentry account.
Once authenticated, you can use Sentry tools in your prompts to query issues, projects, and error data.
Show me the latest unresolved issues in my project. use sentry
Add the Context7 MCP server to search through docs.
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://mcp.context7.com/mcp"
If you have signed up for a free account, you can use your API key and get higher rate-limits.
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://mcp.context7.com/mcp",
"CONTEXT7_API_KEY": "{env:CONTEXT7_API_KEY}"
Here we are assuming that you have the CONTEXT7_API_KEY environment variable set.
Add use context7 to your prompts to use Context7 MCP server.
Configure a Cloudflare Worker script to cache JSON API responses for five minutes. use context7
Alternatively, you can add something like this to your AGENTS.md.
AGENTS.md
When you need to search docs, use `context7` tools.

---

## Page 5

Add the Grep by Vercel MCP server to search through code snippets on GitHub.
opencode.json
"$schema": "https://opencode.ai/config.json",
"url": "https://mcp.grep.app"
Since we named our MCP server gh_grep, you can add use the gh_grep tool to your prompts to get the agent to use
it.
What's the right way to set a custom domain in an SST Astro component? use the gh_grep tool
Alternatively, you can add something like this to your AGENTS.md.
AGENTS.md
If you are unsure how to do something, use `gh_grep` to search code examples from GitHub.