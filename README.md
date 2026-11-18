# github-ticket-desk

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill for running an
operations team's ticket queue as **GitHub issues that follow a fixed issue form**,
plus a small Python tracker that tells you what's overdue, due today, or waiting on you.

You talk to Claude in plain language ("raise a ticket for Bob: certificates show the
wrong duration, need it by Friday") and it files a complete, consistently structured
issue. Ask "track my tickets" and you get a prioritised summary instead of a wall of
notifications.

## Why

It started with an education operations team that handled certificates, exam
registration, learner and coordinator portals, and reporting. Requests came in as
chat messages like "the certificate thing is broken again", and developers then had
to come back with questions: which page? which account? broken how? and how would
anyone know it was fixed?

A **form-based ticket** fixes that. Every ticket answers the same questions:

- **What's needed?**, **Full URL(s)** and **Logged in as**, so it can be reproduced
- **Expected result — how do we verify it's done?**, so closing it is a check, not an opinion
- **Categories**, **Urgency** (P0–P3) and **Needed by**, so it can be routed and prioritised

Forms are tedious to fill in by hand, though. This skill lets Claude fill them in
from a one-line request, and the tracker reads the same fields back out.

## Features

- **Create tickets** with the exact issue-form headings. Claude looks for related or
  duplicate issues first, infers categories and the assignee from your team table,
  turns "tomorrow" into a date, defaults sensibly (P2, screenshot N/A), and asks only
  for what it really can't work out.
- **Update tickets**: comment, assign, label, close or reopen. Claude only edits the body
  of tickets you wrote and shows you a comment before posting it.
- **Track tickets** with `scripts/track.py`: open tickets you wrote or are assigned to,
  sorted by urgency and then due date, with **OVERDUE** and **TODAY** flags and the latest
  commenter. Claude then summarises: what's late, who replied and what they said, which
  P0/P1s have had no response, and what to do next.
- **Issue form included**: `templates/operations_ticket.yml` produces the same headings
  on GitHub's web UI.
- **Offline demo**: `--demo` runs the tracker on bundled sample tickets, without `gh`
  or a GitHub account.
- Standard library only (Python 3.9+), apart from the `gh` CLI for live use.

## Install

```bash
git clone https://github.com/lakshmi0511/github-ticket-desk.git ~/.claude/skills/github-ticket-desk
```

Claude Code picks up skills in `~/.claude/skills/` automatically. For live use you also
need the [GitHub CLI](https://cli.github.com/), logged in with `gh auth login`.

## Configure

```bash
cd ~/.claude/skills/github-ticket-desk
cp config.example.json config.json   # config.json is git-ignored
```

Edit `config.json`:

| Key | What it is |
| --- | --- |
| `repo` | Your tickets repo, e.g. `acme-edu/operations` |
| `me` | Your GitHub login |
| `people` | Team members: spoken name, GitHub login, and the areas they usually handle |
| `categories` | Checkbox options in the form, also used as labels |
| `urgency` | P0–P3 labels exactly as written in the form |

To get the form on GitHub, copy `templates/operations_ticket.yml` into your repo's
`.github/ISSUE_TEMPLATE/` folder. If you change categories or urgency labels, change
them in both the form and `config.json`.

## Try the demo

```bash
python3 scripts/track.py --demo --today 2026-03-16
```

`--demo` reads `sample/issues.json` (ten made-up tickets in the same JSON shape `gh`
returns) and `--today` fixes the date so the output is reproducible:

```
#    St  Urg  Needed by           Assignees                  Cmts  Last comment           Title
---  --  ---  ------------------  -------------------------  ----  ---------------------  ------------------------------------------------------------------------------
142  O   P0   2026-03-16 TODAY    bob-ops,alice-dev          1     alice-dev 2026-03-16   Mar 2026 exams: exam form rejects valid ID numbers — all learners
141  O   P1   2026-03-13 OVERDUE  bob-ops                    2     bob-ops 2026-03-14     Jan 2026 term: certificates show wrong course duration — all 8-week courses
147  O   P1   2026-03-16 TODAY    dan-infra                  0     -                      Security: rotate shared admin password after staff change — admin console
143  O   P1   2026-03-18          you-github-login           1     erin-coord 2026-03-11  Apr 2026 term: bulk-enrol coordinator upload times out — files over 2,000 rows
144  O   P2   2026-03-12 OVERDUE  carol-data                 1     carol-data 2026-03-09  Jan 2026 term: monthly enrolment report missing two regions — Feb report
146  O   P2   2026-03-20          farah-qb,you-github-login  2     farah-qb 2026-03-15    Question bank: duplicate questions in week 3 quizzes — Data Science course
145  O   P3   2026-03-31          alice-dev                  0     -                      Website: update FAQ page with new exam fee — fee change

7 ticket(s)
```

Other modes (these work with `--demo` too):

```bash
python3 scripts/track.py --all                 # every open ticket, not just yours
python3 scripts/track.py 141 146               # specific tickets
python3 scripts/track.py --since 2026-03-01    # open or closed, updated since a date
python3 scripts/track.py --config other.json   # use a different config
```

From that table, Claude's summary would point out that #142 (P0) and #147 are due
today and #147 has had no response; that #141 is overdue but Bob is waiting for you
to spot-check three certificates; and that Farah asked a question on #146.

## Example prompts

- "Raise a ticket for Alice: the FAQ still shows the old exam fee, low priority, end of month."
- "File a P0: learners can't submit the exam form if their ID has a hyphen. Assign Bob and Alice, needed today."
- "Track my tickets." / "What's overdue?" / "Anything new on my tickets?"
- "What's the status of #141?"
- "Tell Bob the three certificates look fine and he can regenerate the rest."
- "Reassign #144 to Carol and add the Reporting label."
- "Close #149, the learner confirmed."

## Layout

```
github-ticket-desk/
├── SKILL.md                       # instructions Claude follows (create / update / track)
├── scripts/
│   └── track.py                   # ticket tracker (gh or --demo)
├── templates/
│   └── operations_ticket.yml      # GitHub issue form with the matching headings
├── sample/
│   └── issues.json                # made-up tickets for the offline demo
├── config.example.json            # copy to config.json and edit
├── LICENSE                        # MIT
└── README.md
```

## License

MIT, see [LICENSE](LICENSE).
