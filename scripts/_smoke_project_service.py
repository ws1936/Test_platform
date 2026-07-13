"""End-to-end smoke test for Project repository + service.

Covers:
  * Repository CRUD + list_paginated (with search + owner filter)
  * Service.create_project (owner injected from current_user)
  * Service.get_project (404 path)
  * Service.list_projects (pagination + filter)
  * Service.update_project (owner success, non-owner forbidden,
    admin override)
  * Service.delete_project (owner success, non-owner forbidden)
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "src")

from sqlalchemy import delete

from app.common.exceptions import ForbiddenException, ProjectNotFoundException
from app.domain.project.model import ApiProject
from app.domain.project.repository import ProjectRepository
from app.domain.project.schema import (
    ProjectCreateRequest,
    ProjectListQuery,
    ProjectUpdateRequest,
)
from app.domain.project.service import ProjectService
from app.domain.user.model import User
from app.infrastructure.database.session import async_session_factory


async def _make_user(s, *, is_superuser: bool = False) -> User:
    uid = uuid.uuid4()
    u = User(
        id=uid,
        username=f"u_{uid.hex[:8]}",
        email=f"{uid.hex[:8]}@example.com",
        hashed_password="x",
        is_superuser=is_superuser,
    )
    s.add(u)
    await s.commit()
    return u


async def main() -> None:
    async with async_session_factory() as s:
        owner = await _make_user(s)
        stranger = await _make_user(s)
        admin = await _make_user(s, is_superuser=True)
        print(f"users: owner={owner.id} stranger={stranger.id} admin={admin.id}")

        svc = ProjectService(s)

        # === A) create_project: owner injected ===
        print("\n[A] create_project")
        req = ProjectCreateRequest(name="Order Svc", description="checkout pipeline")
        resp = await svc.create_project(req, current_user=owner)
        assert resp.owner_id == owner.id, "owner_id must be injected from current_user"
        assert resp.name == "Order Svc"
        pid = resp.id
        print(f"  created project {pid} owner={resp.owner_id} name={resp.name!r}")

        # === G) get_project: not found ===
        print("\n[G] get_project: missing → ProjectNotFoundException")
        try:
            await svc.get_project(uuid.uuid4())
            print("  FAIL: did not raise")
        except ProjectNotFoundException as e:
            print(f"  PASS: code={e.code} status={e.status_code} msg={e.message!r}")

        # === B) list_projects: pagination + search ===
        print("\n[B] list_projects: pagination + search")
        # add a few more projects under different owners
        await svc.create_project(
            ProjectCreateRequest(name="User Svc", description="users api"),
            current_user=owner,
        )
        await svc.create_project(
            ProjectCreateRequest(name="Billing Svc", description="billing"),
            current_user=admin,
        )

        all_list = await svc.list_projects(ProjectListQuery(page=1, size=50))
        print(f"  total projects={all_list.total}")
        assert all_list.total >= 3

        only_order = await svc.list_projects(
            ProjectListQuery(page=1, size=50, search="order")
        )
        names = [p.name for p in only_order.items]
        print(f"  search='order' → {names}")
        assert all("order" in n.lower() for n in names)

        # === C) list_projects: owner filter ===
        print("\n[C] list_projects: owner_id filter")
        owner_list = await svc.list_projects(
            ProjectListQuery(page=1, size=50, owner_id=owner.id)
        )
        owners = {p.owner_id for p in owner_list.items}
        print(f"  owner={owner.id} → {len(owner_list.items)} items, distinct owners={owners}")
        assert owners == {owner.id}, "filter must restrict to owner's projects"

        # === D) update_project: owner success ===
        print("\n[D] update_project by owner")
        updated = await svc.update_project(
            pid,
            ProjectUpdateRequest(description="updated by owner"),
            current_user=owner,
        )
        assert updated.description == "updated by owner"
        print(f"  description now={updated.description!r}")

        # === E) update_project: stranger → ForbiddenException ===
        print("\n[E] update_project by stranger → ForbiddenException")
        try:
            await svc.update_project(
                pid, ProjectUpdateRequest(name="hijacked"), current_user=stranger
            )
            print("  FAIL: stranger update was allowed")
        except ForbiddenException as e:
            print(f"  PASS: code={e.code} status={e.status_code}")

        # === F) update_project: admin override ===
        print("\n[F] update_project by admin (non-owner) → OK")
        admin_update = await svc.update_project(
            pid, ProjectUpdateRequest(name="Order Svc (admin renamed)"), current_user=admin
        )
        assert admin_update.name == "Order Svc (admin renamed)"
        print(f"  admin renamed project to {admin_update.name!r}")

        # === H) delete_project: stranger → ForbiddenException ===
        print("\n[H] delete_project by stranger → ForbiddenException")
        try:
            await svc.delete_project(pid, current_user=stranger)
            print("  FAIL: stranger delete was allowed")
        except ForbiddenException as e:
            print(f"  PASS: code={e.code} status={e.status_code}")

        # === I) delete_project: owner success ===
        print("\n[I] delete_project by owner → OK")
        await svc.delete_project(pid, current_user=owner)
        try:
            await svc.get_project(pid)
            print("  FAIL: project still exists")
        except ProjectNotFoundException:
            print("  PASS: project removed")

        # === cleanup ===
        await s.execute(delete(ApiProject))
        await s.execute(delete(User))
        await s.commit()
        print("\ncleanup ok")


asyncio.run(main())
print("\n=== ALL DONE ===")