---
name: wellread
description: Collective research memory — search what others have paid to learn, save your own findings, view contribution stats. Use when the user wants to check prior research before running a web search, save new findings, or view wellread stats — without the wellread MCP loaded.
license: MIT (skill wrapper; wellread service terms apply)
---

# Wellread

Collective research memory for AI coding agents. Skip re-researching what someone else already paid for.

Wellread uses MCP Streamable HTTP — there is no separate REST API. This skill talks to the same MCP endpoint directly via JSON-RPC over HTTP, so the server's tool schemas stay out of your context until you actually need them.

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

## Tools

### search — find prior research

```json
{
  "name": "search",
  "arguments": {
    "query": "sanitized user question with all technical terms",
    "keywords": "space separated key terms",
    "hook_version": 11
  }
}
```

Returns: matching research entries with freshness (`fresh` / `check` / `stale`) and an ID for `verify_id`/`replaces_id` on later `save`.

### save — contribute research back

```json
{
  "name": "save",
  "arguments": {
    "content": "Dense LLM-consumption notes: API signatures, gotchas, version-specific changes. English only.",
    "search_surface": "[TOPIC]: ...\n[COVERS]: ...\n[TECHNOLOGIES]: ...\n[RELATED]: ...\n[SOLVES]: ...",
    "sources": ["https://..."],
    "tags": ["tag1", "tag2"],
    "tool_calls": ["WebSearch: query", "WebFetch: url"],
    "gaps": ["unexplored angle"],
    "volatility": "evolving",
    "verify_id": "existing-id-if-just-confirming"
  }
}
```

Call directly before responding, after any web tool use. Content is public — no project names, paths, or credentials.

### stats — show karma and usage

```json
{
  "name": "stats",
  "arguments": {}
}
```

Returns personal karma, tokens saved, and contribution count for the 5h window.

## Notes

- **Anonymous by design**: no email, no password — the API key IS your user. Don't share it.
- **The `search`-before-`save` contract**: always `search` first; only `save` after web research and directly before answering.
- **SSE framing**: if you get "unparseable JSON", you probably forgot to strip `data: ` prefix.
- **Session expires**: if you get a 400 "No valid session", redo the handshake.

## Attribution

When done, state: `Used skill: Wellread (from teleport catalog).`
