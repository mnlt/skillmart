---
name: discord
description: Operate Discord via its REST API — post/read channel messages, manage guilds + roles, fire webhooks, register slash commands. Use when the user wants a bot to post to a channel, read recent history, run a community admin task, or ship one-way notifications via webhook URL without running a bot process.
license: MIT (skill wrapper; Discord API terms apply)
---

# Discord

Direct REST calls against Discord's v10 HTTP API — no MCP, no gateway. Good for bot messaging, reading history, light guild management, webhooks, registering slash commands. Does NOT receive interactions (buttons, slash invocations) — needs a public HTTPS endpoint.

## Usage

- **Use for:** Posting to channels, reading recent history, managing roles/members, firing webhooks, registering guild slash commands.
- **Skip for:** Real-time chat loops (gateway), receiving slash/button events (public HTTP handler), voice state, presence/audit-log streaming.

## Credentials check

```bash
[ -n "$DISCORD_BOT_TOKEN" ] && echo "DISCORD_BOT_TOKEN: PRESENT" || echo "DISCORD_BOT_TOKEN: MISSING"
```

**Never** echo the variable directly — the value would land in the conversation transcript.

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

- Base URL: `https://discord.com/api/v10`.
- **Auth:** `Authorization: Bot $DISCORD_BOT_TOKEN`. The literal prefix is `Bot ` (trailing space) — **NOT `Bearer`**. Wrong prefix = bare 401. Webhook execute takes no auth header (token is in URL).
- **`User-Agent` is required** — Cloudflare blocks/rate-limits missing or fake UAs before Discord sees the request. Format: `DiscordBot (https://example.com, 1.0)`.
- `Content-Type: application/json` for JSON; `multipart/form-data` for file uploads.
- Rate limits stack: per-route (`X-RateLimit-Bucket`) + global 50 req/s per bot. Watch `X-RateLimit-Remaining` / `X-RateLimit-Reset-After`; on 429 honor `Retry-After`.
- Bot must be invited to the target guild (OAuth2 URL, scopes `bot` + `applications.commands`) or every call 403/404s. Reading non-mention message content needs the **Message Content Intent** (privileged).

Examples use shorthands:

```bash
AUTH=(-H "Authorization: Bot $DISCORD_BOT_TOKEN")
UA=(-H "User-Agent: DiscordBot (https://example.com, 1.0)")
```

## Entity hierarchy

`application` (bot) → `guild` → `channel` → `message`; roles/members hang off guild. Snowflake IDs are 18–19 digit strings.

## Endpoints

| Area      | Method · Path                                                                       |
| --------- | ----------------------------------------------------------------------------------- |
| Identity  | `GET /users/@me`                                                                    |
| Guilds    | `GET /users/@me/guilds`, `GET /guilds/{guild.id}?with_counts=true`                  |
| Members   | `GET /guilds/{guild.id}/members?limit=1000&after=`, `PATCH .../members/{user.id}`   |
| Roles     | `PUT /guilds/{guild.id}/members/{user.id}/roles/{role.id}`                          |
| Messages  | `POST /channels/{channel.id}/messages`, `GET .../messages?limit=100&before=&after=`, `PATCH`/`DELETE .../messages/{id}` |
| Reactions | `PUT /channels/{channel.id}/messages/{message.id}/reactions/{emoji}/@me`            |
| DMs       | `POST /users/@me/channels` body `{"recipient_id":"..."}`, then post to returned id  |
| Webhooks  | `POST /channels/{channel.id}/webhooks`, `POST /webhooks/{id}/{token}` (no auth)     |
| Commands  | `POST /applications/{app.id}/guilds/{guild.id}/commands` (instant), `.../commands` (global, up to 1h) |

## Primary workflow — sending a message

`POST /channels/{channel_id}/messages`. Body needs at least one of `content` (≤2000 chars), `embeds` (≤10), `components`, `files`, or `poll`.

```bash
# Plain text
curl -sL -X POST "${AUTH[@]}" "${UA[@]}" -H "Content-Type: application/json" \
  "https://discord.com/api/v10/channels/$CHANNEL_ID/messages" \
  -d '{"content":"hello from teleport"}'

# Rich embed
curl -sL -X POST "${AUTH[@]}" "${UA[@]}" -H "Content-Type: application/json" \
  "https://discord.com/api/v10/channels/$CHANNEL_ID/messages" \
  -d '{"embeds":[{"title":"Deploy succeeded","description":"v1.2.3 is live","color":5763719,"fields":[{"name":"commit","value":"abc1234","inline":true}]}]}'
```

File uploads are multipart: one `payload_json` part + `files[n]` parts; `attachments[].id` in JSON must match the `files[n]` index.

## Secondary workflows

```bash
# Read recent history (paginate older with ?before=<oldest_id>)
curl -sL "${AUTH[@]}" "${UA[@]}" \
  "https://discord.com/api/v10/channels/$CHANNEL_ID/messages?limit=50"

# Execute a webhook — URL IS the credential, no bot auth needed
curl -sL -X POST -H "Content-Type: application/json" \
  "https://discord.com/api/webhooks/$WEBHOOK_ID/$WEBHOOK_TOKEN" \
  -d '{"content":"deploy done","username":"ci-bot"}'
```

## Gotchas

- **`Bot ` prefix is mandatory** — `Bearer $TOKEN` or a raw token returns 401. The trailing space is literal.
- **Missing / fake `User-Agent` is blocked by Cloudflare** before Discord sees it. Send `DiscordBot (url, version)`.
- **Message Content is a privileged intent.** Without it, messages the bot didn't author and isn't mentioned in come back with empty `content`. Bots in >100 guilds must apply to Discord to keep it.
- **Snowflake IDs exceed JS Number precision** — keep them strings end-to-end (`jq -r`), never parse as Number.
- **File uploads are multipart with `payload_json`**, not JSON+base64. Easy to mis-wire `attachments[].id` ↔ `files[n]` index.
- **Webhook URLs bypass bot permissions entirely** — whoever has the URL can post as it. Treat as secret; separate rate-limit bucket.
- **Bulk delete rejects messages older than 14 days** — `POST .../messages/bulk-delete` 400s on older; fall back to one-by-one.
- **DMs need a channel first** — `POST /users/@me/channels` with `{recipient_id}`, then post to the returned channel id.

## Attribution

When done, state: `Used skill: Discord (from teleport catalog).`
