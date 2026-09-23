import pytest
import json
from tenant_app.models import Member
from django.db import connection

# Mark all tests in this module to use the database
pytestmark = pytest.mark.django_db(transaction=True) # Use transactions for speed

# Constant used in tests
NONEXISTENT_ID = 9999

def detail_url(tenant_domain, member):
    """Helper to get detail URL for a member, including tenant domain prefix"""
    return f'/client/{tenant_domain}/washington/api/members/{member.id}'

def test_list_members(tenant_client, test_tenant, member1, member2):
    """Test listing all members"""
    domain = test_tenant.test_domain # Get domain from the tenant fixture
    list_url = f'/client/{domain}/washington/api/members' # Construct URL dynamically

    response = tenant_client.get(list_url)
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 2

    # Check member data is correct (order might vary, sort by id)
    members_data = sorted(data, key=lambda x: x['id'])
    assert members_data[0]['id'] == member1.id
    assert members_data[0]['name'] == member1.name
    assert members_data[0]['email'] == member1.email
    assert members_data[0]['phone'] == member1.phone
    assert members_data[1]['id'] == member2.id
    assert members_data[1]['name'] == member2.name

def test_create_member(tenant_client, test_tenant):
    """Test creating a new member"""
    domain = test_tenant.test_domain
    list_url = f'/client/{domain}/washington/api/members'

    new_member_data = {
        "name": "New Test User",
        "email": "new@example.com",
        "phone": "555-555-5555"
    }

    response = tenant_client.post(
        list_url, # Use dynamic URL
        data=json.dumps(new_member_data),
        content_type='application/json'
    )
    data = response.json()

    assert response.status_code == 200
    assert 'id' in data
    assert data['name'] == new_member_data['name']
    assert data['email'] == new_member_data['email']
    assert data['phone'] == new_member_data['phone']

    # Verify in database (ensure connection is still set correctly)
    connection.set_tenant(test_tenant)
    created_member = Member.objects.get(id=data['id'])
    assert created_member.name == new_member_data['name']
    connection.set_schema_to_public()

def test_create_member_invalid_data(tenant_client, test_tenant):
    """Test creating a member with invalid data (missing required fields)"""
    domain = test_tenant.test_domain
    list_url = f'/client/{domain}/washington/api/members'

    invalid_data = {
        # Missing required 'name' field
        "email": "invalid@example.com",
        "phone": "555-555-5555"
    }

    response = tenant_client.post(
        list_url, # Use dynamic URL
        data=json.dumps(invalid_data),
        content_type='application/json'
    )

    # Assuming Ninja returns 422 for validation errors
    assert response.status_code == 422

def test_get_member(tenant_client, test_tenant, member1):
    """Test retrieving a specific member"""
    domain = test_tenant.test_domain
    url = detail_url(domain, member1) # Pass domain to helper

    response = tenant_client.get(url)
    data = response.json()

    assert response.status_code == 200
    assert data['id'] == member1.id
    assert data['name'] == member1.name
    assert data['email'] == member1.email
    assert data['phone'] == member1.phone

def test_get_nonexistent_member(tenant_client, test_tenant):
    """Test retrieving a member that doesn't exist"""
    domain = test_tenant.test_domain
    nonexistent_url = f'/client/{domain}/washington/api/members/{NONEXISTENT_ID}' # Construct URL dynamically

    response = tenant_client.get(nonexistent_url)
    # Assuming Ninja returns 404 when Member.DoesNotExist is caught by its handler
    assert response.status_code == 404

