"""Transaction-local region scope for API calls and background jobs."""
from contextlib import contextmanager
import re

from django.db import connection, transaction


@contextmanager
def region_context(region):
    if (
        not isinstance(region, str)
        or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", region)
        or len(region) > 63
    ):
        raise ValueError("Region must be a lowercase slug of at most 63 characters.")
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.region', true)")
            previous = cursor.fetchone()[0] or ""
            cursor.execute("SELECT set_config('app.region', %s, true)", [region])
        try:
            yield
        except BaseException:
            # atomic() rolls back the scope, including its local settings.
            raise
        else:
            if not connection.needs_rollback:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT set_config('app.region', %s, true)", [previous])
