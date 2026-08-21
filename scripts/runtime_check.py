"""End-to-end runtime check for the first-user Project creation flow.

This script boots the FastAPI app in-process via httpx.ASGITransport
so it does not require a running uvicorn.  It then exercises:

* register the first user (becomes superuser)
* create a project
* verify the new project is in GET /projects
* verify duplicate creation returns 409
* verify a stale token is rejected with 401

Run via::

    ENVIRONMENT=test DATABASE_URL=sqlite+aiosqlite:///:memory: \\
    JWT_SECRET_KEY=test-secret-key-for-pytest-only-not-for-prod \\
    uv run --no-sync python scripts/runtime_check.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from typing import Tuple

import httpx


def _patch_sqlite_path_for_tests() -> None:
    # The default DATABASE_URL points to a non-existing Postgres instance.
    # For the runtime check we want an isolated SQLite file inside the
    # repository's temp dir so multiple runs don't conflict.
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("JWT_SECRET_KEY", "runtime-check-secret-key-32+chars")
    os.environ.setdefault("ENVIRONMENT", "test")


async def _create_user(client: httpx.AsyncClient, email: str, username: str) -> Tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "Runtime123!",
            "nickname": "Runtime",
            "phone": "13800000000",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["user"]["id"], body["token"]["access_token"]


async def main() -> int:
    _patch_sqlite_path_for_tests()

    # Reuse the real application so we exercise the full middleware/router
    # stack (auth, exception handlers, etc).
    from app.main import app  # noqa: WPS433 - late import on purpose
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    from app.infrastructure.database.session import Base

    # Build a fresh in-memory schema and override the get_db dependency so
    # we get a clean DB for this run.  This mirrors what the pytest
    # fixture does, but standalone.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    from app.infrastructure.database.session import get_db

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://runtime-check") as client:
        # ---- 1. First user → superuser, then create project ------------
        suffix = uuid.uuid4().hex[:8]
        user_id, token = await _create_user(
            client,
            email=f"first-{suffix}@example.com",
            username=f"first-{suffix}",
        )
        print(f"OK  register   user_id={user_id}")

        project_name = f"Runtime Project {suffix}"
        resp = await client.post(
            "/api/v1/projects",
            json={"name": project_name, "description": "runtime"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, resp.text
        project = resp.json()
        project_id = project["id"]
        assert project["name"] == project_name
        assert project["owner_id"] == user_id
        print(f"OK  create     project_id={project_id}")

        # ---- 2. List projects -> contains the new one -------------------
        resp = await client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        names = [p["name"] for p in body["items"]]
        assert project_name in names, body
        print(f"OK  list       found in {body['total']} projects")

        # ---- 3. Duplicate name -> 409 -------------------------------
        resp = await client.post(
            "/api/v1/projects",
            json={"name": project_name, "description": "dup"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert body["code"] == "PROJECT_NAME_TAKEN", body
        print(f"OK  duplicate  409 PROJECT_NAME_TAKEN")

        # ---- 4. Stale token (bumped version) -> 401 ----------------
        from app.common.security import decode_token
        from app.domain.user.model import User
        from sqlalchemy import select

        # Bump token_version via the engine directly.
        async with session_factory() as session:
            res = await session.execute(
                select(User).where(User.id == uuid.UUID(user_id))
            )
            db_user = res.scalar_one()
            db_user.token_version = db_user.token_version + 1
            await session.commit()

        resp = await client.post(
            "/api/v1/projects",
            json={"name": "StaleRequest", "description": "stale"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401, resp.text
        body = resp.json()
        assert body["code"] == "TOKEN_INVALID", body
        print("OK  stale      401 TOKEN_INVALID")

        # ---- 5. Re-login to obtain a fresh token (the previous one was
        # rotated in step 4).  Validation behavior must still work with
        # a healthy token. -----------------------------------------------
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": f"first-{suffix}@example.com", "password": "Runtime123!"},
        )
        assert resp.status_code == 200, resp.text
        fresh_token = resp.json()["token"]["access_token"]

        resp = await client.post(
            "/api/v1/projects",
            json={"name": ""},
            headers={"Authorization": f"Bearer {fresh_token}"},
        )
        assert resp.status_code == 422, resp.text
        body = resp.json()
        assert body["code"] == "VALIDATION_ERROR", body
        assert body["details"][0]["field"].endswith("name"), body
        print("OK  invalid    422 VALIDATION_ERROR")

    print("\nALL OK: first-user Project create flow is healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
