---
name: github-ticket-desk
description: Create, update and track operations tickets (GitHub issues that follow a fixed issue-form template) in the team's configured repo. Use this whenever the user wants to create, raise, file or log a ticket, comment on a ticket, assign or reassign it, add labels, close or reopen it, follow up on tickets, or asks what's pending, overdue or updated — "track my tickets", "what's overdue", "anything new on my tickets", "status of #123" — even if they don't say "GitHub" or "issue".
---

# GitHub Ticket Desk

Run an operations team's ticket queue as GitHub issues. Every ticket follows the
same issue form so that each request says exactly what is needed, where, and how
to verify it is done.

## Config

Read `config.json` in this skill's folder (fall back to `config.example.json`
and tell the user to create their own). It holds:

- `repo` — the tickets repo, e.g. `acme-edu/operations`
- `me` — the user's GitHub login
- `people` — name → login → areas they usually handle
- `categories` — the checkbox list (also used as labels)
- `urgency` — the P0–P3 labels exactly as they appear in the form

Always pass `-R <repo>` to every `gh` command. If `gh` reports an auth error,
tell the user to run `! gh auth login` and stop.

## Creating a ticket

1. **Look for related tickets first.**
   `gh issue list -R <repo> --state all --search "<key words>" --limit 15 --json number,title,state,url`
   If something looks like a duplicate, say so before creating. Otherwise mention
   related tickets in the body as `Related: #123, #130`.

2. **Fill the issue-form body** with these exact headings, in this order:

   ```
   ### What's needed?
   ### Full URL(s)
   ### Logged in as
   ### Expected result — how do we verify it's done?
   ### Full-screen screenshot
   ### Dev diagnostics (optional)
   ### Categories
   ### Urgency
   ### Needed by
   ```

   - **Categories**: a checkbox list of every category in config, `- [X]` for each
     that applies (tick all that apply), `- [ ]` for the rest.
   - **Urgency**: one of the config labels — P0 critical, P1 urgent (this week),
     P2 normal, P3 low.
   - **Needed by**: `YYYY-MM-DD`.
   - **Title**: `<Programme / month>: <what> — <scope>`,
     e.g. `Mar 2026 exams: exam form rejects valid IDs — all learners`.

   Write the body to a temp file and pass `--body-file` (never inline a long
   `--body`; quoting breaks on apostrophes and em dashes).

3. **Fill gaps sensibly.** Default urgency to P2 and screenshot to `N/A`. Convert
   "today", "tomorrow", "Friday" to absolute dates. Infer categories and the
   assignee from the people table's areas. Ask only for what you genuinely can't
   infer (usually the URL or the expected result).
   - If assignee, urgency and needed-by date were all given, create straight away.
   - Otherwise show the draft (title + body + assignee + labels) and wait for an OK.

4. **Create it**, setting labels directly from the ticked categories:
   ```
   gh issue create -R <repo> --title "<title>" --body-file <tmp> \
     --assignee <login>[,<login>] --label "<Category>,<Category>"
   ```
   If a label doesn't exist in the repo, create the ticket without it and say which.

5. **Report back**: link, title, assignees, labels, urgency, needed-by, and any
   assumptions you made (defaults, inferred dates, inferred assignee).

## People

Map spoken names ("ask Bob", "give it to the data person") to logins using
`people` in config. If a name isn't there, list who can be assigned:
`gh api repos/<repo>/assignees --jq '.[].login'`
and confirm the right login with the user before using it.

## Updating tickets

| Action | Command |
| --- | --- |
| Comment | `gh issue comment <n> -R <repo> --body-file <tmp>` |
| Assign / unassign | `gh issue edit <n> -R <repo> --add-assignee <login>` / `--remove-assignee <login>` |
| Labels | `gh issue edit <n> -R <repo> --add-label "<label>"` / `--remove-label "<label>"` |
| Close / reopen | `gh issue close <n> -R <repo> [--comment "<why>"]` / `gh issue reopen <n> -R <repo>` |
| Edit body | `gh issue edit <n> -R <repo> --body-file <tmp>` |

- Only edit the body of tickets the user authored. On anyone else's ticket, add a
  comment instead.
- Show the comment text before posting, unless the user dictated it word for word.

## Tracking

Run the tracker from this skill's folder:

```
python3 scripts/track.py              # open tickets I authored or am assigned to
python3 scripts/track.py --all        # every open ticket
python3 scripts/track.py 141 146      # specific tickets
python3 scripts/track.py --since 2026-03-01   # anything updated since a date
```

Then summarise for the user — don't just paste the table:

1. **Overdue and due today** first, with who owns each.
2. **New activity**: tickets where someone other than the user commented last.
   Read those comments (`gh issue view <n> -R <repo> --comments`) and say what
   they actually say, especially questions waiting on the user.
3. **P0/P1 with no response** (zero comments) — these need a nudge.
4. **Suggested next actions** (reply on #141, chase #147, close #149 …).

Never close, comment on or reassign anything during tracking without the
user's explicit go-ahead.
