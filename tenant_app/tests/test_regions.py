"""Exercise real routing and PostgreSQL policies, including unfiltered SQL."""
import uuid

import pytest
from django.db import connection, DatabaseError, transaction

from tenant_app.models import Member
from tenant_app.regions import region_context

pytestmark = pytest.mark.django_db


def url(tenant, region="washington"):
    return f"/client/{tenant.test_domain}/{region}/api/members"


def create(client, endpoint, name):
    response = client.post(endpoint, {"name": name}, content_type="application/json")
    assert response.status_code == 200, response.content
    return response.json()


def test_regions_share_schema_but_isolate_all_operations(tenant_client, test_tenant):
    wa_url = url(test_tenant)
    co_url = url(test_tenant, "colarado")
    wa = create(tenant_client, wa_url, "Washington member")
    co = create(tenant_client, co_url, "Colarado member")
    assert wa["region"] == "washington"
    assert co["region"] == "colarado"
    assert tenant_client.get(wa_url).json() == [wa]
    assert tenant_client.get(co_url).json() == [co]
    for endpoint, foreign_id in [(wa_url, co["id"]), (co_url, wa["id"])]:
        detail = f"{endpoint}/{foreign_id}"
        assert tenant_client.get(detail).status_code == 404
        assert tenant_client.put(detail, {"name": "changed"}, content_type="application/json").status_code == 404
        assert tenant_client.delete(detail).status_code == 404
    assert tenant_client.get(co_url).json() == [co]
    # A direct query as the test administrator proves both rows are in one schema.
    connection.set_tenant(test_tenant)
    assert set(Member.objects.values_list("region", flat=True)) == {"washington", "colarado"}
    assert connection.schema_name == test_tenant.schema_name
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.region', true)")
        assert cursor.fetchone()[0] in (None, "")


def test_region_required_and_validated(tenant_client, test_tenant):
    assert tenant_client.get(f"/client/{test_tenant.test_domain}/api/members").status_code == 404
    for region in ["Washington", "bad_region", "a" * 64]:
        assert tenant_client.get(url(test_tenant, region)).status_code == 422
    endpoint = url(test_tenant)
    assert tenant_client.post(endpoint, {"name": "x", "region": "colarado"}, content_type="application/json").status_code == 422
    assert tenant_client.get(endpoint).json() == []


def test_openapi_and_docs(tenant_client, test_tenant):
    prefix = f"/client/{test_tenant.test_domain}/api"
    assert tenant_client.get(f"{prefix}/docs").status_code == 200
    response = tenant_client.get(f"{prefix}/openapi.json")
    assert response.status_code == 200
    path = next(value for key, value in response.json()["paths"].items() if key.endswith('/{region}/api/members'))
    assert any(p["name"] == "region" and p["in"] == "path" for p in path["get"]["parameters"])


@pytest.fixture
def restricted_role(test_tenant):
    connection.set_tenant(test_tenant)
    role = "region_test_" + uuid.uuid4().hex
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE ROLE {quote(role)} NOSUPERUSER NOBYPASSRLS NOLOGIN")
        cursor.execute(f"GRANT USAGE ON SCHEMA public, {quote(test_tenant.schema_name)} TO {quote(role)}")
        cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {quote(role)}")
        cursor.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {quote(test_tenant.schema_name)} TO {quote(role)}")
        cursor.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA {quote(test_tenant.schema_name)} TO {quote(role)}")
    return role  # pytest's transaction rollback removes the role and grants.


def test_rls_crud_without_application_filters(test_tenant, restricted_role):
    wa = Member.objects.create(region="washington", name="wa")
    co = Member.objects.create(region="colarado", name="co")
    with connection.cursor() as cursor:
        # Even the table owner must obey FORCE ROW LEVEL SECURITY.
        cursor.execute(f'ALTER TABLE tenant_app_member OWNER TO "{restricted_role}"')
        cursor.execute(f'SET LOCAL ROLE "{restricted_role}"')
    try:
        assert Member.objects.count() == 0
        with pytest.raises(DatabaseError), transaction.atomic():
            Member.objects.create(region="washington", name="no context")
        with region_context("washington"):
            assert list(Member.objects.values_list("id", flat=True)) == [wa.id]
            with connection.cursor() as cursor:
                cursor.execute("SELECT region FROM tenant_app_member")
                assert cursor.fetchall() == [("washington",)]
                cursor.execute("UPDATE tenant_app_member SET name = 'forbidden' WHERE id = %s", [co.id])
                assert cursor.rowcount == 0
                cursor.execute("DELETE FROM tenant_app_member WHERE id = %s", [co.id])
                assert cursor.rowcount == 0
            with pytest.raises(DatabaseError), transaction.atomic():
                Member.objects.create(region="colarado", name="forbidden")
            with pytest.raises(DatabaseError), transaction.atomic():
                Member.objects.filter(id=wa.id).update(region="colarado")
            allowed = Member.objects.create(region="washington", name="allowed")
            assert Member.objects.filter(id=allowed.id).update(name="updated") == 1
            assert Member.objects.filter(id=allowed.id).delete()[0] == 1
        with region_context("colarado"):
            assert list(Member.objects.values_list("name", flat=True)) == ["co"]
        assert Member.objects.count() == 0
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")


def test_api_with_restricted_role(tenant_client, test_tenant, restricted_role):
    with connection.cursor() as cursor:
        cursor.execute(f'SET LOCAL ROLE "{restricted_role}"')
    try:
        wa = create(tenant_client, url(test_tenant), "wa")
        co = create(tenant_client, url(test_tenant, "colarado"), "co")
        assert tenant_client.get(url(test_tenant)).json() == [wa]
        assert tenant_client.get(url(test_tenant, "colarado")).json() == [co]
        assert Member.objects.count() == 0
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET ROLE")


def test_nested_and_exception_context_cleanup(test_tenant):
    connection.set_tenant(test_tenant)
    def active_region():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.region', true)")
            return cursor.fetchone()[0] or ""
    with region_context("washington"):
        with region_context("colarado"):
            assert active_region() == "colarado"
        assert active_region() == "washington"
        with pytest.raises(DatabaseError):
            with region_context("colarado"):
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 / 0")
        assert active_region() == "washington"
    assert active_region() == ""
    with pytest.raises(ValueError):
        with region_context("bad_region"):
            pass


def test_migration_preserves_existing_members_in_default_region(test_tenant):
    from django.db.migrations.executor import MigrationExecutor

    connection.set_tenant(test_tenant)
    executor = MigrationExecutor(connection)
    old_target = [("tenant_app", "0001_initial")]
    new_target = [("tenant_app", "0002_member_region")]
    executor.migrate(old_target)
    try:
        old_member = executor.loader.project_state(old_target).apps.get_model("tenant_app", "Member")
        member = old_member.objects.create(name="Legacy member", phone="123", email="legacy@example.com")
    finally:
        MigrationExecutor(connection).migrate(new_target)
    migrated = Member.objects.get(pk=member.pk)
    assert migrated.region == "default"
    assert migrated.name == "Legacy member"
    assert migrated.email == "legacy@example.com"
    with connection.cursor() as cursor:
        cursor.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE oid = 'tenant_app_member'::regclass")
        assert cursor.fetchone() == (True, True)
