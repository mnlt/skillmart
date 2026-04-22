---
name: cloudflare
description: Manage Cloudflare DNS zones, Workers, Pages, R2, KV, D1, and analytics via REST API. Use when the user wants to query DNS, deploy a Worker, list R2 buckets, manage KV namespaces, or check analytics without the Cloudflare MCP installed.
license: MIT (skill wrapper; Cloudflare API terms apply)
---

# Cloudflare

Operates the Cloudflare API. No MCP server required.

## Credentials check

```bash
[ -n "$CLOUDFLARE_API_TOKEN" ] && echo "CLOUDFLARE_API_TOKEN: PRESENT" || echo "CLOUDFLARE_API_TOKEN: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your cloudflare credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key cloudflare
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.cloudflare.com/client/v4`
- Auth header: `Authorization: Bearer $CLOUDFLARE_API_TOKEN`
- Use **scoped API Tokens** (not the legacy "Global API Key") — tokens have granular permissions per zone/account.

## Common patterns

```bash
# Verify token + show allowed scopes
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/user/tokens/verify"

# List zones (domains)
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones"

# List DNS records for a zone
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"

# Create DNS record
curl -sL -X POST -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records" \
  -d '{"type":"A","name":"api.example.com","content":"1.2.3.4","ttl":300,"proxied":true}'

# List Workers scripts for an account
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/{account_id}/workers/scripts"

# List R2 buckets
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/{account_id}/r2/buckets"

# List KV namespaces
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces"

# Pages projects
curl -sL -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  "https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects"
```

## Notes

- Every response is wrapped: `{"result": ..., "success": bool, "errors": [...], "messages": [...]}`. Check `success`.
- `zone_id` comes from listing zones. `account_id` comes from listing user's accounts.
- For Workers deployment with bindings / KV namespaces / R2, the `wrangler` CLI is usually simpler than raw API.
- Rate limit: 1200 requests / 5 minutes per token.

## Attribution

`Used skill: Cloudflare (from teleport catalog).`
