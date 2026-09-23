# Endpoint and curl reference

Derived from `starterapp/urls_public.py`, `starterapp/urls.py`, both API modules,
and the registered Django admin routes. Commands are examples, not an executed
CRUD sequence. POST, PUT, and DELETE examples modify data when you run them.

## Setup

```bash
BASE_URL='http://localhost:8000'
TENANT='testing_onos' # A Domain.domain value, not necessarily the schema name
TENANT_URL="$BASE_URL/client/$TENANT"
REGION='washington' # Use colarado for a separate region in the same tenant
REGION_URL="$TENANT_URL/$REGION"
MEMBER_ID=1 # Replace with the ID returned by member creation
```

The seven JSON operations below currently have no configured authentication.
Use the exact paths shown, without trailing slashes.

## Shared JSON API

List clients — `GET /api/clients`:

```bash
curl -i "$BASE_URL/api/clients"
```

List domain mappings — `GET /api/domains`:

```bash
curl -i "$BASE_URL/api/domains"
```

There are no JSON endpoints for creating, updating, or deleting clients or
domains. Those operations are available through Django admin.

## Tenant JSON API

List members — `GET /client/{domain}/{region}/api/members`:

```bash
curl -i "$REGION_URL/api/members"
```

Create member — `POST /client/{domain}/{region}/api/members`:

```bash
curl -i -X POST "$REGION_URL/api/members" \
  -H 'Content-Type: application/json' \
  --data '{"name":"Jane Doe","email":"jane@example.com","phone":"555-0100"}'
```

Read member — `GET /client/{domain}/{region}/api/members/{member_id}`:

```bash
curl -i "$REGION_URL/api/members/$MEMBER_ID"
```

Update member — `PUT /client/{domain}/{region}/api/members/{member_id}`:

```bash
curl -i -X PUT "$REGION_URL/api/members/$MEMBER_ID" \
  -H 'Content-Type: application/json' \
  --data '{"name":"Jane Smith","email":"jane.smith@example.com","phone":"555-0101"}'
```

Delete member — `DELETE /client/{domain}/{region}/api/members/{member_id}`:

```bash
curl -i -X DELETE "$REGION_URL/api/members/$MEMBER_ID"
```

Successful operations are declared as HTTP 200, including create and delete.
Missing member IDs return 404. The delete route declares an empty response body.
`name` is required for both POST and PUT. On POST, omitted/null `email` and
`phone` become empty strings. The region comes from the URL; a body `region`
field is rejected. Responses include `region`. On PUT, omitting them or passing null preserves the
existing values; use an empty string to clear either field. No PATCH exists.

## API documentation and generated root routes

```bash
# Swagger UI (HTML)
curl -i "$BASE_URL/api/docs"
curl -i "$TENANT_URL/api/docs"

# OpenAPI descriptions (JSON)
curl -i "$BASE_URL/api/openapi.json"
curl -i "$TENANT_URL/api/openapi.json"

# Generated Ninja root routes; these are not business API operations
curl -i "$BASE_URL/api/"
curl -i "$TENANT_URL/"
```

## Django admin routes

These return HTML or admin-specific responses, not the application JSON API.
Both public and tenant URL trees expose the same registered admin routes.
Accounts and permissions are evaluated in the selected schema. Tenant member
tables live in tenant schemas. With RLS enforced, the unscoped admin cannot
access members; use the region-scoped member API. See README for runtime grants.

Select one admin base:

```bash
ADMIN_URL="$TENANT_URL/admin"
# Or use the public admin:
# ADMIN_URL="$BASE_URL/admin"
```

Fetch the login form and save its CSRF cookie:

```bash
COOKIE_JAR=$(mktemp)
curl -sS -c "$COOKIE_JAR" "$ADMIN_URL/login/" -o /tmp/starterapp-admin-login.html
CSRF_TOKEN=$(awk '$6 == "csrftoken" {print $7}' "$COOKIE_JAR")
```

Log in with an existing staff account in the selected schema. Replace the
example credentials locally; these are placeholders.

```bash
curl -i -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -e "$ADMIN_URL/login/" \
  --data-urlencode "csrfmiddlewaretoken=$CSRF_TOKEN" \
  --data-urlencode 'username=YOUR_USERNAME' \
  --data-urlencode 'password=YOUR_PASSWORD' \
  --data-urlencode "next=$ADMIN_URL/" \
  "$ADMIN_URL/login/"
```

Admin navigation and account pages:

```bash
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/login/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/password_change/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/password_change/done/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/jsi18n/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/shared_app/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/auth/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/tenant_app/"
```

The following six route patterns exist for each of these five registered models:

| MODEL_PATH | Model |
| --- | --- |
| shared_app/client | Tenant/client |
| shared_app/domain | Domain mapping |
| tenant_app/member | Member |
| auth/user | User |
| auth/group | Group |

Set `MODEL_PATH` to each desired row and `OBJECT_ID` to an existing record ID:

```bash
MODEL_PATH='shared_app/client'
OBJECT_ID=1
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/$MODEL_PATH/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/$MODEL_PATH/add/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/$MODEL_PATH/$OBJECT_ID/change/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/$MODEL_PATH/$OBJECT_ID/delete/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/$MODEL_PATH/$OBJECT_ID/history/"
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/$MODEL_PATH/$OBJECT_ID/"
```

These GET requests only fetch pages (the last is a legacy redirect). Saving add,
change, delete, password-change forms, or changelist actions uses POST to the
corresponding URL with the actual form fields and a fresh CSRF token. Inline
forms also require their management fields. They do not accept JSON payloads.

User password form:

```bash
USER_ID=1
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/auth/user/$USER_ID/password/"
```

Additional built-in routes (registered, but not configured for useful results
for every model):

```bash
# Requires a supported relationship field and configured search_fields
curl -i -b "$COOKIE_JAR" --get "$ADMIN_URL/autocomplete/" \
  --data-urlencode 'app_label=shared_app' \
  --data-urlencode 'model_name=domain' \
  --data-urlencode 'field_name=tenant' \
  --data-urlencode 'term=testing'

# View-on-site redirect; requires an object with get_absolute_url().
# This project's Client, Domain, and Member models do not define one.
CONTENT_TYPE_ID=1
OBJECT_ID=1
curl -i -b "$COOKIE_JAR" "$ADMIN_URL/r/$CONTENT_TYPE_ID/$OBJECT_ID/"
```

Log out (POST; login rotates the CSRF cookie, so read it again):

```bash
CSRF_TOKEN=$(awk '$6 == "csrftoken" {print $7}' "$COOKIE_JAR")
curl -i -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -e "$ADMIN_URL/" \
  --data-urlencode "csrfmiddlewaretoken=$CSRF_TOKEN" \
  "$ADMIN_URL/logout/"
rm -f "$COOKIE_JAR"
```

The admin also registers a catch-all for unmatched paths; it is not an extra
application endpoint. Development static-file serving is likewise not a JSON
API endpoint.
