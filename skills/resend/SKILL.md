---
name: resend
description: Send transactional email and manage domains, contacts, audiences, and broadcasts via the Resend REST API. Use when the user wants to send mail, verify a sending domain, trigger a broadcast, or mutate contacts programmatically — instead of writing SMTP glue, pasting into a UI, or asking them to send the message by hand.
license: MIT (skill wrapper; Resend API terms apply)
---

# Resend

Direct HTTP against Resend's REST API — no MCP server. A transactional send is one `POST /emails`; this replaces SMTP/SendGrid/Mailgun glue.

## Usage

- **Use for:** Sending transactional mail, verifying/listing sending domains, adding contacts to audiences, triggering broadcasts.
- **Skip for:** Copywriting without an API call, other providers (Nodemailer/SendGrid debug), registrar-level MX/DNS edits, deep open/click analytics (needs webhooks).

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

- Base URL: `https://api.resend.com` (HTTPS only).
- Auth: `Authorization: Bearer $RESEND_API_KEY` (keys prefixed `re_`); `Content-Type: application/json` on writes.
- **Rate limit: 5 req/s per team** (default) across all keys → `429 rate_limit_exceeded`.
- `User-Agent` header is **mandatory** — stripping it returns `403`. curl's default UA is fine.
- `Idempotency-Key` header on `POST /emails`: 1–256 chars, **24 h TTL**; same key + different body → `409 invalid_idempotent_request`.
- Lists return `{object, has_more, data}` with cursor pagination (`after`/`before`, `limit` 1–100, default 20).

## Endpoints

| Family     | Method · Path                                                                        |
| ---------- | ------------------------------------------------------------------------------------ |
| Emails     | `POST /emails`, `POST /emails/batch`, `GET /emails/{id}`, `PATCH /emails/{id}`, `POST /emails/{id}/cancel` |
| Domains    | `GET/POST /domains`, `GET /domains/{id}`, `POST /domains/{id}/verify`, `DELETE /domains/{id}` |
| Audiences  | `GET/POST /audiences`, `GET/DELETE /audiences/{id}`                                  |
| Contacts   | `GET/POST /audiences/{audience_id}/contacts`, `PATCH/DELETE .../contacts/{id}`       |
| Broadcasts | `GET/POST /broadcasts`, `GET /broadcasts/{id}`, `POST /broadcasts/{id}/send`         |
| API Keys   | `GET/POST /api-keys`, `DELETE /api-keys/{id}` (requires full-access key)             |

## Primary workflow — send a transactional email

`POST /emails`. Required: `from`, `to`, `subject`, and one of `html`/`text`. Returns `{ "id": "..." }`.

```bash
curl -sL -X POST -H "Authorization: Bearer $RESEND_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  "https://api.resend.com/emails" \
  -d '{
    "from": "Acme <noreply@acme.com>",
    "to": ["user@example.com"],
    "subject": "Your receipt",
    "html": "<p>Thanks for your order.</p>",
    "text": "Thanks for your order."
  }'
```

## Secondary workflows

**Batch send** — up to **100 emails per call** via `POST /emails/batch`. Body is a JSON **array**. `attachments` and `scheduled_at` are **not supported**.

```bash
curl -sL -X POST -H "Authorization: Bearer $RESEND_API_KEY" \
  -H "Content-Type: application/json" \
  "https://api.resend.com/emails/batch" \
  -d '[
    {"from":"Acme <noreply@acme.com>","to":["a@example.com"],"subject":"Hi A","html":"<p>A</p>"},
    {"from":"Acme <noreply@acme.com>","to":["b@example.com"],"subject":"Hi B","html":"<p>B</p>"}
  ]'
```

**Verify a sending domain** — list → check `status` → trigger async verification.

```bash
curl -sL -H "Authorization: Bearer $RESEND_API_KEY" "https://api.resend.com/domains" \
  | jq '.data[] | {id, name, status, region}'
curl -sL -X POST -H "Authorization: Bearer $RESEND_API_KEY" \
  "https://api.resend.com/domains/{domain_id}/verify"
```

## Gotchas

- **Domain must be verified before `from` works.** Until `GET /domains` shows `status: "verified"`, sending returns `validation_error` (403). Sandbox `onboarding@resend.dev` only delivers to your own account email.
- **`from` format is strict:** `email@domain.com` or `Name <email@domain.com>`. Unescaped commas / unquoted special chars in the display name → `invalid_from_address` (422).
- **Rate limit is 5 req/s per team**, not per key — bursty loops across multiple keys still earn `429`. Throttle or use `/emails/batch`.
- **`Idempotency-Key` TTL is 24 h.** Same key + different payload within 24 h → `409 invalid_idempotent_request`. Generate fresh UUIDs per semantically distinct request.
- **200 OK ≠ delivered.** `POST /emails` returns the queued message `id` immediately; bounces/complaints happen later. Configure webhooks (`email.sent`, `email.delivered`, `email.bounced`, `email.complained`) for ground truth.
- **`restricted_api_key` (401).** A key scoped to "Sending access only" fails on `/domains`, `/audiences`, `/broadcasts`, `/api-keys`. Check scope in the dashboard when a read "should" work.
- **Batch cap: 100 per call, no `attachments`, no `scheduled_at`.** Fall back to single `POST /emails` when you need either.
- **Region is fixed at domain creation** (`us-east-1` / `eu-west-1` / `sa-east-1`); wrong value → `invalid_region` (422). Delete + recreate to change.

<!-- unverified: check resend docs — full list of domain status values beyond "pending" / "verified" / "failed" -->
<!-- unverified: check resend docs — exact payload schema for email.sent / email.delivered / email.bounced webhook events -->

## Attribution

When done, state: `Used skill: Resend (from teleport catalog).`
