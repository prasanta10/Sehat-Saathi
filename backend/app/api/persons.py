from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionDep, WorkerDep
from app.api.schemas import PersonIn, PersonOut, PersonPatch
from app.services import audit
from app.services.errors import NotFound
from app.store.models import Person

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonOut])
def list_persons(session: SessionDep, worker: WorkerDep) -> list[Person]:
    return list(
        session.scalars(select(Person).where(Person.worker_id == worker.id).order_by(Person.name))
    )


@router.post("", response_model=PersonOut, status_code=201)
def create_person(body: PersonIn, session: SessionDep, worker: WorkerDep) -> Person:
    person = Person(worker_id=worker.id, state=worker.state, **body.model_dump())
    session.add(person)
    session.flush()
    audit.record(session, "person_created", actor_id=worker.id, person_id=person.id)
    session.commit()
    return person


def _get(session: SessionDep, worker: WorkerDep, person_id: str) -> Person:
    person = session.get(Person, person_id)
    if person is None or person.worker_id != worker.id:
        raise NotFound("person_not_found")
    return person


@router.get("/{person_id}", response_model=PersonOut)
def get_person(person_id: str, session: SessionDep, worker: WorkerDep) -> Person:
    return _get(session, worker, person_id)


@router.patch("/{person_id}", response_model=PersonOut)
def patch_person(
    person_id: str, body: PersonPatch, session: SessionDep, worker: WorkerDep
) -> Person:
    person = _get(session, worker, person_id)
    fields = body.model_dump(exclude_unset=True)
    for k, v in fields.items():
        setattr(person, k, v)
    audit.record(
        session,
        "person_updated",
        actor_id=worker.id,
        person_id=person.id,
        detail={"fields": sorted(fields)},
    )
    session.commit()
    return person
