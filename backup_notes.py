#!/usr/bin/env python3
"""Daily backup: pull Monologue notes via the CLI and write them to an
Obsidian vault as one markdown file per note. Incremental via a status file."""

import json
import os
import re
import subprocess
import sys
import zoneinfo
from datetime import datetime, timezone
from pathlib import Path

# ─── Configure ──────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.expanduser(
    os.environ.get("MONOLOGUE_OUTPUT_DIR", "~/Documents/hivemind/Voice")
)
CLI_PATH = os.path.expanduser(os.environ.get("MONOLOGUE_CLI", "~/.local/bin/monologue"))
STATUS_FILE = os.path.expanduser("~/.monologue-backup-status.json")
TIMEZONE = os.environ.get("MONOLOGUE_TIMEZONE", "America/New_York")

DRY_RUN = "--dry-run" in sys.argv
FORCE_FULL = "--full" in sys.argv


def read_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def write_status(success, saved=0, last_synced=None, error=None):
    prev = read_status()
    status = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "saved_count": saved,
    }
    if last_synced:
        status["last_synced"] = last_synced
    elif prev.get("last_synced"):
        status["last_synced"] = prev["last_synced"]
    if error:
        status["error"] = error
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        print(f"Warning: status write failed: {e}")


def safe_title(title):
    safe = "".join(c for c in title if c.isalnum() or c in " -_").strip()
    return safe.replace(" ", "_")[:100] or "Untitled"


def fetch_notes(updated_after=None):
    cmd = [CLI_PATH, "notes", "all"]
    if updated_after:
        cmd.extend(["--updated-after", updated_after])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        print(f"ERROR: monologue CLI not found at {CLI_PATH}")
        return None
    except subprocess.TimeoutExpired:
        print("ERROR: CLI timed out")
        return None
    if r.returncode != 0:
        print(f"ERROR: CLI returned {r.returncode}: {r.stderr.strip()}")
        return None
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        print(f"ERROR: could not parse CLI output: {e}")
        return None
    return data.get("items", []) if isinstance(data, dict) else data


def fetch_note_detail(note_id):
    try:
        r = subprocess.run(
            [CLI_PATH, "notes", "get", note_id],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def save_note(note, local_tz):
    title = note.get("title") or "Untitled Note"
    created_at = note["created_at"]
    if created_at.endswith("Z"):
        created_at = created_at[:-1] + "+00:00"
    local_dt = datetime.fromisoformat(created_at).astimezone(local_tz)

    date_only = local_dt.strftime("%Y-%m-%d")
    time_only = local_dt.strftime("%H%M")
    filename = f"{date_only}_{time_only}_{safe_title(title)}.md"
    out = Path(OUTPUT_DIR) / local_dt.strftime("%Y")

    if (out / filename).exists():
        print(f"  exists: {filename}")
        return False

    summary = (note.get("summary") or "").strip()
    transcript = (note.get("transcript") or "").strip()
    duration = note.get("duration")

    md = [
        "---",
        f"date: '[[{date_only}]]'",
        f'time: "{local_dt.strftime("%H:%M")}"',
        "source: monologue",
        f"monologue_id: {note['note_id']}",
        "---",
        "",
        f"# {title}",
        "",
        f"**Date:** {local_dt.strftime('%Y-%m-%d %H:%M %Z')}",
    ]
    if duration:
        md.append(f"**Duration:** {int(duration)}s")
    md += [
        "",
        "---",
        "",
        "## Summary",
        "",
        summary or "_(no summary)_",
        "",
        "---",
        "",
        "## Transcript",
        "",
        transcript or "_(no transcript)_",
        "",
    ]

    if DRY_RUN:
        print(f"  [dry-run] would save: {out / filename}")
        return True

    out.mkdir(parents=True, exist_ok=True)
    (out / filename).write_text("\n".join(md), encoding="utf-8")
    print(f"  saved: {filename}")
    return True


def main():
    local_tz = zoneinfo.ZoneInfo(TIMEZONE)
    print(f"=== Monologue Backup ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ===")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Timezone: {local_tz}")

    status = read_status()
    updated_after = None if FORCE_FULL else status.get("last_synced")
    print(f"{'Incremental since' if updated_after else 'Full sync'}: {updated_after or '(no prior sync)'}")

    items = fetch_notes(updated_after=updated_after)
    if items is None:
        write_status(success=False, error="CLI fetch failed")
        sys.exit(1)

    print(f"Found: {len(items)} note(s)")
    if not items:
        write_status(success=True, saved=0,
                     last_synced=datetime.now(timezone.utc).isoformat())
        return

    saved = 0
    max_updated = None
    for item in items:
        title = item.get("title") or "Untitled"
        print(f"\n{title}")
        detail = fetch_note_detail(item["note_id"])
        if not detail:
            print("  skip: detail fetch failed")
            continue
        try:
            if save_note(detail, local_tz):
                saved += 1
        except Exception as e:
            print(f"  ERROR: {e}")
        updated_at = item.get("updated_at") or item.get("created_at")
        if updated_at and (max_updated is None or updated_at > max_updated):
            max_updated = updated_at

    print(f"\nSaved: {saved}")
    if not DRY_RUN:
        write_status(success=True, saved=saved,
                     last_synced=max_updated or datetime.now(timezone.utc).isoformat())


if __name__ == "__main__":
    main()
