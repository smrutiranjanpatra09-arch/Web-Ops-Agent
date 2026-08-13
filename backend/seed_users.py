"""Seed one demo user per role. Run once after migrations:

    docker compose exec api python -m backend.seed_users
"""
from backend.app.auth.security import hash_password
from backend.app.database.session import SessionLocal
from backend.app.models.user import Role, User

DEMO_USERS = (
    ("ops@makemytrip.demo", "Operations User", "role-operations_user"),
    ("growth@makemytrip.demo", "Growth User", "role-growth_user"),
    ("reviewer@makemytrip.demo", "Reviewer", "role-reviewer"),
    ("owner@makemytrip.demo", "Operations Owner", "role-operations_owner"),
    ("admin@makemytrip.demo", "Administrator", "role-administrator"),
)
DEMO_PASSWORD = "#demoday26"


def main() -> None:
    db = SessionLocal()
    try:
        for email, display_name, role_id in DEMO_USERS:
            if db.query(User).filter(User.email == email).one_or_none():
                continue
            if db.get(Role, role_id) is None:
                print(f"skip {email}: role {role_id} not found (run migrations first)")
                continue
            db.add(User(email=email, display_name=display_name, role_id=role_id, password_hash=hash_password(DEMO_PASSWORD)))
            print(f"seeded {email} ({role_id})")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
