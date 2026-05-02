# monologue-to-obsidian

Sync your [Monologue](https://monologue.to) notes to an Obsidian vault as one markdown file per note. Incremental — runs as often as you want, only pulls what's new.

## Prereqs

- [Monologue toolkit CLI](https://github.com/EveryInc/monologue-toolkit) installed and authed (`monologue notes all` should work)
- Python 3.9+
- An Obsidian vault folder

## Install

```bash
git clone https://github.com/<you>/monologue-to-obsidian.git
cd monologue-to-obsidian
chmod +x backup_notes.py
```

## Configure

Set where notes should land:

```bash
export MONOLOGUE_OUTPUT_DIR="$HOME/Obsidian/MyVault/Monologue"
export MONOLOGUE_TIMEZONE="America/New_York"   # optional, defaults to ET
```

Defaults are `~/Obsidian/Monologue` and `America/New_York`.

## Run

```bash
./backup_notes.py              # incremental
./backup_notes.py --full       # ignore last-synced, pull everything
./backup_notes.py --dry-run    # show what would be written, don't write
```

## Output

```
Monologue/
└── 2026/
    └── 05/
        └── 2026-05-01_1347_Meeting_Recap.md
```

Each file:

```markdown
---
date: 2026-05-01
time: "13:47"
source: monologue
monologue_id: note_abc123
---

# Meeting Recap

**Date:** 2026-05-01 13:47 EDT
**Duration:** 1842s

---

## Summary

…

---

## Transcript

…
```

## Schedule it

**cron** (every 30 min):

```cron
*/30 * * * * /usr/bin/env python3 /path/to/monologue-to-obsidian/backup_notes.py >> /tmp/monologue.log 2>&1
```

**launchd** (macOS, on login + every hour): see Apple's `man launchd.plist`.

**Claude Code** (runs at every session start) — add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "type": "command", "command": "python3 /path/to/monologue-to-obsidian/backup_notes.py" }
        ]
      }
    ]
  }
}
```

## State

`~/.monologue-backup-status.json` — holds `last_synced`. Delete it to force a full sync (or use `--full`).

## License

MIT
