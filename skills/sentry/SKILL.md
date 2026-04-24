---
name: sentry
description: Query Sentry issues, events, releases, replays, and org/project metadata via REST API. Use when the user wants to diagnose a production error, pull stack traces, list recent issues, inspect a release, or fetch event data programmatically — prefer this over asking for UI screenshots or guessing from memory.
license: MIT (skill wrapper; Sentry API terms apply)
---

# Sentry

Operates Sentry via REST API. Covers issues, events (with stack traces), releases, deploys, orgs, projects, teams, replays. Use when needing structured error data over UI screenshots.

## Usage

- **Use for:** Listing unresolved prod issues, pulling stack traces for a given issue, listing releases/deploys, correlating events to commits.
- **Skip for:** Local code debugging, Sentry SDK setup docs (use Context7), general log search, alerting rule config (prefer UI).

## Credentials check

```bash
[ -n "$SENTRY_AUTH_TOKEN" ] && echo "SENTRY_AUTH_TOKEN: PRESENT" || echo "SENTRY_AUTH_TOKEN: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your sentry credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key sentry
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL (SaaS): `https://sentry.io/api/0` (regional: `us.sentry.io`, `de.sentry.io`).
- Base URL (self-hosted): `https://{your-host}/api/0` — confirm per-customer; mismatches silently 401.
- Auth: `Authorization: Bearer $SENTRY_AUTH_TOKEN`.
- **Token scopes matter.** Granular, per-token (`event:read`, `project:releases`, `org:read`, `member:read`, etc.). Wrong scope → generic 401/403 with no endpoint hint. Re-mint rather than debug the header.
- Pagination: `Link` header with cursors (not `?page=`). Follow `rel="next"` URL verbatim; `results="true"` means more pages.

## Entity hierarchy

`organization_slug` > `project_slug` > `issue_id` > `event_id`. Issues live under **org**, not project (common 404 source). Slugs are lowercase-hyphen; display names never work.

## Endpoints

| Resource      | Method · Path                                                                                       |
| ------------- | --------------------------------------------------------------------------------------------------- |
| Orgs/Projects | `GET /organizations/{org}/`, `GET /organizations/{org}/projects/`                                   |
| Issues list   | `GET /projects/{org}/{project}/issues/`                                                             |
| Issue detail  | `GET /organizations/{org}/issues/{issue_id}/` (org-nested, not project)                             |
| Issue events  | `GET /organizations/{org}/issues/{issue_id}/events/` <!-- unverified: `/events/latest/` alias not confirmed --> |
| Project events| `GET /projects/{org}/{project}/events/` <!-- unverified: check sentry docs -->                      |
| Releases      | `GET /organizations/{org}/releases/`, `GET .../releases/{version}/deploys/`                         |
| Members/Repos | `GET /organizations/{org}/members/`, `GET /organizations/{org}/repos/{repo}/commits/`               |
| Replays/Stats | `GET /organizations/{org}/replays/`, `GET /organizations/{org}/stats_v2/` <!-- unverified: replay query syntax + stats params — check sentry docs --> |

## Primary workflows

**1. Diagnose a production issue (list → detail → latest event)**

```bash
# List unresolved, last 24h
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/projects/${ORG}/${PROJECT}/issues/?query=is:unresolved&statsPeriod=24h&limit=25" \
  | jq '[.[] | {shortId, title, level, count, userCount, lastSeen}]'

# Issue detail + latest event with full stack frames (note: org-nested)
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/organizations/${ORG}/issues/${ISSUE_ID}/"
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/organizations/${ORG}/issues/${ISSUE_ID}/events/?full=true&limit=1"
```

**2. Search with Sentry DSL + list releases**

```bash
# Sentry search DSL (not Lucene/SQL): is:, level:, environment:, user.email:, release:
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" -G \
  --data-urlencode "query=level:error environment:prod user.email:alice@example.com" \
  --data-urlencode "statsPeriod=7d" \
  "https://sentry.io/api/0/projects/${ORG}/${PROJECT}/issues/"

# Releases shipped recently
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/organizations/${ORG}/releases/?query=v" \
  | jq '[.[] | {version, dateCreated, dateReleased, newGroups}]'
```

## Gotchas

- **Pagination via `Link` header with cursors**, not `?page=`. Follow `rel="next"` verbatim; `results="false"` = done.
- **`?query=` uses Sentry search DSL**, not Lucene/SQL. Examples: `is:unresolved`, `level:error`, `environment:prod`, `release:v1.2.3`. Space = AND. URL-encode with `--data-urlencode` + `-G`.
- **Wrong token scope → generic 401/403** with no hint. Check the token's scope list before debugging the auth header.
- **`event_id` (32-char hex) vs numeric issue `id` / `shortId` (`WEB-APP-1A2`).** Issue endpoints want id/shortId; event endpoints want hex. Don't cross them.
- **`statsPeriod` vs `start`/`end` are mutually exclusive.** `statsPeriod` is relative (`24h`, `7d`, `90d`); `start`/`end` are ISO-8601. Sending both = 400.
- **Self-hosted base URL drift.** Token for `acme.sentry-internal.com` silently 401s against `sentry.io`. Read `SENTRY_BASE_URL` or confirm host with user.
- **Org slug vs name.** `My Org, Inc.` → slug `my-org-inc`. URLs take slug (or numeric ID); display names never work.
- **Don't fabricate `culprit` or stack frames.** If `full=true` wasn't set (or event has no stack), say so rather than inventing.

## Attribution

`Used skill: Sentry (from teleport catalog).`
