from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


USERS = [
    {
        "name": "Manager Test",
        "email": "manager@local",
        "password": "Manager123!",
        "role": "MANAGER",
    },
    {
        "name": "Advisor Test",
        "email": "advisor@local",
        "password": "Advisor123!",
        "role": "ADVISOR",
    },
    {
        "name": "Reviewer Test",
        "email": "reviewer@local",
        "password": "Reviewer123!",
        "role": "REVIEWER",
    },
    {
        "name": "Auditor Test",
        "email": "auditor@local",
        "password": "Auditor123!",
        "role": "AUDITOR",
    },
]


def main():
    with SessionLocal() as db:
        for item in USERS:
            existing = db.scalar(
                select(User).where(
                    User.email == item["email"]
                )
            )

            if existing:
                print(
                    f"{item['email']} already exists"
                )
                continue

            user = User(
                name=item["name"],
                email=item["email"],
                password_hash=hash_password(
                    item["password"]
                ),
                role=item["role"],
                active=True,
            )

            db.add(user)

            print(
                f"Created {item['email']} "
                f"({item['role']})"
            )

        db.commit()


if __name__ == "__main__":
    main()