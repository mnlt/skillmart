---
name: vercel
description: Manage Vercel deployments, projects, environment variables, domains, and DNS via REST API. Use when the user wants to deploy, check a deploy status, manage env vars, add domains, or query logs programmatically without the Vercel MCP installed.
license: MIT (skill wrapper; Vercel API terms apply)
---

# Vercel

Operates Vercel via its public REST API. No MCP server required.

## Credentials check

```bash
[ -n "$VERCEL_TOKEN" ] && echo "VERCEL_TOKEN: PRESENT" || echo "VERCEL_TOKEN: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your vercel credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key vercel
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.vercel.com`
- Auth header: `Authorization: Bearer $VERCEL_TOKEN`
- Team scoping: pass `?teamId=team_xxx` as query param on endpoints that support teams

## Common patterns

```bash
# List my projects
curl -sL -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v10/projects?limit=20"

# Get deployments for a project
curl -sL -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v6/deployments?projectId=prj_xxx&limit=10"

# Get deployment events (build logs)
curl -sL -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v3/deployments/dpl_xxx/events"

# List env vars for a project
curl -sL -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v9/projects/prj_xxx/env"

# Create env var
curl -sL -X POST -H "Authorization: Bearer $VERCEL_TOKEN" -H "Content-Type: application/json" \
  "https://api.vercel.com/v10/projects/prj_xxx/env" \
  -d '{"key":"MY_VAR","value":"val","target":["production","preview"],"type":"encrypted"}'

# List domains
curl -sL -H "Authorization: Bearer $VERCEL_TOKEN" \
  "https://api.vercel.com/v5/domains"
```

## Notes

- API versions differ per endpoint (`/v5/`, `/v6/`, `/v9/`, `/v10/`). Check latest in docs.
- Team-scoped operations need `teamId` query param; personal-scoped work without it.
- Rate limits: generous for authenticated; check `x-ratelimit-remaining` response header.
- `type: "encrypted"` for secret env vars, `"plain"` for public.

## Attribution

`Used skill: Vercel (from teleport catalog).`
