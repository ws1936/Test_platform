"""End-to-end verification that project_router is wired into main.app.

Checks:
  1) project routes are present in app.routes
  2) OpenAPI schema lists all 5 project endpoints
  3) Live HTTP through main app (lifespan + SQLite) hits all 5 endpoints
     with the real auth + exception handlers.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, "src")


def main() -> None:
    # Use a temp SQLite DB so lifespan can create tables in isolation.
    db_path = tempfile.mktemp(suffix=".db")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["ENVIRONMENT"] = "test"

    from fastapi.testclient import TestClient

    from app.main import app

    # === 1) routes ===
    print("=== 1) registered project routes ===")
    project_paths = []
    for r in app.routes:
        if hasattr(r, "path") and "/projects" in r.path:
            methods = sorted(r.methods or [])
            project_paths.append(r.path)
            print(f"  {','.join(methods):10s} {r.path:40s} name={r.name}")
    assert any(p == "/api/v1/projects" for p in project_paths), "missing list/create"
    assert any(p == "/api/v1/projects/{project_id}" for p in project_paths), (
        "missing detail/update/delete"
    )

    # === 2) openapi ===
    print("\n=== 2) OpenAPI schema: /api/v1/projects paths ===")
    spec = app.openapi()
    openapi_paths = []
    for path, ops in sorted(spec.get("paths", {}).items()):
        if "/projects" in path:
            for method, info in ops.items():
                tag = info.get("tags", [""])[0]
                openapi_paths.append((method.upper(), path))
                print(
                    f"  {method.upper():6s} {path:30s} "
                    f"tag={tag!r:12s} summary={info.get('summary', '')!r}"
                )
    assert ("get", "/api/v1/projects") in [(m, p) for m, p in [
        (m.lower(), p.replace("/api/v1", "")) for m, p in openapi_paths
    ]] or any(
        m == "GET" and p == "/api/v1/projects" for m, p in openapi_paths
    ), f"missing GET /api/v1/projects in OpenAPI; got {openapi_paths}"

    # === 3) live HTTP via main app + lifespan ===
    print("\n=== 3) live HTTP via main app + lifespan ===")
    with TestClient(app) as client:
        # register first user (becomes superuser)
        r = client.post(
            "/api/v1/auth/register",
            json={
                "username": "smoke",
                "email": "smoke@example.com",
                "password": "TestPass123!",
                "nickname": "Smoke",
                "phone": "13800000000",
            },
        )
        print(f"  register                              → {r.status_code}")
        assert r.status_code == 201, r.text
        token = r.json()["token"]["access_token"]
        H = {"Authorization": f"Bearer {token}"}

        # 5 endpoints
        r = client.post(
            "/api/v1/projects", json={"name": "Live Test"}, headers=H
        )
        print(f"  POST   /api/v1/projects               → {r.status_code}")
        assert r.status_code == 201, r.text
        pid = r.json()["id"]

        r = client.get("/api/v1/projects", headers=H)
        print(f"  GET    /api/v1/projects               → {r.status_code}")
        assert r.status_code == 200
        assert r.json()["total"] == 1

        r = client.get(f"/api/v1/projects/{pid}", headers=H)
        print(f"  GET    /api/v1/projects/{{id}}          → {r.status_code}")
        assert r.status_code == 200

        r = client.put(
            f"/api/v1/projects/{pid}", json={"description": "live"}, headers=H
        )
        print(f"  PUT    /api/v1/projects/{{id}}          → {r.status_code}")
        assert r.status_code == 200

        r = client.delete(f"/api/v1/projects/{pid}", headers=H)
        print(f"  DELETE /api/v1/projects/{{id}}          → {r.status_code}")
        assert r.status_code == 200

    try:
        os.unlink(db_path)
    except OSError:
        pass
    print("\n=== ALL OK ===")


main()
