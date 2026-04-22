---
name: posthog
description: Query PostHog product analytics — events, insights, feature flags, experiments, session replays, funnels — via REST API. Use when the user wants to check analytics, toggle a feature flag, query events, or inspect experiment results programmatically without the PostHog MCP installed.
license: MIT (skill wrapper; PostHog API terms apply)
---

# PostHog

Operates PostHog via its public REST API. No MCP server required.

## Credentials check

```bash
[ -n "${POSTHOG_PERSONAL_API_KEY:-$POSTHOG_API_KEY}" ] && echo "POSTHOG_API_KEY: PRESENT" || echo "POSTHOG_API_KEY: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your posthog credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key posthog
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL (US cloud): `https://us.posthog.com/api`
- Base URL (EU cloud): `https://eu.posthog.com/api`
- Self-hosted: `https://{your-posthog-host}/api`
- Auth header: `Authorization: Bearer $POSTHOG_PERSONAL_API_KEY`
- Key format: `phx_*`

**Important:** confirm with the user which instance (US vs EU). Asking the wrong instance returns 401.

## Common patterns

```bash
# List projects
curl -sL -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  "https://us.posthog.com/api/projects/"

# List recent events
curl -sL -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  "https://us.posthog.com/api/projects/{project_id}/events/?limit=20"

# Run a HogQL query (SQL-ish over events)
curl -sL -X POST -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" -H "Content-Type: application/json" \
  "https://us.posthog.com/api/projects/{project_id}/query/" \
  -d '{"query":{"kind":"HogQLQuery","query":"SELECT count() FROM events WHERE event=$pageview AND timestamp > now() - INTERVAL 7 DAY"}}'

# List feature flags
curl -sL -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  "https://us.posthog.com/api/projects/{project_id}/feature_flags/"

# Toggle a feature flag
curl -sL -X PATCH -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" -H "Content-Type: application/json" \
  "https://us.posthog.com/api/projects/{project_id}/feature_flags/{flag_id}/" \
  -d '{"active":true}'

# List experiments
curl -sL -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  "https://us.posthog.com/api/projects/{project_id}/experiments/"

# List insights (saved charts)
curl -sL -H "Authorization: Bearer $POSTHOG_PERSONAL_API_KEY" \
  "https://us.posthog.com/api/projects/{project_id}/insights/"
```

## Notes

- Personal API keys (`phx_*`) are for admin/management operations. Don't confuse with Project API Keys (`phc_*`) which are public (client SDK ingestion).
- HogQL is PostHog's SQL dialect for event analytics — very powerful.
- Rate limit: 240 req/min per team.
- For high-volume event ingestion, use the client SDKs, not this REST API.

## Attribution

`Used skill: PostHog (from teleport catalog).`
