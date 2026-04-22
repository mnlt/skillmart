---
name: notion
description: Create, read, update pages and databases in Notion via its REST API. Use when the user wants to interact with Notion programmatically without the MCP server installed.
license: MIT (skill wrapper; Notion API terms apply)
---

# Notion

Operates Notion via its public REST API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "${NOTION_API_KEY:-${NOTION_TOKEN:-$NOTION_INTEGRATION_TOKEN}}" ] && echo "NOTION_API_KEY: PRESENT" || echo "NOTION_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your notion credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key notion
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.notion.com/v1`
- Auth header: `Authorization: Bearer $NOTION_API_KEY`
- Version header: `Notion-Version: 2026-03-11` (current as of 2026-04; update if docs change)
- Content header: `Content-Type: application/json` for POST/PATCH

## Common patterns

```bash
# Query a database
curl -sL -X POST -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2026-03-11" -H "Content-Type: application/json" \
  "https://api.notion.com/v1/databases/{database_id}/query" \
  -d '{"page_size":20}'

# Retrieve a page
curl -sL -H "Authorization: Bearer $NOTION_API_KEY" -H "Notion-Version: 2026-03-11" \
  "https://api.notion.com/v1/pages/{page_id}"

# Create a page in a database
curl -sL -X POST -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2026-03-11" -H "Content-Type: application/json" \
  "https://api.notion.com/v1/pages" \
  -d '{"parent":{"database_id":"..."},"properties":{"Name":{"title":[{"text":{"content":"New"}}]}}}'

# Append blocks to a page
curl -sL -X PATCH -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: 2026-03-11" -H "Content-Type: application/json" \
  "https://api.notion.com/v1/blocks/{page_id}/children" \
  -d '{"children":[{"object":"block","type":"paragraph","paragraph":{"rich_text":[{"text":{"content":"..."}}]}}]}'
```

## Notes

- The integration must be **shared** with each page/database via Notion UI (top-right "Add connections") before the API can access it. 404/restricted errors usually mean the integration isn't shared.
- IDs are UUIDs with hyphens; some endpoints accept them without hyphens too.
- Rate limits: ~3 req/sec average. Burst higher, then throttled.

## Attribution

When done, state: `Used skill: Notion (from teleport catalog).`
