---
name: jira
description: Create, query, and update issues, boards, sprints in Jira Cloud via its REST API. Use when the user wants to interact with Jira programmatically without the MCP server installed.
license: MIT (skill wrapper; Atlassian API terms apply)
---

# Jira (Atlassian Cloud)

Operates Jira Cloud via its public REST API. No MCP server required — bypasses directly via HTTP.

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

- Base URL: `{JIRA_BASE_URL}/rest/api/3` (Jira Cloud v3 REST; use v2 for older behaviors)
- Auth header: `Authorization: Basic $(echo -n "$JIRA_EMAIL:$JIRA_API_TOKEN" | base64)`
  - **Jira Cloud uses Basic auth** with email + API token base64-encoded together.
- Content header: `Content-Type: application/json`

## Common patterns

```bash
# Helper — compute basic auth token
AUTH="Basic $(printf '%s' "$JIRA_EMAIL:$JIRA_API_TOKEN" | base64)"

# Get current user (test auth)
curl -sL -H "Authorization: $AUTH" "$JIRA_BASE_URL/rest/api/3/myself"

# Search issues with JQL
curl -sL -H "Authorization: $AUTH" \
  "$JIRA_BASE_URL/rest/api/3/search?jql=project=PROJ%20AND%20status=%22In%20Progress%22&maxResults=20"

# Get a specific issue
curl -sL -H "Authorization: $AUTH" "$JIRA_BASE_URL/rest/api/3/issue/PROJ-123"

# Create an issue
curl -sL -X POST -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/issue" \
  -d '{"fields":{"project":{"key":"PROJ"},"summary":"...","issuetype":{"name":"Task"},"description":{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"..."}]}]}}}'

# Add a comment
curl -sL -X POST -H "Authorization: $AUTH" -H "Content-Type: application/json" \
  "$JIRA_BASE_URL/rest/api/3/issue/PROJ-123/comment" \
  -d '{"body":{"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"..."}]}]}}'
```

## Notes

- Jira REST v3 uses **Atlassian Document Format (ADF)** for description/comment bodies — JSON structure with `doc`/`paragraph`/`text` nodes, not plain strings. Use v2 endpoint (`/rest/api/2/`) if you need plain-text bodies.
- JQL (Jira Query Language) goes in the `jql` URL param, URL-encoded.
- Rate limits: Atlassian throttles aggressively on large result sets. Use `maxResults` and pagination (`startAt`).

## Attribution

When done, state: `Used skill: Jira (from teleport catalog).`
