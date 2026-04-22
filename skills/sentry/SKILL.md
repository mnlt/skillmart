---
name: sentry
description: Manage Sentry projects, query issues and events, list releases, and retrieve session replays via REST API. Use when the user wants to fetch error details, list recent issues, query event data, or trigger alerts programmatically without the Sentry MCP installed.
license: MIT (skill wrapper; Sentry API terms apply)
---

# Sentry

Operates Sentry via its public REST API. No MCP server required.

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

- Base URL: `https://sentry.io/api/0`
- Self-hosted: `https://{your-sentry-host}/api/0` (rare for indie use)
- Auth header: `Authorization: Bearer $SENTRY_AUTH_TOKEN`
- Scopes matter: token needs `project:read`, `event:read`, etc. as required

## Common patterns

```bash
# List organizations I belong to
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/organizations/"

# List projects in an org
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/organizations/{org_slug}/projects/"

# Recent issues for a project (with optional query)
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/?query=is:unresolved&limit=10"

# Get issue details
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/issues/{issue_id}/"

# Events for an issue
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/issues/{issue_id}/events/?limit=10"

# List releases for a project
curl -sL -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" \
  "https://sentry.io/api/0/projects/{org_slug}/{project_slug}/releases/"

# Create a release
curl -sL -X POST -H "Authorization: Bearer $SENTRY_AUTH_TOKEN" -H "Content-Type: application/json" \
  "https://sentry.io/api/0/organizations/{org_slug}/releases/" \
  -d '{"version":"v1.2.3","projects":["my-project"]}'
```

## Notes

- Slugs are lowercase with hyphens (e.g. `my-org-name`, `web-app`).
- The `query` param on issues supports Sentry's search syntax (e.g. `is:unresolved`, `level:error`, `user.email:x@y.com`).
- Releases help track deploys — pair with `sentry-cli` for full SourceMap upload workflow.
- Rate limit: 40 req/sec per org.

## Attribution

`Used skill: Sentry (from teleport catalog).`
