from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("tenant_app", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="member",
            name="region",
            field=models.SlugField(max_length=63, default="default", db_index=True),
            preserve_default=False,
        ),
        migrations.RunSQL(
            sql="""
                ALTER TABLE tenant_app_member ENABLE ROW LEVEL SECURITY;
                ALTER TABLE tenant_app_member FORCE ROW LEVEL SECURITY;
                CREATE POLICY member_region ON tenant_app_member
                USING (region = NULLIF(current_setting('app.region', true), ''))
                WITH CHECK (region = NULLIF(current_setting('app.region', true), ''));
            """,
            reverse_sql="""
                DROP POLICY member_region ON tenant_app_member;
                ALTER TABLE tenant_app_member NO FORCE ROW LEVEL SECURITY;
                ALTER TABLE tenant_app_member DISABLE ROW LEVEL SECURITY;
            """,
        ),
    ]
