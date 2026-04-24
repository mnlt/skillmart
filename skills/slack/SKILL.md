---
name: slack
description: Send messages, read channels, search Slack via its Web API. Use when the user wants to post to a channel, read recent messages, list users/channels, or search a workspace programmatically — no MCP server required.
license: MIT (skill wrapper; Slack Web API terms apply)
---

# Slack

Operates Slack via its public Web API (`https://slack.com/api/METHOD`). Covers messaging, channels/DMs, users, files, search, reactions, and pins — no MCP server required.

## Usage

- **Use for:** Posting to channels, reading recent history, listing channels/members, searching messages, managing reactions/pins.
- **Skip for:** Interactive back-and-forth (needs Events API / RTM), human approval flows, Enterprise Grid admin ops (SCIM / Admin API).

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
- Auth: `Authorization: Bearer $TOKEN` — bot `xoxb-` (most methods), user `xoxp-` (required for `search.*`). Header only, never query param.
- **HTTP 200 on errors.** Status alone means nothing — every response is JSON `{"ok": true|false, ...}`; on false, read `.error` (`channel_not_found`, `missing_scope`, `invalid_auth`, `ratelimited`, `not_in_channel`, `no_text`). Always branch on `.ok`.
- Content-Type: `application/json; charset=utf-8` for writes; reads also accept form-encoded / GET query strings.
- Rate limits: per-method tiers (Tier 1 ~1/min admin → Tier 4 100+/min; Special for `chat.postMessage` ~1/sec/channel + workspace cap). On 429, honor `Retry-After: <seconds>` header.

## Token scopes

Bot tokens need explicit scopes per method (`chat:write`, `channels:read`/`:history`, `users:read`(+`.email`), `reactions:write`, etc.). Wrong scope → `{"ok": false, "error": "missing_scope"}`. `search.messages` requires a **user** token (`xoxp-`) with `search:read`. Scopes are additive-only; downgrading needs revoke + reinstall.

## Endpoints

| Method                                                              | One-liner                                   |
| ------------------------------------------------------------------- | ------------------------------------------- |
| `chat.postMessage` / `.update` / `.delete` / `.postEphemeral`       | Post, edit, delete, post-to-one-user        |
| `conversations.list` / `.info` / `.members` / `.join`               | Enumerate / inspect / join channels         |
| `conversations.history` / `.replies`                                | Channel messages / thread replies           |
| `users.list` / `.info` / `.conversations`                           | Member directory, by ID, user's channels   |
| `files.getUploadURLExternal` / `.completeUploadExternal` / `.list`  | Current upload flow + listing               |
| `search.messages` / `search.files`                                  | Search (user token + `search:read`)         |
| `reactions.add` / `.remove`                                         | Emoji reactions                             |
| `pins.add` / `.remove` / `.list`                                    | Pinned messages                             |

## Primary workflow — post a message

```bash
curl -sL -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  "https://slack.com/api/chat.postMessage" \
  -d '{"channel":"C0123ABC","text":"deploy v2.3.1 succeeded"}' \
  | jq '{ok, error, ts}'
```

Pass a channel **ID** (`C0123ABC`), not a name. Always include `text` as fallback even when sending `blocks: [...]` (design at Block Kit Builder `https://app.slack.com/block-kit-builder`). <!-- unverified: check slack docs --> Thread reply: add `"thread_ts": "1745520000.000100"` (parent's `ts`).

## Secondary workflows

```bash
# Read recent messages (Tier 3, reverse chron). Paginate via response_metadata.next_cursor.
curl -sL -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.history?channel=C0123ABC&limit=100" \
  | jq '{ok, has_more, messages: [.messages[] | {user, text, ts}]}'

# List channels (Tier 2). types default is public only.
curl -sL -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  "https://slack.com/api/conversations.list?types=public_channel,private_channel&exclude_archived=true&limit=200"

# Bot joins public channel before posting (avoids not_in_channel)
curl -sL -X POST -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json; charset=utf-8" \
  "https://slack.com/api/conversations.join" -d '{"channel":"C0123ABC"}'
```

## Gotchas

- **HTTP 200 lies.** Every call can fail with status 200 — always branch on `.ok` and map `.error` before surfacing.
- **Channel IDs (`C0123ABC`), not names (`#general`).** Most endpoints reject names. Resolve once via `conversations.list` and cache.
- **Bot must be in the channel to post** or you get `not_in_channel`. Fix: `conversations.join` (public) or admin `/invite @bot` in UI (private — no self-join).
- **Timestamps are strings with microsecond precision** (`"1745520000.000100"`). Compare as strings or split on `.` — **never parse as float**; precision is lost and `thread_ts` references break.
- **Pagination is cursor-based, not page-number.** Read `response_metadata.next_cursor`, pass back as `cursor=`. Empty/absent = end.
- **Message Content is a privileged intent** once your app is installed in >100 workspaces — must be requested/justified in app settings. <!-- unverified: check slack docs -->
- **`files.upload` is deprecated.** Current flow: (1) `files.getUploadURLExternal` → URL + file ID, (2) `PUT` bytes to that URL, (3) `files.completeUploadExternal` with file ID (+ optional `channel_id`).
- **Rate limit tiers vary per method** — don't assume one tier per family. On 429, sleep `Retry-After` seconds.

## Attribution

When done, state: `Used skill: Slack (from teleport catalog).`
