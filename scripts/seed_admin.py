"""Seed (or reset) a known local-development superuser.

Occam: the simplest helper that guarantees a working login at startup.

Usage (from project root)::

    .venv/bin/python scripts/seed_admin.py                # default admin / Admin@12345
    .venv/bin/python scripts/seed_admin.py --reset        # force-reset an existing superuser
    .venv/bin/python scripts/seed_admin.py --username dev --password 'Dev@1234' --email dev@local.dev

Rules
-----
* Database URL is read from the same ``app.config.settings`` the FastAPI app
  uses, so this works for both SQLite (local dev) and PostgreSQL (docker).
* If the users table is empty, the script inserts a single superuser and exits.
  The first user is the bootstrap admin; the API itself promotes it.
* If the users table is non-empty, the script -- by default -- *refuses* to
  touch existing accounts.  Pass ``--reset`` to reset the password of the
  first active superuser instead.
* The password is bcrypt-hashed via the project's own ``hash_password``
  helper, so the credentials are guaranteed to validate against
  ``/api/v1/auth/login``.

Why the script looks the way it does
------------------------------------
This file had to dodge two SQLAlchemy async footguns:

1. ``MissingGreenlet``: async sessions raise this when an attribute is
   accessed after the session is closed.  The trigger in v0 was the
   ``user.id`` / ``user.username`` reads that happened *after* ``commit()``
   -- because the default ``expire_on_commit=True`` expires every loaded
   attribute, and the eventual reload needs a sync DBAPI call that the
   event loop cannot satisfy without ``greenlet_spawn``.
   Fix: pass ``expire_on_commit=False`` to every ``async_sessionmaker``
   so attributes stay available after commit, and pre-assign the UUID
   with ``id=uuid4()`` in Python so it is never lazy-loaded.

2. UUID storage mismatch: SQLAlchemy stores ``UUID`` columns in SQLite
   as ``CHAR(32)`` *without* the canonical hyphen separators. Passing
   the hyphenated form (``str(uuid4())``) to a query parameter silently
   matches zero rows.  Fix: normalize IDs to ``hex`` (32 lowercase hex
   chars) in the helpers below; this works for both CHAR(32) on SQLite
   and the native UUID column on PostgreSQL thanks to SQLAlchemy's
   per-dialect type coercion -- but we sidestep the question entirely
   by binding already-normalized strings only.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

# Make the project importable when running this script directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    async_sessionmaker,
    create_async_engine,
)

from app.common.security import hash_password  # noqa: E402
from app.config import settings  # noqa: E402
from app.domain.user.model import User  # noqa: E402


# Local-dev defaults; safe to commit because the project ships with
# ENVIRONMENT=test + a JWT secret tagged "change-in-production".
DEFAULT_USERNAME = "admin"
DEFAULT_EMAIL = "admin@local.dev"
DEFAULT_PASSWORD = "Admin@12345"
DEFAULT_NICKNAME = "Local Admin"


def _session_factory():
    """Build a sessionmaker with ``expire_on_commit=False``.

    Centrally guarantees that no attribute access after ``commit()``
    triggers a sync DBAPI reload (and therefore no ``MissingGreenlet``).
    """
    engine = create_async_engine(settings.DATABASE_URL)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _fetch_users() -> list[tuple[str, str, str, int, int]]:
    """Return ``(id, username, email, is_superuser, status)`` for every user.

    Plain tuples only -- no ORM objects, so no lazy-load surprises across
    async sessions.
    """
    engine, factory = _session_factory()
    try:
        async with factory() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT id, username, email, is_superuser, status "
                        "FROM users ORDER BY created_at ASC"
                    )
                )
            ).all()
        return [(str(r[0]), str(r[1]), str(r[2]), int(r[3]), int(r[4])) for r in rows]
    finally:
        await engine.dispose()


async def _insert_bootstrap(
    *, username: str, email: str, password: str, nickname: str
) -> None:
    """Insert the first superuser.

    The UUID is generated in Python and stored in CHAR(32) form to match
    what the SQLAlchemy ``UUID`` column uses on SQLite. After commit we
    still read the attribute back, but with ``expire_on_commit=False``
    that does not touch the (now-closed) session.
    """
    new_id = uuid4()  # captured as a UUID object; .hex gives the 32-char form
    new_id_str = new_id.hex

    engine, factory = _session_factory()
    try:
        async with factory() as session:
            user = User(
                id=new_id,  # explicit so SQLAlchemy does not need to roundtrip
                username=username,
                email=email,
                hashed_password=hash_password(password),
                nickname=nickname,
                is_superuser=True,
                status=1,
            )
            session.add(user)
            await session.commit()

        print(
            "[seed_admin] INSERTED bootstrap superuser\n"
            f"  id       : {new_id_str}\n"
            f"  username : {username}\n"
            f"  email    : {email}\n"
            f"  password : {password}\n"
            f"  database : {settings.DATABASE_URL}\n"
        )
    finally:
        await engine.dispose()


async def _reset_existing(
    superuser_id: UUID, username_for_log: str, password: str
) -> None:
    """Set the password (and bump token_version) for ``superuser_id``.

    Uses raw SQL and binds ``superuser_id.hex`` -- the 32-char
    no-hyphen form.  This matches SQLite's ``CHAR(32)`` storage and
    SQLAlchemy's UUID-type hex representation for PostgreSQL.
    """
    engine, factory = _session_factory()
    try:
        async with factory() as session:
            result = await session.execute(
                text(
                    "UPDATE users "
                    "SET hashed_password = :hpwd, status = 1, "
                    "    token_version = token_version + 1, "
                    "    updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = :uid"
                ),
                {
                    "hpwd": hash_password(password),
                    "uid": superuser_id.hex,
                },
            )
            await session.commit()
        print(
            "[seed_admin] RESET password on existing superuser\n"
            f"  id       : {superuser_id.hex}\n"
            f"  username : {username_for_log}\n"
            f"  password : {password}\n"
            f"  database : {settings.DATABASE_URL}\n"
            f"  note     : token_version bumped; old JWTs invalidated.\n"
        )
    finally:
        await engine.dispose()


async def seed(
    *,
    username: str,
    email: str,
    password: str,
    nickname: str,
    reset: bool,
) -> int:
    """Insert or reset a local superuser.

    Returns a shell-friendly exit code: 0 = acted, 2 = nothing to do.
    """
    existing = await _fetch_users()

    # --- empty DB: insert the bootstrap superuser --------------------------
    if not existing:
        await _insert_bootstrap(
            username=username, email=email, password=password, nickname=nickname
        )
        return 0

    # --- DB has users already ----------------------------------------------
    superuser = next(
        (r for r in existing if r[3] == 1 and r[4] == 1),
        None,
    )
    if superuser is None:
        print(
            f"[seed_admin] no active superuser found (existing={len(existing)}).\n"
            "             promote one manually, e.g.:\n"
            f"             sqlite3 dev.db \"UPDATE users SET is_superuser=1, status=1 WHERE id='<uuid>';\"\n",
            file=sys.stderr,
        )
        return 2

    sid, sname, semail, _, _ = superuser

    if not reset:
        print(
            f"[seed_admin] database already has {len(existing)} user(s); first superuser is:\n"
            f"  username : {sname}\n"
            f"  email    : {semail}\n"
            "             pass --reset to overwrite the password.\n"
        )
        return 2

    # --- reset path ---------------------------------------------------------
    # ``sid`` is whatever SQLite stored -- a 32-char hex string for CHAR(32)
    # columns. Construct the UUID from hex so its own ``.hex`` round-trips.
    try:
        sid_uuid = UUID(hex=sid)
    except ValueError:
        # Stored value is hyphenated; normalise it.
        sid_uuid = UUID(sid)

    await _reset_existing(sid_uuid, sname, password)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed (or reset) a local superuser for development.",
    )
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--nickname", default=DEFAULT_NICKNAME)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="If users already exist, overwrite the first superuser's password.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return asyncio.run(
        seed(
            username=args.username,
            email=args.email,
            password=args.password,
            nickname=args.nickname,
            reset=args.reset,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
