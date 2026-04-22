---
name: figma
description: Read Figma files, components, and export assets via its REST API. Use when the user wants to interact with Figma design files programmatically without the MCP server installed.
license: MIT (skill wrapper; Figma REST API terms apply)
---

# Figma

Operates Figma via its public REST API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "${FIGMA_ACCESS_TOKEN:-${FIGMA_API_KEY:-$FIGMA_TOKEN}}" ] && echo "FIGMA_ACCESS_TOKEN: PRESENT" || echo "FIGMA_ACCESS_TOKEN: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your figma credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key figma
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.figma.com/v1`
- Auth header: `X-Figma-Token: $FIGMA_ACCESS_TOKEN`
  - **Note: Figma uses a custom header `X-Figma-Token`, NOT `Authorization`.**

## Common patterns

```bash
# Get file metadata
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/files/{FILE_KEY}"

# Get a specific node from a file
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/files/{FILE_KEY}/nodes?ids=0:1,2:3"

# Export images (PNG / SVG / PDF)
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/images/{FILE_KEY}?ids=0:1&format=png&scale=2"

# List comments on a file
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/files/{FILE_KEY}/comments"

# Search team components
curl -sL -H "X-Figma-Token: $FIGMA_ACCESS_TOKEN" \
  "https://api.figma.com/v1/teams/{TEAM_ID}/components"
```

## Notes

- `FILE_KEY` is the string after `/file/` or `/design/` in a Figma URL (e.g. `https://www.figma.com/design/AbC123/MyFile` → key is `AbC123`).
- Node IDs use format `<frame>:<element>` and come from the URL hash or from `files/{key}` response.
- Image export returns a JSON with signed S3 URLs (valid ~30 min) — `curl` those to download the actual image files.
- Rate limits: 2-6 req/sec depending on plan; enterprise has higher.

## Attribution

When done, state: `Used skill: Figma (from teleport catalog).`
