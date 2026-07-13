"""Smoke test for Project Pydantic schemas."""
import sys, uuid
from datetime import datetime, timezone

sys.path.insert(0, "src")

print("=== import ===")
from app.domain.project.schema import (
    ProjectBase,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    ProjectListQuery,
    ProjectResponse,
    ProjectListResponse,
)
print("imports ok\n")

print("=== 1) ProjectCreateRequest: happy path ===")
req = ProjectCreateRequest(name="Order Service", description="smoke test")
print(f"  {req.model_dump()}\n")

print("=== 2) ProjectCreateRequest: empty name should fail ===")
try:
    ProjectCreateRequest(name="", description="x")
    print("  FAIL: empty name accepted")
except Exception as e:
    print(f"  PASS: {type(e).__name__}: {e.errors()[0]['msg']}\n")

print("=== 3) ProjectCreateRequest: 101-char name should fail ===")
try:
    ProjectCreateRequest(name="a" * 101)
    print("  FAIL: 101-char name accepted")
except Exception as e:
    print(f"  PASS: {type(e).__name__}\n")

print("=== 4) ProjectCreateRequest: must reject extra owner_id (security) ===")
try:
    ProjectCreateRequest(name="x", owner_id=uuid.uuid4())
    print("  FAIL: owner_id was accepted")
except Exception as e:
    print(f"  PASS: {type(e).__name__} (owner_id rejected)\n")

print("=== 5) ProjectUpdateRequest: all fields optional ===")
u = ProjectUpdateRequest()
print(f"  empty update: {u.model_dump(exclude_none=True)}")
u = ProjectUpdateRequest(name="new")
print(f"  partial: {u.model_dump(exclude_none=True)}\n")

print("=== 6) ProjectListQuery: defaults + constraints ===")
q = ProjectListQuery()
print(f"  defaults: page={q.page} size={q.size} search={q.search!r} owner={q.owner_id}")
try:
    ProjectListQuery(page=0)
    print("  FAIL: page=0 accepted")
except Exception as e:
    print(f"  PASS: {type(e).__name__} rejects page=0")
try:
    ProjectListQuery(size=500)
    print("  FAIL: size=500 accepted")
except Exception as e:
    print(f"  PASS: {type(e).__name__} rejects size=500\n")

print("=== 7) ProjectResponse: from ORM ApiProject ===")
from app.domain.project.model import ApiProject
fake_id = uuid.uuid4()
fake_owner = uuid.uuid4()
now = datetime.now(timezone.utc)
orm = ApiProject(
    id=fake_id,
    name="X",
    description="d",
    owner_id=fake_owner,
    created_at=now,
    updated_at=now,
)
resp = ProjectResponse.model_validate(orm)
print(f"  {resp.model_dump_json()}\n")

print("=== 8) ProjectListResponse: nested ===")
lst = ProjectListResponse(items=[resp, resp], total=2, page=1, size=20)
print(f"  total={lst.total} page={lst.page} size={lst.size} items={len(lst.items)}\n")

print("=== 9) JSON schema (OpenAPI snippet) ===")
import json
print(json.dumps(ProjectCreateRequest.model_json_schema(), indent=2)[:300], "...\n")

print("=== ALL DONE ===")