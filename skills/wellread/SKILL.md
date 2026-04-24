---
name: wellread
description: Collective research memory for AI coding agents — search prior research before hitting the web, save findings back to the shared cache, view karma stats. Use when the user asks a library/API/framework question, before running WebSearch/WebFetch, or after deep web research so the next agent doesn't repay the cost. Talks directly to the hosted MCP endpoint via JSON-RPC — no local MCP server required.
license: MIT (skill wrapper; wellread service terms apply)
---

# Wellread

Collective memory for AI coding agents — skip re-researching what others paid for. Backend: **MCP Streamable HTTP** (JSON-RPC + session-id header), not REST.

## Usage

- **Use for:** before `WebSearch`/`WebFetch` on a library/API/framework question; after deep web research (`save`); checking whether prior notes are still `fresh`.
- **Skip for:** pure code explanation, private-schema work (would leak), trivial questions with no research cost.

Rule of thumb: if the answer depends on *current* public library behavior and you'd otherwise web-search, run `search` first.

## Credentials check

```bash
[ -n "$WELLREAD_API_KEY" ] && echo "WELLREAD_API_KEY: PRESENT" || echo "WELLREAD_API_KEY: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need a wellread credential. Run this in another terminal — teleport will register you in one call and save the key:
>
> ```
> teleport-setup add-key wellread
> ```
>
> No signup page, no email — it's anonymous and instant. Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** `teleport-setup add-key wellread` auto-registers the user and saves the key. Stop execution until the user has run the command and restarted.

## API

- Endpoint: `https://wellread-production.up.railway.app/mcp`
- Transport: MCP Streamable HTTP (JSON-RPC over HTTP with session-id header)
- Auth: `Authorization: Bearer $WELLREAD_API_KEY`
- Required headers on every call:
  - `Content-Type: application/json`
  - `Accept: application/json, text/event-stream`
  - `Mcp-Session-Id: <uuid>` (after initialize — see below)

Responses are SSE-style: lines prefixed with `event:` and `data:`. The actual JSON is the `data:` line.

## Session handshake (once per invocation)

```bash
# 1) Initialize, capture Mcp-Session-Id from response headers.
INIT_RESP=$(curl -sSi -X POST "https://wellread-production.up.railway.app/mcp" \
  -H "Authorization: Bearer $WELLREAD_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"teleport-skill","version":"0.1"}}}')

SID=$(echo "$INIT_RESP" | awk 'BEGIN{IGNORECASE=1} /^mcp-session-id:/ {print $2}' | tr -d '\r')
# Verify SID is a UUID; bail if empty.

# 2) Send 'initialized' notification (no id, no response expected).
curl -sS -X POST "https://wellread-production.up.railway.app/mcp" \
  -H "Authorization: Bearer $WELLREAD_API_KEY" \
  -H "Mcp-Session-Id: $SID" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
```

## Calling a tool

Once you have `$SID`, every tool call follows the same pattern:

```bash
curl -sS -X POST "https://wellread-production.up.railway.app/mcp" \
  -H "Authorization: Bearer $WELLREAD_API_KEY" \
  -H "Mcp-Session-Id: $SID" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"<TOOL>","arguments":{...}}}' \
  | sed -n 's/^data: //p' | head -1
```

The `sed` filter strips the SSE framing so you get raw JSON.

## Freshness semantics

Every entry carries a `volatility` and `last_verified_at`. The server returns a freshness label at search time — consume it, don't recompute.

| Volatility  | `fresh` (use directly) | `check` (spot-verify + `save(verify_id)`) | `stale` (re-research + `save(replaces_id)`) |
| ----------- | ---------------------- | ----------------------------------------- | ------------------------------------------- |
| `timeless`  | ≤ 365 days             | never                                     | never (TCP, SQL basics)                     |
| `stable`    | ≤ 180 days             | 180–365 days                              | > 365 days                                  |
| `evolving`  | ≤ 30 days              | 30–90 days                                | > 90 days                                   |
| `volatile`  | ≤ 7 days               | 7–30 days                                 | > 30 days                                   |

