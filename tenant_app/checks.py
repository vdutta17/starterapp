from django.core.checks import Error, Tags, register
from django.db import connections


@register(Tags.database, deploy=True)
def check_rls_role(app_configs, databases=None, **kwargs):
    errors = []
    for alias in databases or []:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
            superuser, bypass_rls = cursor.fetchone()
        if superuser or bypass_rls:
            errors.append(Error(
                f"Database '{alias}' uses a role that bypasses region row-level security.",
                hint="Run the server with a NOSUPERUSER NOBYPASSRLS role; use a separate migration role.",
                id="tenant_app.E001",
            ))
    return errors
