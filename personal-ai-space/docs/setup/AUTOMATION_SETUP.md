# 🤖 Intake Automation — Running 24/7

## What's Running

**Intake Watcher Service** continuously monitors your staging folder and auto-processes new files.

### How It Works

1. **File Added** → staging folder
2. **Watcher Detects** (checks every 10 seconds)
3. **Waits 60 Seconds** (debounce for batch uploads)
4. **Auto-Runs** `process_intake.py`
5. **Files Routed** to correct destinations
6. **Logged** to audit trail

**Result:** Zero manual intervention needed.

---

## Service Details

**Service Name:** `com.personalai.intake-watcher`  
**Status:** ✅ Running (macOS launchd)  
**Restart:** Automatic (if crashes)  
**Startup:** Auto on reboot  
**Logs:** `intake/watcher.log`

---

## Usage

### Add Data (Just Drop & Walk Away)

```bash
# Copy files to staging
cp ~/Obsidian/vault/notes/*.md ~/Documents/Personal_AI_powerhouse/personal-ai-space/intake/staging/

# That's it. Watcher will process in ~60 seconds automatically.
```

### Monitor Progress

```bash
# Live log
tail -f ~/Documents/Personal_AI_powerhouse/personal-ai-space/intake/watcher.log

# Or check status
launchctl list | grep intake-watcher
```

### Control Service

```bash
# Stop watcher
launchctl unload ~/Library/LaunchAgents/com.personalai.intake-watcher.plist

# Start watcher
launchctl load ~/Library/LaunchAgents/com.personalai.intake-watcher.plist

# View service plist
cat ~/Library/LaunchAgents/com.personalai.intake-watcher.plist
```

---

## Log Format

```
[2026-05-06 02:00:20] 🚀 Intake Watcher started
[2026-05-06 02:00:40] 📁 Change detected: 172 files in staging
[2026-05-06 02:01:41] 🔄 Running intake processor...
[2026-05-06 02:01:42] ✅ Intake processing complete
```

---

## Routing Rules (Automatic)

When files are processed, they're auto-routed based on:

| Trigger | Destination |
|---------|-------------|
| Filename contains "Daily Notes" | `command/inbox/` |
| Filename contains "Life Plans" | `self/goals/` |
| Filename contains "People" | `self/relationships/` |
| Filename contains "PF" or "financial" | `command/finances/` |
| Frontmatter tag: `article` | `knowledge/articles/` |
| Frontmatter tag: `project` | `knowledge/projects/` |
| Default | `knowledge/notes/` |

---

## Best Practices

### 1. Organize Before Dropping

For bulk imports, organize in staging first:
```
intake/staging/
  ├── Daily Notes/    (auto-routes to inbox)
  ├── Life Plans/     (auto-routes to goals)
  └── People/         (auto-routes to relationships)
```

### 2. Use Frontmatter Tags

Add metadata to your Obsidian files:
```markdown
---
tags: [article, research]
category: finance
---

# Content here
```

### 3. Monitor the Log

Check watcher.log after adding files to see what happened:
```bash
tail watcher.log
```

### 4. One Filename Per File

If you drop files with duplicate names, the processor will overwrite. Rename first if needed.

---

## How to Add More Data

### Option A: Single File
```bash
cp ~/Obsidian/file.md ~/Documents/Personal_AI_powerhouse/personal-ai-space/intake/staging/
# Watcher auto-processes in ~60s
```

### Option B: Bulk from Obsidian
```bash
# Copy entire folder
cp -r ~/Obsidian/vault/knowledge/* ~/Documents/Personal_AI_powerhouse/personal-ai-space/intake/staging/

# Organize into subfolders if needed
mkdir -p intake/staging/{Daily\ Notes,Life\ Plans,People}
cp ~/Obsidian/vault/daily/*.md intake/staging/Daily\ Notes/

# Watcher auto-processes entire batch in ~60s
```

### Option C: Programmatic (for future integrations)
```bash
# Drop files via script
curl -s https://obsidian-sync-api/ | tar -xz -C intake/staging/

# Watcher handles the rest
```

---

## Troubleshooting

### Watcher Not Processing

**Check if running:**
```bash
launchctl list | grep intake-watcher
```

Expected output: `- 0 com.personalai.intake-watcher` or PID number

**Restart if needed:**
```bash
launchctl unload ~/Library/LaunchAgents/com.personalai.intake-watcher.plist
launchctl load ~/Library/LaunchAgents/com.personalai.intake-watcher.plist
```

### Files Not Routed Correctly

Check `intake/intake.log` for detailed import records:
```bash
tail -50 intake/intake.log | grep "filename"
```

Look for `"status": "SUCCESS"` vs `"status": "ERROR"`

### Service Keeps Crashing

Check launchd logs:
```bash
log stream --predicate 'eventMessage contains[c] "intake-watcher"' --level debug
```

---

## What's Automated

✅ File monitoring (every 10 seconds)  
✅ Change detection (batch debounce 60 seconds)  
✅ Intake processing (runs automatically)  
✅ File routing (by tag/folder/filename)  
✅ Audit logging (all imports tracked)  
✅ Service restart (if crashes)  
✅ Boot persistence (survives reboot)  

---

## What's NOT Automated (Yet)

❌ Learning inference (run manually or on schedule)  
❌ Knowledge indexing (run manually or on schedule)  
❌ Pattern analysis (run manually or on schedule)  
❌ Report generation (run manually or on schedule)  

---

## Integration with Learning System

Every auto-processed file is observed by the learning system:

1. File added to staging
2. Watcher triggers intake processor
3. Files routed to destinations
4. Observer logs the import event
5. Next learning inference picks it up
6. Patterns adapt based on new data

---

## Summary

**Your intake system is now hands-free.** Just copy files to staging and the system handles everything:
- Detects new files
- Waits for batch completion (60 sec debounce)
- Routes to correct locations
- Logs everything for audit
- Integrates with learning system

**No manual commands needed.**

