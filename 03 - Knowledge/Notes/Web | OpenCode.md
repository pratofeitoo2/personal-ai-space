---
title: Web | OpenCode
type: note
created: 2026-05-11T19:47
updated: 2026-05-11T19:47
---

# Web | OpenCode

## Page 1

Web
Using OpenCode in your browser.
OpenCode can run as a web application in your browser, providing the same powerful AI coding experience without needing
a terminal.

---

## Page 2

Start the web interface by running:
This starts a local server on 127.0.0.1 with a random available port and automatically opens OpenCode in your default
browser.
Caution
If OPENCODE_SERVER_PASSWORD is not set, the server will be unsecured. This is fine for local use but should be set for network
access.
Windows Users
For the best experience, run opencode web from WSL rather than PowerShell. This ensures proper file system access and
terminal integration.
You can configure the web server using command line flags or in your config file.
By default, OpenCode picks an available port. You can specify a port:
By default, the server binds to 127.0.0.1 (localhost only). To make OpenCode accessible on your network:

---

## Page 3

opencode web --hostname 0.0.0.0
When using 0.0.0.0, OpenCode will display both local and network addresses:
Local access: http://localhost:4096
Network access: http://192.168.1.100:4096
Enable mDNS to make your server discoverable on the local network:
This automatically sets the hostname to 0.0.0.0 and advertises the server as opencode.local.
You can customize the mDNS domain name to run multiple instances on the same network:
opencode web --mdns --mdns-domain myproject.local
To allow additional domains for CORS (useful for custom frontends):
opencode web --cors https://example.com
To protect access, set a password using the OPENCODE_SERVER_PASSWORD environment variable:
OPENCODE_SERVER_PASSWORD=secret opencode web
The username defaults to opencode but can be changed with OPENCODE_SERVER_USERNAME.
Once started, the web interface provides access to your OpenCode sessions.
View and manage your sessions from the homepage. You can see active sessions and start new ones.

---

## Page 4

Click “See Servers” to view connected servers and their status.

---

## Page 6

You can attach a terminal TUI to a running web server:
# In another terminal, attach the TUI
opencode attach http://localhost:4096
This allows you to use both the web interface and terminal simultaneously, sharing the same sessions and state.
You can also configure server settings in your opencode.json config file:
"hostname": "0.0.0.0",
"cors": ["https://example.com"]
Command line flags take precedence over config file settings.