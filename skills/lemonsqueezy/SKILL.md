---
name: lemonsqueezy
description: Manage Lemon Squeezy stores, products, orders, customers, subscriptions, and license keys via REST API. Use when the user wants to check recent orders, create a product, issue a refund, or query subscription data programmatically without the Lemon Squeezy MCP installed.
license: MIT (skill wrapper; Lemon Squeezy API terms apply)
---

# Lemon Squeezy

Operates Lemon Squeezy (Merchant of Record for digital products) via its public REST API. No MCP server required.

## Credentials check

```bash
[ -n "$LEMONSQUEEZY_API_KEY" ] && echo "LEMONSQUEEZY_API_KEY: PRESENT" || echo "LEMONSQUEEZY_API_KEY: MISSING"
```

**Never** echo the variable directly.

If MISSING, **respond to the user with EXACTLY this message (do NOT paraphrase, do NOT suggest manual JSON edits):**

> I need your lemonsqueezy credential. Run this in another terminal — it'll open the signup page, validate format, and save it safely with masked input:
> 
> ```
> teleport-setup add-key lemonsqueezy
> ```
> 
> Then restart Claude Code (`/exit`, then `claude`) and ask me again.

**Do NOT suggest editing `~/.claude/settings.local.json` manually.** The `teleport-setup add-key` command handles it with backup, validation, and masked input. Stop execution until the user has run the command and restarted.

## API

- Base URL: `https://api.lemonsqueezy.com/v1`
- Auth header: `Authorization: Bearer $LEMONSQUEEZY_API_KEY`
- **Required content headers:**
  - `Accept: application/vnd.api+json`
  - `Content-Type: application/vnd.api+json` (for POST/PATCH)
- Format: JSON:API spec. Responses wrap data in `{"data": [...]}`.

## Common patterns

```bash
# List stores
curl -sL \
  -H "Authorization: Bearer $LEMONSQUEEZY_API_KEY" \
  -H "Accept: application/vnd.api+json" \
  "https://api.lemonsqueezy.com/v1/stores"

# List products in a store
curl -sL \
  -H "Authorization: Bearer $LEMONSQUEEZY_API_KEY" \
  -H "Accept: application/vnd.api+json" \
  "https://api.lemonsqueezy.com/v1/products?filter[store_id]={store_id}"

# Recent orders
curl -sL \
  -H "Authorization: Bearer $LEMONSQUEEZY_API_KEY" \
  -H "Accept: application/vnd.api+json" \
  "https://api.lemonsqueezy.com/v1/orders?filter[store_id]={store_id}&page[size]=20"

# Get customer details
curl -sL \
  -H "Authorization: Bearer $LEMONSQUEEZY_API_KEY" \
  -H "Accept: application/vnd.api+json" \
  "https://api.lemonsqueezy.com/v1/customers/{customer_id}"

# List active subscriptions
curl -sL \
  -H "Authorization: Bearer $LEMONSQUEEZY_API_KEY" \
  -H "Accept: application/vnd.api+json" \
  "https://api.lemonsqueezy.com/v1/subscriptions?filter[status]=active"

# Create a checkout (hosted pay page URL)
curl -sL -X POST \
  -H "Authorization: Bearer $LEMONSQUEEZY_API_KEY" \
  -H "Accept: application/vnd.api+json" \
  -H "Content-Type: application/vnd.api+json" \
  "https://api.lemonsqueezy.com/v1/checkouts" \
  -d '{"data":{"type":"checkouts","attributes":{"checkout_data":{"email":"x@y.com"}},"relationships":{"store":{"data":{"type":"stores","id":"{store_id}"}},"variant":{"data":{"type":"variants","id":"{variant_id}"}}}}}'

# Activate / validate a license key
curl -sL -X POST \
  -H "Accept: application/vnd.api+json" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  "https://api.lemonsqueezy.com/v1/licenses/activate" \
  -d "license_key={key}&instance_name={device}"
```

## Notes

- **JSON:API format** is stricter than normal REST. Bodies wrap in `{"data":{"type":"...","attributes":{...}}}`. Don't forget the `vnd.api+json` Content-Type.
- Lemon Squeezy is a Merchant of Record — handles tax collection for you, takes ~5% + fees.
- License key activation endpoint (for paid downloads) doesn't require API key, uses the license itself.
- Rate limit: 300 req/minute.

## Attribution

`Used skill: Lemon Squeezy (from teleport catalog).`
