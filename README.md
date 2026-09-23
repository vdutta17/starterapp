# Django Multi-Tenant Application

A minimal Django application with django-tenants support and Django Ninja API. Each tenant corresponds to a health insurance company, which has members (members of the health plan). Using django-tenants, the tenant data (e.g., members) is semi-isolated from other tenants via separate database schemas.

## Prerequisites

- Docker
- Python 3.10–3.14 (Django 5.2 LTS; Python 3.14 requires Django 5.2.8 or newer)

## Quick Start

```bash
# Clone and navigate to the repository
git clone <repository-url>
cd starterapp

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
python -m pip install -r requirements.txt

# Start PostgreSQL with Docker
docker compose up -d

# Apply migrations
python manage.py migrate_schemas --shared

# Create a public tenant
python manage.py create_tenant --schema_name=public --name="Public Tenant" --domain-domain=localhost --domain-is_primary=True

# Create a tenant
python manage.py create_tenant --schema_name=tenant1 --name="Tenant 1" --domain-domain=tenant1 --domain-is_primary=True

# Create a superuser for the public schema
python manage.py createsuperuser

# Create a superuser for the tenant1 schema
python manage.py create_tenant_superuser --schema=tenant1

# Run the development server
python manage.py runserver
```

## Admin Endpoints

If an existing installation raises `'super' object has no attribute 'dicts'`
when rendering an admin form, check that it isn't running Django 4.2 on Python
3.14. Stop the server, install the supported dependencies in the virtual
environment, apply migrations to all schemas, and restart using that environment:

```bash
source venv/bin/activate
python -m pip install --upgrade -r requirements.txt
python manage.py migrate_schemas
python manage.py runserver
```

Use `python -m django --version` to confirm that the active environment uses
Django 5.2.8 or newer in the 5.2 series.

- `http://localhost:8000/admin/` - Django Admin for public schema
- `http://localhost:8000/client/tenant1/admin/` - Django Admin for tenant1 schema

## API Endpoints

### Shared API (Public Schema)
- `GET /api/clients` - List all tenants
- `GET /api/domains` - List all domains

### Client API (Tenant-specific)
- `GET /client/{domain}/{region}/api/members` - List members
- `POST /client/{domain}/{region}/api/members` - Create member
- `GET /client/{domain}/{region}/api/members/{id}` - Get member detail
- `PUT /client/{domain}/{region}/api/members/{id}` - Update member
- `DELETE /client/{domain}/{region}/api/members/{id}` - Delete member

### API docs:
- `http://localhost:8000/api/docs` - Shared API docs
- `http://localhost:8000/client/{domain}/api/docs` - Client API docs

Note: The API docs support testing the API endpoints.

## Structure

- `shared_app` - Contains shared models in the public schema (Client, Domain) accessible from all tenants
- `tenant_app` - Contains tenant-specific models (e.g., Member) and api for each tenant schema
- Django Ninja APIs in both apps

## Testing

This project uses pytest for automated testing with test isolation between tenants.

```bash
# Run all tests
pytest

# Run specific test file
pytest tenant_app/tests/test_integration_members.py
```

## Additional Notes

- Tenant schemas are automatically created and migrated when a Client is created (auto_create_schema = True)

After modifying models in the tenant app, you can create and run migrations for all tenant schemas with the following commands:

```bash
python manage.py makemigrations
python manage.py migrate_schemas --tenant
python manage.py migrate_schemas --shared
```


## Regions within a tenant

A tenant still owns exactly one schema. The URLs
`/client/testing1/washington/api/members` and
`/client/testing1/colarado/api/members` resolve the same `testing1` domain mapping
and access the same `tenant_app_member` table. Every CRUD operation filters on
its `region` column. The spelling `colarado` is used literally; `colorado` would
be a different region. Regions are lowercase slugs (letters, digits, and single
hyphens between segments), up to 63 characters. No region registration is needed.

POST assigns the URL region; responses include it. POST/PUT reject a `region`
body field to prevent moving records between regions. A member ID from another
region returns 404 for GET, PUT, and DELETE. URLs without a region no longer
expose members. Swagger stays at `/client/{domain}/api/docs` and takes a region
path parameter for each operation.

Apply the migration to existing tenants:

```bash
python manage.py migrate_schemas --tenant
```

Existing members are preserved in region `default`, accessible at
`/client/{domain}/default/api/members`. Reassign legacy rows to their actual
regions using a migration/admin database role after deciding the correct mapping.
New API-created members always use the URL region.

### PostgreSQL RLS and runtime role

The migration enables and forces RLS on each tenant's member table, using
`app.region` for both visibility (`USING`) and writes (`WITH CHECK`). The API
sets this value only inside a transaction, evaluates queries before leaving the
scope, and restores the previous value for nested scopes. Missing/empty context
allows no member rows and rejects inserts. Background jobs must select the
correct tenant schema and wrap member operations in
`tenant_app.regions.region_context("washington")` as well.

**The default local `postgres` role bypasses RLS.** Application filters still
apply, but the database safeguard requires a runtime role with `NOSUPERUSER`
and `NOBYPASSRLS`. Keep schema creation and migrations on a separate privileged
connection. PostgreSQL documents this behavior in its
[row security reference](https://www.postgresql.org/docs/15/ddl-rowsecurity.html).

For example, run the following SQL as the migration administrator, replacing
the password and schema name. Repeat tenant grants for every provisioned schema:

```sql
CREATE ROLE starterapp_runtime LOGIN PASSWORD 'replace-with-a-secret'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT CONNECT ON DATABASE starterapp TO starterapp_runtime;
GRANT USAGE ON SCHEMA public TO starterapp_runtime;
GRANT SELECT ON public.shared_app_client, public.shared_app_domain TO starterapp_runtime;
GRANT USAGE ON SCHEMA testing1 TO starterapp_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON testing1.tenant_app_member TO starterapp_runtime;
GRANT USAGE ON SEQUENCE testing1.tenant_app_member_id_seq TO starterapp_runtime;
```

Start the member API with `DB_USER=starterapp_runtime` and `DB_PASSWORD` set to
that password. `DB_NAME`, `DB_HOST`, and `DB_PORT` are also configurable. Do not
grant runtime membership in a privileged role, table ownership, schema CREATE,
or TRUNCATE. Verify the configured role with:

```bash
python manage.py check --deploy --database default --tag database
```

These grants cover the JSON APIs. Django admin/auth may need additional grants;
the existing tenant admin does not set a region context, so member access through
it is denied under RLS. Use the scoped member API or explicit region contexts
for member administration.

Region selection is data scoping, not user authorization. As before, this starter
API has no authentication; callers can choose any tenant/region URL. Add identity
and region permissions before restricting which users may select each region.