def test_update_member(tenant_client, test_tenant, member1):
    """Test updating a member"""
    domain = test_tenant.test_domain
    url = detail_url(domain, member1) # Pass domain to helper

    update_data = {
        "name": "Updated Test User",
        "email": "updated@example.com",
        "phone": "999-999-9999"
    }

    response = tenant_client.put(
        url,
        data=json.dumps(update_data),
        content_type='application/json'
    )
    data = response.json()

    assert response.status_code == 200
    assert data['name'] == update_data['name']
    assert data['email'] == update_data['email']
    assert data['phone'] == update_data['phone']

    # Verify in database
    connection.set_tenant(test_tenant)
    updated_member = Member.objects.get(id=member1.id)
    assert updated_member.name == update_data['name']
    assert updated_member.email == update_data['email']
    assert updated_member.phone == update_data['phone']
    connection.set_schema_to_public()

def test_update_nonexistent_member(tenant_client, test_tenant):
    """Test updating a member that doesn't exist"""
    domain = test_tenant.test_domain
    nonexistent_url = f'/client/{domain}/washington/api/members/{NONEXISTENT_ID}' # Construct URL dynamically

    update_data = {
        "name": "This Won't Work",
        "email": "wont@example.com",
        "phone": "000-000-0000"
    }

    response = tenant_client.put(
        nonexistent_url, # Use dynamic URL
        data=json.dumps(update_data),
        content_type='application/json'
    )
    assert response.status_code == 404

def test_update_member_invalid_data(tenant_client, test_tenant, member1):
    """Test updating a member with invalid data"""
    domain = test_tenant.test_domain
    url = detail_url(domain, member1) # Pass domain to helper

    invalid_data = {
        # Missing required 'name' field in MemberSchema
        "email": "stillneeded@example.com",
        "phone": "123-123-1234"
    }

    response = tenant_client.put(
        url,
        data=json.dumps(invalid_data),
        content_type='application/json'
    )
    assert response.status_code == 422 # Assuming Ninja validation error

def test_partial_update_member(tenant_client, test_tenant, member1):
    """
    Test partial update of a member.
    NOTE: Your current API PUT handler requires all fields in the payload schema.
    For partial updates (PATCH), you'd typically need a different schema or logic.
    This test assumes the PUT behaves like PATCH if fields are missing in the *payload*,
    which might not be the case depending on Ninja/Pydantic defaults.
    Let's test the behavior of the *current* PUT implementation where name is required.
    If you implement PATCH, you'd adjust this test.
    """
    domain = test_tenant.test_domain
    url = detail_url(domain, member1) # Pass domain to helper

    # Your MemberSchema requires 'name'. Let's provide it.
    # If email/phone are optional in the schema, they can be omitted for PUT.
    update_data = {
        "name": "Partially Updated User",
        # "email": None, # Explicitly setting to None might clear it
        # "phone": None, # Explicitly setting to None might clear it
        # Omitting optional fields if the schema allows
    }

    response = tenant_client.put(
        url,
        data=json.dumps(update_data),
        content_type='application/json'
    )
    data = response.json()

    assert response.status_code == 200

    # Verify in database
    connection.set_tenant(test_tenant)
    updated_member = Member.objects.get(id=member1.id)
    assert updated_member.name == update_data['name']
    # Check if email/phone remained unchanged (depends on API logic)
    assert updated_member.email == member1.email
    assert updated_member.phone == member1.phone
    connection.set_schema_to_public()

def test_delete_member(tenant_client, test_tenant, member1):
    """Test deleting a member"""
    domain = test_tenant.test_domain
    url = detail_url(domain, member1) # Pass domain to helper

    response = tenant_client.delete(url)
    assert response.status_code == 200

    # Verify member was deleted from database
    connection.set_tenant(test_tenant)
    with pytest.raises(Member.DoesNotExist):
        Member.objects.get(id=member1.id)
    connection.set_schema_to_public()

def test_delete_nonexistent_member(tenant_client, test_tenant):
    """Test deleting a member that doesn't exist"""
    domain = test_tenant.test_domain
    nonexistent_url = f'/client/{domain}/washington/api/members/{NONEXISTENT_ID}' # Construct URL dynamically

    response = tenant_client.delete(nonexistent_url)
    assert response.status_code == 404 