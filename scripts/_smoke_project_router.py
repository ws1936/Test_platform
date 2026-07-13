"""End-to-end HTTP test for the project router via FastAPI TestClient.

Uses ``app.dependency_overrides`` to bypass JWT authentication and inject
a known ``User`` as the current user, so the test focuses on routing +
service wiring rather than the auth layer.
"""

from __future__ import annotations

import asyncio
import sys
import uuid

sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.common.dependencies import get_current_user
from app.domain.project.model import ApiProject
from app.domain.user.model import User
from app.infrastructure.database.session import async_session_factory
from app.main import app


async def _make_user(*, is_superuser: bool = False) -> User:
    uid = uuid.uuid4()
    async with async_session_factory() as s:
        u = User(
            id=uid,
            username=f"router_{uid.hex[:8]}",
            email=f"router_{uid.hex[:8]}@example.com",
            hashed_password="x",
            is_superuser=is_superuser,
        )
        s.add(u)
        await s.commit()
        await s.refresh(u)
    return u


async def _cleanup(user_ids: list[uuid.UUID]) -> None:
    async with async_session_factory() as s:
        await s.execute(delete(ApiProject))
        await s.execute(delete(User).where(User.id.in_(user_ids)))
        await s.commit()


def main() -> None:
    owner = asyncio.run(_make_user())
    stranger = asyncio.run(_make_user())
    admin = asyncio.run(_make_user(is_superuser=True))
    print(f"users: owner={owner.id} stranger={stranger.id} admin={admin.id}\n")

    with TestClient(app) as client:
        # === 1) POST as owner ===
        app.dependency_overrides[get_current_user] = lambda: owner
        r = client.post(
            "/api/v1/projects",
            json={"name": "Order Svc", "description": "checkout pipeline"},
        )
        print(f"[1] POST /projects (owner) → {r.status_code}")
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["owner_id"] == str(owner.id), "owner_id must come from current_user"
        assert body["name"] == "Order Svc"
        pid = body["id"]
        print(f"    id={pid} owner_id={body['owner_id']} name={body['name']!r}")

        # === 2) GET list ===
        r = client.get("/api/v1/projects")
        print(f"[2] GET /projects → {r.status_code}")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total" in body and "page" in body
        print(f"    total={body['total']} items={len(body['items'])} page={body['page']}")

        # === 3) GET list with search ===
        r = client.get("/api/v1/projects?search=order")
        print(f"[3] GET /projects?search=order → {r.status_code}")
        assert r.status_code == 200
        body = r.json()
        names = [p["name"] for p in body["items"]]
        print(f"    hits={names}")
        assert all("order" in n.lower() for n in names)

        # === 4) GET detail ===
        r = client.get(f"/api/v1/projects/{pid}")
        print(f"[4] GET /projects/{{id}} → {r.status_code}")
        assert r.status_code == 200
        assert r.json()["id"] == pid

        # === 5) PUT update by owner ===
        r = client.put(
            f"/api/v1/projects/{pid}", json={"description": "updated by owner"}
        )
        print(f"[5] PUT /projects/{{id}} (owner) → {r.status_code}")
        assert r.status_code == 200
        assert r.json()["description"] == "updated by owner"

        # === 6) PUT update by stranger → 403 ===
        app.dependency_overrides[get_current_user] = lambda: stranger
        r = client.put(f"/api/v1/projects/{pid}", json={"name": "hijacked"})
        print(f"[6] PUT /projects/{{id}} (stranger) → {r.status_code}")
        assert r.status_code == 403
        body = r.json()
        print(f"    code={body.get('code')} message={body.get('message')!r}")

        # === 7) DELETE by stranger → 403 ===
        r = client.delete(f"/api/v1/projects/{pid}")
        print(f"[7] DELETE /projects/{{id}} (stranger) → {r.status_code}")
        assert r.status_code == 403

        # === 8) PUT by admin (non-owner but superuser) → 200 ===
        app.dependency_overrides[get_current_user] = lambda: admin
        r = client.put(
            f"/api/v1/projects/{pid}", json={"name": "Order Svc (admin renamed)"}
        )
        print(f"[8] PUT /projects/{{id}} (admin) → {r.status_code}")
        assert r.status_code == 200
        assert r.json()["name"] == "Order Svc (admin renamed)"

        # === 9) GET not found → 404 ===
        r = client.get(f"/api/v1/projects/{uuid.uuid4()}")
        print(f"[9] GET missing → {r.status_code}")
        assert r.status_code == 404
        body = r.json()
        print(f"    code={body.get('code')} message={body.get('message')!r}")

        # === 10) POST with extra owner_id → 422 (extra="forbid") ===
        app.dependency_overrides[get_current_user] = lambda: owner
        r = client.post(
            "/api/v1/projects",
            json={"name": "x", "owner_id": str(stranger.id)},
        )
        print(f"[10] POST with extra owner_id → {r.status_code} (expect 422)")
        assert r.status_code == 422

        # === 11) POST empty name → 422 ===
        r = client.post("/api/v1/projects", json={"name": ""})
        print(f"[11] POST empty name → {r.status_code} (expect 422)")
        assert r.status_code == 422

        # === 12) DELETE by owner → 200 + message body ===
        r = client.delete(f"/api/v1/projects/{pid}")
        print(f"[12] DELETE /projects/{{id}} (owner) → {r.status_code}")
        assert r.status_code == 200
        assert "message" in r.json()
        print(f"    message={r.json()['message']!r}")

        # === 13) GET after delete → 404 ===
        r = client.get(f"/api/v1/projects/{pid}")
        print(f"[13] GET after delete → {r.status_code}")
        assert r.status_code == 404

        # === 14) No auth → 401 ===
        app.dependency_overrides.clear()
        r = client.get("/api/v1/projects")
        print(f"[14] GET without auth → {r.status_code} (expect 401)")
        assert r.status_code == 401

    # cleanup
    asyncio.run(_cleanup([owner.id, stranger.id, admin.id]))
    print("\ncleanup ok")


main()
print("\n=== ALL DONE ===")