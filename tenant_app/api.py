from datetime import datetime
from typing import Annotated, List, Optional

from django.core.exceptions import ObjectDoesNotExist
from ninja import NinjaAPI, Path, Schema
from pydantic import ConfigDict

from .models import Member
from .regions import region_context

api = NinjaAPI(title="Tenant API", urls_namespace="tenant_api", docs_url="/api/docs", openapi_url="/api/openapi.json")
RegionPath = Annotated[str, Path(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=63)]


class MemberUpdateSchema(Schema):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class MemberResponseSchema(Schema):
    id: int
    region: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime


@api.exception_handler(ObjectDoesNotExist)
def object_does_not_exist_handler(request, exc):
    return api.create_response(request, {"detail": "Object not found."}, status=404)


@api.get("/{region}/api/members", response=List[MemberResponseSchema])
def list_members(request, region: RegionPath):
    with region_context(region):
        # Evaluate before the transaction-local database scope is cleared.
        return list(Member.objects.filter(region=region))


@api.post("/{region}/api/members", response=MemberResponseSchema)
def create_member(request, region: RegionPath, payload: MemberUpdateSchema):
    with region_context(region):
        return Member.objects.create(
            region=region, name=payload.name,
            phone=payload.phone or "", email=payload.email or "",
        )


@api.get("/{region}/api/members/{member_id}", response=MemberResponseSchema)
def get_member(request, region: RegionPath, member_id: int):
    with region_context(region):
        return Member.objects.get(region=region, id=member_id)


@api.put("/{region}/api/members/{member_id}", response=MemberResponseSchema)
def update_member(request, region: RegionPath, member_id: int, payload: MemberUpdateSchema):
    with region_context(region):
        member = Member.objects.get(region=region, id=member_id)
        member.name = payload.name
        if payload.phone is not None:
            member.phone = payload.phone
        if payload.email is not None:
            member.email = payload.email
        # Keep the application-level region predicate on the write as well.
        Member.objects.filter(region=region, id=member_id).update(
            name=member.name, phone=member.phone, email=member.email,
        )
        return member


@api.delete("/{region}/api/members/{member_id}", response=None)
def delete_member(request, region: RegionPath, member_id: int):
    with region_context(region):
        member = Member.objects.get(region=region, id=member_id)
        Member.objects.filter(region=region, id=member.id).delete()
        return None
