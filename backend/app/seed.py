"""Load synthetic demo data: demo accounts and a few invented people.

Every name here is made up, and the demo PINs are for local development only: never use them on
a shared or pilot server. Never add real people.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.auth import hash_pin
from app.store.db import get_session
from app.store.models import Person, Worker

DEMO_WORKERS = [
    {
        "name": "Demo ASHA (synthetic)",
        "phone": "9000000001",
        "pin": "1234",
        "role": "worker",
        "state": "UP",
        "district": "Sitapur",
    },
    {
        "name": "Second ASHA (synthetic)",
        "phone": "9000000002",
        "pin": "1234",
        "role": "worker",
        "state": "UP",
        "district": "Sitapur",
    },
    {
        "name": "Demo admin (synthetic)",
        "phone": "9000000009",
        "pin": "4321",
        "role": "admin",
        "state": "UP",
        "district": "Sitapur",
    },
]
SYNTHETIC_PEOPLE = [
    {
        "name": "Kamla Devi (synthetic)",
        "age_years": 62,
        "sex": "female",
        "village": "Rampur (synthetic)",
    },
    {
        "name": "Ramesh Kumar (synthetic)",
        "age_years": 38,
        "sex": "male",
        "village": "Rampur (synthetic)",
    },
    {
        "name": "Sunita (synthetic)",
        "age_years": 24,
        "sex": "female",
        "village": "Sitapur (synthetic)",
        "pregnant": "yes",
    },
    {
        "name": "Baby of Sunita (synthetic)",
        "age_years": 0,
        "age_months": 0,
        "sex": "female",
        "village": "Sitapur (synthetic)",
    },
]


@lru_cache
def _demo_pin_hash(pin: str) -> str:
    # Demo accounts only: one Argon2 hash per PIN per process keeps tests fast. Real accounts
    # are created with their own salted hash.
    return hash_pin(pin)


def ensure_worker(session: Session, spec: dict[str, str]) -> Worker:
    w = session.scalar(select(Worker).where(Worker.phone == spec["phone"]))
    if w is None:
        w = Worker(
            name=spec["name"],
            phone=spec["phone"],
            role=spec["role"],
            state=spec["state"],
            district=spec["district"],
        )
        w.pin_hash = _demo_pin_hash(spec["pin"])
        session.add(w)
        session.flush()
    return w


def seed(session: Session) -> int:
    workers = [ensure_worker(session, w) for w in DEMO_WORKERS]
    added = 0
    for p in SYNTHETIC_PEOPLE:
        if (
            session.scalar(
                select(Person).where(Person.worker_id == workers[0].id, Person.name == p["name"])
            )
            is None
        ):
            session.add(Person(worker_id=workers[0].id, state="UP", synthetic=True, **p))
            added += 1
    session.commit()
    return added


if __name__ == "__main__":
    s = next(get_session())
    print(f"seeded demo accounts and {seed(s)} synthetic people (local development only)")
