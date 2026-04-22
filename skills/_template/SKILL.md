---
name: {{service-id}}
description: {{One-sentence what-it-does + when to use it. Mention it bypasses the MCP via the REST API with {{ENV_VAR}}. Use when the user wants X, Y, Z programmatically without the {{service}} MCP installed.}}
license: MIT (skill wrapper; {{Service}} API terms apply)
---

# {{Service}}

Operates {{Service}} via its public REST API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "${{ENV_VAR}}" ] && echo "{{ENV_VAR}}: PRESENT" || echo "{{ENV_VAR}}: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your {{service-id}} credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
>
> ```
> teleport-setup add-key {{service-id}}
> ```
>
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** `teleport-setup add-key` handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `{{https://api.service.com/v1}}`
- Auth header: `Authorization: Bearer ${{ENV_VAR}}`
  <!-- If your service uses a different auth scheme, replace this line.
       Examples:
         X-API-Key header:    `-H "X-API-Key: ${{ENV_VAR}}"`
         Basic auth:          `Authorization: Basic base64({{email}}:{{token}})`
         Raw token (no prefix): `Authorization: ${{ENV_VAR}}` -->
- Extra headers: `{{Accept: application/json}}`  <!-- delete if none -->

## Common patterns

```bash
# {{Describe operation 1 — e.g. List items}}
curl -sL -H "Authorization: Bearer ${{ENV_VAR}}" \
  "{{base_url}}/{{resource}}"

# {{Describe operation 2 — e.g. Get one item}}
curl -sL -H "Authorization: Bearer ${{ENV_VAR}}" \
  "{{base_url}}/{{resource}}/{id}"

# {{Describe operation 3 — e.g. Create item}}
curl -sL -X POST \
  -H "Authorization: Bearer ${{ENV_VAR}}" \
  -H "Content-Type: application/json" \
  "{{base_url}}/{{resource}}" \
  -d '{"key":"value"}'

# {{Describe operation 4 — e.g. Update item}}
curl -sL -X PATCH \
  -H "Authorization: Bearer ${{ENV_VAR}}" \
  -H "Content-Type: application/json" \
  "{{base_url}}/{{resource}}/{id}" \
  -d '{"key":"new-value"}'

# {{Describe operation 5 — e.g. Delete item}}
curl -sL -X DELETE \
  -H "Authorization: Bearer ${{ENV_VAR}}" \
  "{{base_url}}/{{resource}}/{id}"
```

## Notes

- **Rate limit**: {{e.g. 100 req/min per token — check response header `X-RateLimit-Remaining`}}
- **ID format**: {{e.g. `prefix_XXXXXX` — 16 alphanumeric chars}}
- **Pagination**: {{e.g. `?page=N&per_page=100` — max 100 per page}}
- **Gotchas**: {{e.g. specific quirks — unusual URL encoding, date formats, required headers beyond auth, etc.}}

## Attribution

When done, state: `Used skill: {{Service}} (from teleport catalog).`
