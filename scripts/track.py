#!/usr/bin/env python3
"""Track operations tickets (GitHub issues) that follow the ticket issue form.

Reads issues via the `gh` CLI (or a bundled sample file in --demo mode),
parses the `### Urgency` and `### Needed by` sections out of each issue body,
and prints a table sorted by urgency, then due date, flagging anything
OVERDUE or due TODAY.

Examples:
    python3 scripts/track.py                  # open tickets I authored or am assigned to
    python3 scripts/track.py --all            # every open ticket in the repo
    python3 scripts/track.py 123 130          # specific tickets
    python3 scripts/track.py --since 2026-03-01
    python3 scripts/track.py --demo --today 2026-03-16   # offline, sample data

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
FIELDS = "number,title,state,assignees,author,body,comments,updatedAt,url"
URGENCY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
FAR_FUTURE = dt.date(9999, 12, 31)


# --------------------------------------------------------------------------- config

def load_config(path: Optional[str], demo: bool) -> dict:
    """Load config.json (or an explicit --config). Demo mode falls back to the example."""
    candidates = [Path(path)] if path else [ROOT / "config.json"]
    if demo and not path:
        candidates.append(ROOT / "config.example.json")
    for p in candidates:
        if p.is_file():
            with p.open(encoding="utf-8") as f:
                return json.load(f)
    sys.exit(
        f"No config found ({', '.join(str(c) for c in candidates)}).\n"
        "Copy config.example.json to config.json and fill in your repo and login."
    )


# --------------------------------------------------------------------------- fetching

def gh_json(args: list[str]) -> object:
    """Run a gh command that prints JSON and return the parsed result."""
    try:
        out = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("The GitHub CLI (gh) is not installed. See https://cli.github.com/")
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip()
        if "auth" in msg.lower() or "login" in msg.lower():
            msg += "\nRun `gh auth login` and try again."
        sys.exit(f"gh failed: {msg}")
    return json.loads(out.stdout or "null")


def fetch_live(repo: str, me: str, args: argparse.Namespace) -> list[dict]:
    """Fetch issues from GitHub according to the selected mode."""
    base = ["-R", repo, "--json", FIELDS]
    if args.numbers:
        return [gh_json(["issue", "view", str(n), *base]) for n in args.numbers]

    state = "all" if args.since else "open"
    listing = ["issue", "list", *base, "--state", state, "--limit", "500"]
    if args.since:
        listing += ["--search", f"updated:>={args.since}"]
    if args.all:
        return gh_json(listing)
    # Default: authored by me OR assigned to me. gh can't OR these, so merge two calls.
    authored = gh_json(listing + ["--author", me])
    assigned = gh_json(listing + ["--assignee", me])
    return dedupe(authored + assigned)


def fetch_demo(me: str, args: argparse.Namespace) -> list[dict]:
    """Load sample/issues.json and apply the same filters locally."""
    with (ROOT / "sample" / "issues.json").open(encoding="utf-8") as f:
        issues = json.load(f)
    if args.numbers:
        wanted = set(args.numbers)
        return [i for i in issues if i["number"] in wanted]
    if args.since:
        issues = [i for i in issues if i["updatedAt"][:10] >= args.since]
    else:
        issues = [i for i in issues if i["state"] == "OPEN"]
    if not args.all:
        issues = [i for i in issues if is_mine(i, me)]
    return issues


def is_mine(issue: dict, me: str) -> bool:
    author = (issue.get("author") or {}).get("login")
    return author == me or me in logins(issue.get("assignees"))


def dedupe(issues: list[dict]) -> list[dict]:
    seen: dict[int, dict] = {}
    for i in issues:
        seen.setdefault(i["number"], i)
    return list(seen.values())


# --------------------------------------------------------------------------- parsing

def section(body: str, heading: str) -> str:
    """Return the text under `### <heading>` up to the next heading ('' if absent)."""
    m = re.search(
        rf"^###\s*{re.escape(heading)}[^\n]*\n(.*?)(?=^###\s|\Z)",
        body or "",
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    text = m.group(1).strip() if m else ""
    return "" if text in ("_No response_", "N/A") else text


def parse_urgency(body: str) -> str:
    m = re.search(r"\bP[0-3]\b", section(body, "Urgency"))
    return m.group(0) if m else "-"


def parse_due(body: str) -> Optional[dt.date]:
    m = re.search(r"\d{4}-\d{2}-\d{2}", section(body, "Needed by"))
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(0))
    except ValueError:
        return None


def logins(people) -> list[str]:
    return [p.get("login", "?") for p in (people or [])]


# --------------------------------------------------------------------------- output

def build_rows(issues: list[dict], today: dt.date) -> list[dict]:
    rows = []
    for i in issues:
        body = i.get("body") or ""
        urg, due = parse_urgency(body), parse_due(body)
        is_open = i.get("state") == "OPEN"
        due_txt = due.isoformat() if due else "-"
        if is_open and due:
            if due < today:
                due_txt += " OVERDUE"
            elif due == today:
                due_txt += " TODAY"
        comments = i.get("comments") or []
        last = comments[-1] if comments else None
        last_txt = (
            f"{(last.get('author') or {}).get('login', '?')} {last.get('createdAt', '')[:10]}"
            if last else "-"
        )
        rows.append({
            "sort": (URGENCY_RANK.get(urg, 9), due or FAR_FUTURE, i["number"]),
            "#": str(i["number"]),
            "St": "O" if is_open else "C",
            "Urg": urg,
            "Needed by": due_txt,
            "Assignees": ",".join(logins(i.get("assignees"))) or "-",
            "Cmts": str(len(comments)),
            "Last comment": last_txt,
            "Title": (i.get("title") or "")[:80],
        })
    rows.sort(key=lambda r: r["sort"])
    return rows


def print_table(rows: list[dict]) -> None:
    cols = ["#", "St", "Urg", "Needed by", "Assignees", "Cmts", "Last comment", "Title"]
    widths = {c: max([len(c)] + [len(r[c]) for r in rows]) for c in cols}
    line = lambda r: "  ".join(r[c].ljust(widths[c]) for c in cols).rstrip()
    print(line({c: c for c in cols}))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows:
        print(line(r))
    print(f"\n{len(rows)} ticket(s)")


# --------------------------------------------------------------------------- main

def iso_date(s: str) -> str:
    try:
        dt.date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {s!r}")
    return s


def main() -> None:
    ap = argparse.ArgumentParser(description="Track operations tickets on GitHub.")
    ap.add_argument("numbers", nargs="*", type=int, help="specific issue numbers")
    ap.add_argument("--all", action="store_true", help="all open tickets, not just mine")
    ap.add_argument("--since", type=iso_date, metavar="YYYY-MM-DD",
                    help="tickets (open or closed) updated on/after this date")
    ap.add_argument("--config", metavar="PATH", help="config file (default: config.json)")
    ap.add_argument("--demo", action="store_true",
                    help="read sample/issues.json instead of calling gh")
    ap.add_argument("--today", type=iso_date, metavar="YYYY-MM-DD",
                    help="pretend today is this date (for reproducible output)")
    args = ap.parse_args()

    cfg = load_config(args.config, args.demo)
    me = cfg.get("me", "")
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    issues = fetch_demo(me, args) if args.demo else fetch_live(cfg["repo"], me, args)
    print_table(build_rows(issues, today))


if __name__ == "__main__":
    main()
