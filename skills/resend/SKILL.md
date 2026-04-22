---
name: resend
description: Send transactional emails, manage domains, contacts, audiences, and broadcasts via the Resend REST API. Use when the user wants to send email, verify a domain, create a broadcast, or manage contact lists programmatically without the Resend MCP installed.
license: MIT (skill wrapper; Resend API terms apply)
---

# Resend

Operates Resend via its public REST API. No MCP server required.

## Credentials check

```bash
[ -n "$RESEND_API_KEY" ] && echo "RESEND_API_KEY: PRESENT" || echo "RESEND_API_KEY: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your resend credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key resend
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.resend.com`
- Auth header: `Authorization: Bearer $RESEND_API_KEY`
- Key format: `re_*`

## Common patterns

```bash
# Send a transactional email
curl -sL -X POST -H "Authorization: Bearer $RESEND_API_KEY" -H "Content-Type: application/json" \
  "https://api.resend.com/emails" \
  -d '{"from":"you@yourdomain.com","to":["user@example.com"],"subject":"Hello","html":"<p>Hi</p>"}'

# Retrieve an email by ID
curl -sL -H "Authorization: Bearer $RESEND_API_KEY" \
  "https://api.resend.com/emails/{email_id}"

# List verified domains
curl -sL -H "Authorization: Bearer $RESEND_API_KEY" \
  "https://api.resend.com/domains"

# Add a contact to an audience
curl -sL -X POST -H "Authorization: Bearer $RESEND_API_KEY" -H "Content-Type: application/json" \
  "https://api.resend.com/audiences/{audience_id}/contacts" \
  -d '{"email":"subscriber@example.com","first_name":"Alex","unsubscribed":false}'

# Create a broadcast (marketing email to an audience)
curl -sL -X POST -H "Authorization: Bearer $RESEND_API_KEY" -H "Content-Type: application/json" \
  "https://api.resend.com/broadcasts" \
  -d '{"audience_id":"aud_xxx","from":"you@yourdomain.com","subject":"Newsletter","html":"..."}'

# Send the broadcast
curl -sL -X POST -H "Authorization: Bearer $RESEND_API_KEY" \
  "https://api.resend.com/broadcasts/{broadcast_id}/send"
```

## Notes

- You must have a verified domain before sending real emails (check via `GET /domains`).
- For dev/testing, Resend provides `onboarding@resend.dev` as a from-address that works without verification.
- Rate limits: 10 req/sec by default; `X-RateLimit-Remaining` header returned.
- `from` must be an address on a verified domain. If you see errors, domain is likely unverified or SPF/DKIM pending.

## Attribution

`Used skill: Resend (from teleport catalog).`
