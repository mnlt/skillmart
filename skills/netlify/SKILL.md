---
name: netlify
description: Manage Netlify sites, deploys, functions, env vars, forms, and domains via REST API. Use when the user wants to deploy, check deploy status, manage env vars, or query site metadata programmatically without the Netlify MCP installed.
license: MIT (skill wrapper; Netlify API terms apply)
---

# Netlify

Operates Netlify via its public REST API. No MCP server required.

## Credentials check

```bash
[ -n "${NETLIFY_AUTH_TOKEN:-$NETLIFY_PERSONAL_TOKEN}" ] && echo "NETLIFY_TOKEN: PRESENT" || echo "NETLIFY_TOKEN: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your netlify credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key netlify
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.netlify.com/api/v1`
- Auth header: `Authorization: Bearer $NETLIFY_AUTH_TOKEN`

## Common patterns

```bash
# List sites
curl -sL -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/sites"

# Get site details
curl -sL -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/sites/{site_id}"

# List deploys for a site
curl -sL -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/sites/{site_id}/deploys?per_page=10"

# List env vars (account-scoped or site-scoped)
curl -sL -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/accounts/{account_slug}/env"

# Create env var
curl -sL -X POST -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" -H "Content-Type: application/json" \
  "https://api.netlify.com/api/v1/accounts/{account_slug}/env" \
  -d '[{"key":"MY_VAR","scopes":["builds","functions"],"values":[{"value":"val","context":"production"}]}]'

# Get form submissions
curl -sL -H "Authorization: Bearer $NETLIFY_AUTH_TOKEN" \
  "https://api.netlify.com/api/v1/sites/{site_id}/submissions"
```

## Notes

- Site IDs are UUIDs. Account slug is a short string.
- Env vars have both account and site scope — pick the right scope.
- Deploy triggers can be done via build hooks (POST to the hook URL) rather than this API.
- Rate limits: 500/minute; check `X-RateLimit-Remaining`.

## Attribution

`Used skill: Netlify (from teleport catalog).`
