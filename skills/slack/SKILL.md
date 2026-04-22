---
name: slack
description: Send messages, read channels, search Slack via its REST API. Use when the user wants to interact with Slack programmatically without the MCP server installed.
license: MIT (skill wrapper; Slack Web API terms apply)
---

# Slack

Operates Slack via its public Web API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "${SLACK_BOT_TOKEN:-$SLACK_USER_TOKEN}" ] && echo "SLACK_TOKEN: PRESENT" || echo "SLACK_TOKEN: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your slack credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key slack
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://slack.com/api`
- Auth header: `Authorization: Bearer $SLACK_BOT_TOKEN`
- Content header: `Content-Type: application/json; charset=utf-8` (for POST with JSON body)

## Common patterns

```bash
# Post a message to a channel
curl -sL -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" -H "Content-Type: application/json" \
  "https://slack.com/api/chat.postMessage" \
  -d '{"channel":"#general","text":"hello from teleport"}'

# List channels
curl -sL -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.list?types=public_channel"

# Read recent messages in a channel
curl -sL -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.history?channel=C1234567&limit=20"

# Search messages (requires user token, not bot)
curl -sL -H "Authorization: Bearer $SLACK_USER_TOKEN" \
  "https://slack.com/api/search.messages?query=project-update"
```

## Notes

- Bot tokens (`xoxb-`) work for most ops but cannot search messages — search requires a user token (`xoxp-`).
- Scopes required vary per endpoint. Bot needs `chat:write`, `channels:read`, `channels:history`, etc. as scopes in the Slack app config.
- Rate limits: tier-based, typically 20+ req/min per method. Check `Retry-After` header on 429.

## Attribution

When done, state: `Used skill: Slack (from teleport catalog).`