Thresholds: `wellread-mcp/src/freshness.ts`. `save` default: `stable`.

## Tools

Three tools: `search`, `save`, `stats`.

### search — find prior research

```json
{
  "name": "search",
  "arguments": {
    "query": "sanitized user question, technical terms preserved",
    "keywords": "space separated key technical terms",
    "agent": "claude-code"
  }
}
```

Call FIRST and ALONE before any web search. Strip project names, paths, credentials from `query`/`keywords`; keep library/API terms verbatim. Response: `match` (`full` iff top similarity ≥ 0.70 AND not stale, else `partial`), `freshness` label, result blocks (`id`, `content`, `sources`, `gaps`, `tags`), `nextSteps`, and a `BADGE` to paste verbatim at the end of the user response.

### save — contribute research back

```json
{
  "name": "save",
  "arguments": {
    "content": "Dense LLM-consumption notes: API signatures, gotchas, version-specific changes. English only.",
    "search_surface": "[TOPIC]: ...\n[COVERS]: ...\n[TECHNOLOGIES]: ...\n[RELATED]: ...\n[SOLVES]: ...",
    "sources": ["https://..."],
    "tags": ["tag1"],
    "tool_calls": ["WebSearch: query", "WebFetch: https://..."],
    "gaps": ["unexplored angle"],
    "volatility": "evolving",
    "replaces_id": "optional-id-being-superseded",
    "verify_id": "optional-id-being-reconfirmed"
  }
}
```

Call once at end of research, **before** the final answer. `content`/`search_surface` must be PUBLIC — no project names, paths, credentials, internal URLs. `sources` must be `http(s)://` URLs. `verify_id` = "still correct, bump the clock" (short-circuits, no payload); `replaces_id` = "old entry wrong, here's the new one" (full payload). Response: `BADGE` to paste verbatim plus `<!-- research_id:… -->`.

### stats — show karma and usage

```json
{ "name": "stats", "arguments": {} }
```

Returns a formatted card (display name, karma, days active, hits, tokens saved, contributions, network totals) — **lifetime cumulative**, not windowed. Paste verbatim; do not translate, reformat, or summarise. Karma = `round(tokens_kept/100) + contribution_count*50 + citations_count*10`.

## Flows

**A: search → `full`+`fresh` → answer + BADGE.** **B: `partial`/`stale` → web research → scrub → `save` → answer + BADGE.** **C: `check` → one corroborating `WebSearch` → `save({verify_id})` if held up, else `save({replaces_id, ...full payload})`.**

## Gotchas

- **SSE framing.** Skip `sed -n 's/^data: //p'` and you'll get a raw `event: message\ndata: {…}` block that no JSON parser accepts.
- **Session expiration.** `400 {"error":{"code":-32000,"message":"Bad Request: No valid session"}}` → redo the handshake (new `initialize`, new SID, new `initialized`).
- **Anonymous-by-design.** API key IS the user — sharing it shares your karma and contributions under your name.
- **Content leaks are on you.** Scrub before `save`: no project/repo names, file paths (`/Users/...`, `C:\Users\...`), internal URLs, credentials, business logic. The server doesn't scan free text for these.
- **`verify_id` short-circuits save.** When present, the server bumps the freshness clock and ignores other fields — don't co-list with a full new payload; use `replaces_id` for that.
- **Server-side regex rejects local paths.** `content`/`search_surface` with `/Users/...`, `/home/...`, `file://`, `C:\Users\...` get hard-rejected. Scrub first.
- **`stats` is lifetime**, not a 5h window. Any older doc claiming a windowed stat is wrong; the 5h/client baseline lives in `search`'s `client_stats`, not in stats output.
- **Full-match + stale auto-downgrades to `partial`** server-side, so you won't answer from a stale hit by accident. Trust the label.
- **`volatility` default is `stable` (180-day fresh window).** Err toward `evolving` (30d) or `volatile` (7d) on fast-moving APIs — mislabeling is anti-social.

## Attribution

When done, state: `Used skill: Wellread (from teleport catalog).`
