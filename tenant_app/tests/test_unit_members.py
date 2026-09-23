from contextlib import nullcontext

import pytest


@pytest.fixture(autouse=True)
def mock_region_context(mocker):
    mocker.patch("tenant_app.api.region_context", side_effect=lambda region: nullcontext())

from tenant_app.api import MemberUpdateSchema, list_members, create_member, get_member, update_member, delete_member
from tenant_app.models import Member

# Constant used in tests
NONEXISTENT_ID = 9999

# --- Unit Tests ---
def test_unit_list_members(mocker, member1_unit_data, member2_unit_data):
    """Test listing all members (unit)"""
    mock_all = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_all.return_value = [member1_unit_data, member2_unit_data]

    result = list_members(None, "washington") # Pass None for request as it's unused

    assert len(result) == 2
    assert isinstance(result, list)
    assert result[0].id == 1
    assert result[0].name == "Test User 1"
    assert result[1].id == 2
    assert result[1].name == "Test User 2"
    mock_all.assert_called_once_with(region="washington")

def test_unit_create_member(mocker):
    """Test creating a new member (unit)"""
    mock_create = mocker.patch('tenant_app.api.Member.objects.create')
    created_instance = Member(id=3, name="New Test User", email="new@example.com", phone="555-555-5555")
    mock_create.return_value = created_instance

    payload = MemberUpdateSchema(
        name="New Test User",
        email="new@example.com",
        phone="555-555-5555"
    )

    result = create_member(None, "washington", payload)

    assert result.id == 3
    assert result.name == "New Test User"
    assert result.email == "new@example.com"
    assert result.phone == "555-555-5555"
    mock_create.assert_called_once_with(
        region="washington",
        name="New Test User",
        email="new@example.com",
        phone="555-555-5555"
    )

def test_unit_get_member(mocker, member1_unit_data):
    """Test retrieving a specific member (unit)"""
    mock_get = mocker.patch('tenant_app.api.Member.objects.get')
    mock_filter = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_get.return_value = member1_unit_data

    result = get_member(None, "washington", 1)

    assert result.id == 1
    assert result.name == "Test User 1"
    assert result.email == "test1@example.com"
    mock_get.assert_called_once_with(region="washington", id=1)

def test_unit_get_nonexistent_member(mocker):
    """Test retrieving a member that doesn't exist (unit)"""
    mock_get = mocker.patch('tenant_app.api.Member.objects.get')
    mock_filter = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_get.side_effect = Member.DoesNotExist

    # We expect the exception to be raised and handled by the ninja framework
    with pytest.raises(Member.DoesNotExist):
        get_member(None, "washington", NONEXISTENT_ID)

    mock_get.assert_called_once_with(region="washington", id=NONEXISTENT_ID)

def test_unit_update_member(mocker):
    """Test updating a member (unit)"""
    mock_get = mocker.patch('tenant_app.api.Member.objects.get')
    mock_filter = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_member_instance = mocker.MagicMock(spec=Member)
    mock_member_instance.id = 1
    mock_member_instance.name = "Original Name"
    mock_member_instance.email = "original@example.com"
    mock_member_instance.phone = "111-111-1111"
    mock_get.return_value = mock_member_instance

    payload = MemberUpdateSchema(
        name="Updated Test User",
        email="updated@example.com",
        phone="999-999-9999"
    )

    result = update_member(None, "washington", 1, payload)

    mock_get.assert_called_once_with(region="washington", id=1)
    assert mock_member_instance.name == "Updated Test User"
    assert mock_member_instance.email == "updated@example.com"
    assert mock_member_instance.phone == "999-999-9999"
    mock_filter.assert_called_once_with(region="washington", id=1)
    mock_filter.return_value.update.assert_called_once()
    assert result == mock_member_instance

def test_unit_update_nonexistent_member(mocker):
    """Test updating a member that doesn't exist (unit)"""
    mock_get = mocker.patch('tenant_app.api.Member.objects.get')
    mock_filter = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_get.side_effect = Member.DoesNotExist

    payload = MemberUpdateSchema(
        name="This Won't Work",
        email="wont@example.com",
        phone="000-000-0000"
    )

    # We expect the exception to be raised and handled by the ninja framework
    with pytest.raises(Member.DoesNotExist):
        update_member(None, "washington", NONEXISTENT_ID, payload)

    mock_get.assert_called_once_with(region="washington", id=NONEXISTENT_ID)

def test_unit_partial_update_member(mocker):
    """Test partially updating a member (unit) - based on current API logic"""
    mock_get = mocker.patch('tenant_app.api.Member.objects.get')
    mock_filter = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_member_instance = mocker.MagicMock(spec=Member)
    mock_member_instance.id = 1
    mock_member_instance.name = "Original Name"
    mock_member_instance.email = "original@example.com"
    mock_member_instance.phone = "111-111-1111"
    mock_get.return_value = mock_member_instance

    # Payload requires 'name'. Email/Phone are optional in schema,
    # but API logic checks for None before updating.
    payload = MemberUpdateSchema(
        name="Partially Updated User",
        email=None, # Explicit None in payload
        phone=None  # Explicit None in payload
    )

    result = update_member(None, "washington", 1, payload)

    mock_get.assert_called_once_with(region="washington", id=1)
    assert mock_member_instance.name == "Partially Updated User"
    # API logic checks `if payload.email is not None:`, so original value remains
    assert mock_member_instance.email == "original@example.com"
    # API logic checks `if payload.phone is not None:`, so original value remains
    assert mock_member_instance.phone == "111-111-1111"
    mock_filter.assert_called_once_with(region="washington", id=1)
    mock_filter.return_value.update.assert_called_once()
    assert result == mock_member_instance

def test_unit_delete_member(mocker):
    """Test deleting a member (unit)"""
    mock_get = mocker.patch('tenant_app.api.Member.objects.get')
    mock_filter = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_member_instance = mocker.MagicMock(spec=Member)
    mock_member_instance.id = 1
    mock_get.return_value = mock_member_instance

    result = delete_member(None, "washington", 1)

    mock_get.assert_called_once_with(region="washington", id=1)
    mock_filter.assert_called_once_with(region="washington", id=1)
    mock_filter.return_value.delete.assert_called_once()
    # Delete returns an empty response
    assert result is None

def test_unit_delete_nonexistent_member(mocker):
    """Test deleting a member that doesn't exist (unit)"""
    mock_get = mocker.patch('tenant_app.api.Member.objects.get')
    mock_filter = mocker.patch('tenant_app.api.Member.objects.filter')
    mock_get.side_effect = Member.DoesNotExist

    # We expect the exception to be raised and handled by the ninja framework
    with pytest.raises(Member.DoesNotExist):
        delete_member(None, "washington", NONEXISTENT_ID)

    mock_get.assert_called_once_with(region="washington", id=NONEXISTENT_ID)
