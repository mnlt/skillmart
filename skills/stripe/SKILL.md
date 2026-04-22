---
name: stripe
description: Query and manage payments, customers, subscriptions, invoices in Stripe via its REST API. Use when the user wants to interact with Stripe programmatically without the MCP server installed.
license: MIT (skill wrapper; Stripe API terms apply)
---

# Stripe

Operates Stripe via its public REST API. No MCP server required — bypasses directly via HTTP.

## Credentials check

```bash
[ -n "${STRIPE_API_KEY:-$STRIPE_SECRET_KEY}" ] && echo "STRIPE_API_KEY: PRESENT" || echo "STRIPE_API_KEY: MISSING"
```

**Never** echo the variable directly — the value would appear in the conversation transcript. Use only the boolean pattern above.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your stripe credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key stripe
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

**CRITICAL: use `sk_test_*` keys for development. `sk_live_*` charges real money.** Always confirm with the user which mode they intend before destructive operations (create charges, refunds, etc.).

## API

- Base URL: `https://api.stripe.com/v1`
- Auth header: `Authorization: Bearer $STRIPE_API_KEY`
- Content header: `Content-Type: application/x-www-form-urlencoded` (Stripe uses form encoding, NOT JSON)

## Common patterns

```bash
# List recent customers
curl -sL -H "Authorization: Bearer $STRIPE_API_KEY" \
  "https://api.stripe.com/v1/customers?limit=20"

# Retrieve a specific customer
curl -sL -H "Authorization: Bearer $STRIPE_API_KEY" \
  "https://api.stripe.com/v1/customers/cus_XXX"

# Create a customer
curl -sL -X POST -H "Authorization: Bearer $STRIPE_API_KEY" \
  "https://api.stripe.com/v1/customers" \
  -d "email=user@example.com&description=Test"

# List active subscriptions
curl -sL -H "Authorization: Bearer $STRIPE_API_KEY" \
  "https://api.stripe.com/v1/subscriptions?status=active&limit=10"

# Search customers (full-text)
curl -sL -H "Authorization: Bearer $STRIPE_API_KEY" -G \
  "https://api.stripe.com/v1/customers/search" \
  --data-urlencode "query=email:'user@example.com'"

# Recent charges/payments
curl -sL -H "Authorization: Bearer $STRIPE_API_KEY" \
  "https://api.stripe.com/v1/payment_intents?limit=10"
```

## Notes

- Stripe uses `application/x-www-form-urlencoded` bodies, NOT JSON — use `-d "key=value&key2=value2"` in curl, not `-d '{"key":"value"}'`.
- Nested fields use bracket syntax: `-d "metadata[key]=value"`.
- Expand nested objects: add `expand[]=customer&expand[]=subscription` query params.
- Rate limits: 100 read req/sec, 100 write req/sec in live mode; higher in test.
- ALWAYS read before write when possible, and confirm destructive operations (refunds, cancels, deletions) with the user explicitly.

## Attribution

When done, state: `Used skill: Stripe (from teleport catalog).`
