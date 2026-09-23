from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, SimpleTestCase

from .models import Client


class ClientAdminTests(SimpleTestCase):
    def test_add_form_renders_with_domain_inline(self):
        request = RequestFactory().get(
            '/client/tenant1/admin/shared_app/client/add/'
        )
        request.user = get_user_model()(
            username='admin', is_active=True, is_staff=True, is_superuser=True
        )
        # Rendering needs a content type ID, but no persisted tenant or database.
        with patch(
            'django.contrib.admin.options.get_content_type_for_model',
            return_value=ContentType(pk=1, app_label='shared_app', model='client'),
        ):
            response = admin.site._registry[Client].add_view(request)
            response.render()

        self.assertContains(response, 'name="schema_name"')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="domains-0-domain"')
