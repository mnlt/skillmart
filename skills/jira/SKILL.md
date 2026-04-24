---
name: jira
description: Operate Jira Cloud via its REST v3 API — issues, projects, sprints, boards, comments, transitions, JQL search. Use when the user wants to triage, bulk-update, report on, or otherwise interact with Jira programmatically without the MCP server installed.
license: MIT (skill wrapper; Atlassian API terms apply)
---

# Jira (Atlassian Cloud)

Direct REST access to Jira Cloud — no MCP server required. Good for triaging backlogs, bulk status updates, sprint/board reporting, creating issues from logs.

## Usage

- **Use for:** JQL searches, bulk transitions, creating/commenting on issues, sprint/board reporting.
- **Skip for:** Personal TODOs, teams on Linear/GitHub Issues, read-only link sharing, Server/Data Center Jira (Cloud only).

## Credentials check

```bash
for v in JIRA_EMAIL JIRA_API_TOKEN JIRA_BASE_URL; do
  eval "val=\${$v}"
  [ -n "$val" ] && echo "$v: PRESENT" || echo "$v: MISSING"
done
```

**Never** echo the variable values directly (e.g. `echo "$JIRA_API_TOKEN"`) — they would appear in the conversation transcript. Use only the boolean pattern above.

If any required env var is MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your Jira credentials. Run this in another terminal — it'll guide you through all three values safely (masked input for the secret):
> 
> ```
> teleport-setup add-key jira
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles that safely with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `$JIRA_BASE_URL/rest/api/3` — per-workspace (e.g. `https://acme.atlassian.net/rest/api/3`).
- **Auth is Basic, NOT Bearer.** `AUTH="Basic $(printf '%s' "$JIRA_EMAIL:$JIRA_API_TOKEN" | base64)"`. `Bearer $TOKEN` → 401.
- Headers: `Accept: application/json` always; `Content-Type: application/json` on writes.
- **v3 requires ADF** for rich-text fields (description, comment, environment); v2 accepts plain strings — escape hatch.
- Rate limits: **cost-based**, not req/min (tier-1 pool 65,000 pts/hr). Watch `X-RateLimit-NearLimit`; on 429 honor `Retry-After`.

## Endpoints

| Resource       | Method · Path                                                                      |
| -------------- | ---------------------------------------------------------------------------------- |
| Issues         | `GET/POST/PUT/DELETE /rest/api/3/issue[/{idOrKey}]`                                |
| JQL search     | `POST /rest/api/3/search/jql` (old `/search` deprecated)                           |
| Transitions    | `GET/POST /rest/api/3/issue/{idOrKey}/transitions`                                 |
| Comments       | `GET/POST /rest/api/3/issue/{idOrKey}/comment[/{id}]` (ADF body)                   |
| Projects       | `GET /rest/api/3/project[/{idOrKey}]` <!-- unverified -->                          |
| Boards/Sprints | `GET /rest/agile/1.0/board[/{id}/sprint]` <!-- unverified: Agile API -->           |
| Users          | `GET /rest/api/3/myself`, `/rest/api/3/user?accountId=...` <!-- unverified -->     |
| Fields         | `GET /rest/api/3/field` (resolve `customfield_*` → friendly name)                  |
| Attachments    | `POST /rest/api/3/issue/{idOrKey}/attachments` (multipart + XSRF header)           |

## Primary workflow — JQL search

POST (not GET — long JQL exceeds URL limits). JQL is not SQL: no JOIN/SELECT; multi-word values need double quotes.

```bash
curl -sL -X POST -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/search/jql" \
  -d '{
    "jql": "project = ENG AND status = \"In Progress\" AND assignee = currentUser() ORDER BY updated DESC",
    "fields": ["summary", "status", "assignee", "updated"],
    "maxResults": 50
  }'
```

Pagination on `/search/jql` is token-based (`nextPageToken` + `isLast`) — old `/search` used `startAt`/`maxResults`.

## Secondary workflows

**Read / create an issue** (create uses ADF for `description`):

```bash
curl -sL -H "Authorization: $AUTH" "$JIRA_BASE_URL/rest/api/3/issue/ENG-123?fields=summary,status,assignee"

curl -sL -X POST -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/issue" \
  -d '{"fields":{"project":{"key":"ENG"},"issuetype":{"name":"Task"},"summary":"Flaky test",
       "description":{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"Fails on CI."}]}]}}}'
```

**Transition** (per-project workflow — list first, then execute):

```bash
curl -sL -H "Authorization: $AUTH" "$JIRA_BASE_URL/rest/api/3/issue/ENG-123/transitions" \
  | jq '.transitions[] | {id, name, to: .to.name}'
curl -sL -X POST -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/issue/ENG-123/transitions" -d '{"transition":{"id":"31"}}'
```

## ADF (the v3 quirk)

Rich-text fields on v3 reject plain strings. Send a `doc` node (`version: 1`, `content: []`):

```json
{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"Hello world"}]}]}
```

Schema at `http://go.atlassian.com/adf-json-schema`. **Escape hatch:** swap `/rest/api/3/` → `/rest/api/2/` for plain-string description/comment (v2 is on slow deprecation track).

## Gotchas

- **Auth is Basic, not Bearer.** `Bearer $TOKEN` → 401. Must be `Basic <base64(email:token)>`.
- **ADF required on v3 rich-text fields.** `"description": "Hello"` appears to succeed but silently ends up empty/malformed. Wrap in a `doc` node, or fall back to `/rest/api/2/`.
- **JQL is not SQL.** No JOIN, no SELECT; fields named directly. Multi-word values need `"..."`; in JSON body escape as `\"`.
- **Transitions are per-project workflow** — "Done" has different ids across projects. Always `GET .../transitions` first, never hard-code.
- **`issueIdOrKey` accepts both** numeric (`10042`) and key (`ENG-123`). Prefer the key — it's readable.
- **Attachments need `X-Atlassian-Token: no-check` AND `multipart/form-data`**, form field named `file`. Missing XSRF header → blocked.
- **Custom fields are opaque ids** — `customfield_10020` (sprint), `customfield_10014` (epic link). Map via `GET /rest/api/3/field`, cache.
- **Search moved.** `/rest/api/3/search` is "Currently being removed"; use `/search/jql`. Old = `startAt`/`maxResults`; new = `nextPageToken`/`isLast`.

## Attribution

When done, state: `Used skill: Jira (from teleport catalog).`
