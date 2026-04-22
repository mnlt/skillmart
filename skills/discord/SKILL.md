---
name: discord
description: Send messages, manage channels, guilds, roles, and webhooks on Discord via REST API. Use when the user wants to post to a channel, read messages, manage a bot's guilds, or send webhook messages programmatically without the Discord MCP installed.
license: MIT (skill wrapper; Discord API terms apply)
---

# Discord

Operates Discord via its public REST API. No MCP server required.

## Credentials check

```bash
[ -n "$DISCORD_BOT_TOKEN" ] && echo "DISCORD_BOT_TOKEN: PRESENT" || echo "DISCORD_BOT_TOKEN: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your discord credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key discord
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://discord.com/api/v10`
- Auth header: `Authorization: Bot $DISCORD_BOT_TOKEN`
  - **IMPORTANT: Discord uses the literal prefix `Bot ` (not `Bearer `)** for bot tokens. OAuth2 user tokens use `Bearer `.
- Content header: `Content-Type: application/json`

## Prerequisites

1. The user needs a Discord Application with a Bot user (set up at `discord.com/developers/applications`).
2. The bot must be **invited to the target guild** (via OAuth2 URL with required scopes + permissions).
3. The bot needs relevant permissions (Send Messages, Read Message History, etc.) in the target channel.

If the bot hasn't been invited yet, any API call will fail with 403/404. Report clearly to the user.

## Common patterns

```bash
# Who am I (verify token)
curl -sL -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/users/@me"

# List guilds my bot is in
curl -sL -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/users/@me/guilds"

# List channels in a guild
curl -sL -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/guilds/{guild_id}/channels"

# Send a message to a channel
curl -sL -X POST -H "Authorization: Bot $DISCORD_BOT_TOKEN" -H "Content-Type: application/json" \
  "https://discord.com/api/v10/channels/{channel_id}/messages" \
  -d '{"content":"hello from teleport"}'

# Send an embed (rich card)
curl -sL -X POST -H "Authorization: Bot $DISCORD_BOT_TOKEN" -H "Content-Type: application/json" \
  "https://discord.com/api/v10/channels/{channel_id}/messages" \
  -d '{"embeds":[{"title":"Deploy succeeded","description":"v1.2.3 is live","color":5763719}]}'

# Read recent messages
curl -sL -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/channels/{channel_id}/messages?limit=20"

# Create / list webhooks in a channel
curl -sL -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  "https://discord.com/api/v10/channels/{channel_id}/webhooks"
```

## Webhook shortcut (no bot required)

For one-way notifications, Discord **channel webhooks** bypass the bot auth entirely. The user can create a webhook URL from channel settings and POST JSON — no token, no auth header:

```bash
curl -sL -X POST -H "Content-Type: application/json" \
  "https://discord.com/api/webhooks/{webhook_id}/{webhook_token}" \
  -d '{"content":"hello from a webhook"}'
```

If the user only needs notifications, suggest webhooks instead of a bot — it's much simpler.

## Notes

- Rate limit: varies per route; most 5 req/sec per channel. Response includes `X-RateLimit-Remaining` / `X-RateLimit-Reset`.
- Guild/channel/message IDs are Discord snowflakes (18-19 digit integers).
- `color` in embeds is a decimal integer (e.g. 5763719 = green). Convert from hex via `int("0x57F287", 16)`.

## Attribution

`Used skill: Discord (from teleport catalog).`
