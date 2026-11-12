from fastapi import APIRouter, UploadFile

from app.ai.factory import asr_for, writer_for
from app.ai.parsing import parse_duration_days, parse_number, parse_yes_no
from app.api.deps import AsrDep, ExtractorDep, RulesDep, SessionDep, WorkerDep, WriterDep
from app.api.schemas import (
    AnswerIn,
    AudioCaptureOut,
    CaptureOut,
    ConfirmIn,
    ConsentIn,
    ConsentOut,
    EmergencyIn,
    EncounterCreate,
    EncounterOut,
    EncounterPatch,
    EncounterSummary,
    ExtractOut,
    FactOut,
    FactsPatch,
    NextQuestionOut,
    OutputEdit,
    OutputOut,
    ParseAnswerIn,
    ParseAnswerOut,
    PersonOut,
    PlanOut,
    SpokenAnswerOut,
    SuggestedFactOut,
    TextCapture,
    TranscriptEdit,
    TriageOut,
)
from app.config import get_settings
from app.domain.facts import FactOrigin, FactType
from app.rules.engine import TriageResult
from app.services import audit, speech
from app.services import encounters as svc
from app.services import extraction as xsvc
from app.services import outputs as osvc
from app.services.errors import DomainError
from app.store.models import Encounter, OutputRow

router = APIRouter(prefix="/encounters", tags=["encounters"])


def _audit(
    session: SessionDep,
    worker: WorkerDep,
    enc: Encounter,
    action: str,
    versions: dict[str, object] | None = None,
    **detail: object,
) -> None:
    audit.record(
        session,
        action,
        actor_id=worker.id,
        encounter_id=enc.id,
        person_id=enc.person_id,
        detail=detail,
        versions=versions,
    )


def _out(enc: Encounter) -> EncounterOut:
    t = svc.latest_triage(enc)
    return EncounterOut(
        id=enc.id,
        status=enc.status,
        language=enc.language,
        pathway_id=enc.pathway_id,
        pathway_version=enc.pathway_version,
        created_at=enc.created_at,
        person=PersonOut.model_validate(enc.person),
        facts=[
            FactOut(
                key=f.key, value=f.value, status=f.status, origin=f.origin, evidence=f.source_span
            )
            for f in enc.facts
        ],
        captures=[
            CaptureOut(
                id=c.id,
                kind=c.kind,
                transcript=c.transcript,
                transcript_original=c.transcript_original,
                has_audio=c.audio_path is not None,
                created_at=c.created_at,
            )
            for c in enc.captures
        ],
        triage=TriageOut(
            id=t.id, created_at=t.created_at, result=TriageResult.model_validate(t.result)
        )
        if t
        else None,
        unparsed_concerns=enc.extractions[-1].unparsed_concerns if enc.extractions else [],
        record_audio_consent=next(
            (c.granted for c in reversed(enc.consents) if c.kind == "record_audio"), None
        ),
    )


@router.post("", response_model=EncounterOut, status_code=201)
def create(
    body: EncounterCreate, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> EncounterOut:
    enc = svc.create_encounter(
        session, worker, rules, body.person_id, body.language, body.pathway_id
    )
    _audit(session, worker, enc, "encounter_created", pathway_id=enc.pathway_id)
    session.commit()
    return _out(enc)


@router.get("", response_model=list[EncounterSummary])
def list_(session: SessionDep, worker: WorkerDep) -> list[EncounterSummary]:
    out = []
    for e in svc.list_encounters(session, worker):
        t = svc.latest_triage(e)
        out.append(
            EncounterSummary(
                id=e.id,
                status=e.status,
                created_at=e.created_at,
                person_name=e.person.name,
                pathway_id=e.pathway_id,
                urgency=t.urgency if t else None,
            )
        )
    return out


@router.get("/{encounter_id}", response_model=EncounterOut)
def get(encounter_id: str, session: SessionDep, worker: WorkerDep) -> EncounterOut:
    return _out(svc.get_encounter(session, worker, encounter_id))


@router.patch("/{encounter_id}", response_model=EncounterOut)
def patch(
    encounter_id: str, body: EncounterPatch, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    fields = body.model_dump(exclude_unset=True)
    if "pathway_id" in fields:
        svc.set_pathway(enc, rules, fields["pathway_id"])
    if fields.get("language"):
        enc.language = fields["language"]
    session.commit()
    return _out(enc)


@router.post("/{encounter_id}/capture/text", response_model=EncounterOut)
def capture_text(
    encounter_id: str, body: TextCapture, session: SessionDep, worker: WorkerDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    svc.capture_text(enc, body.text)
    _audit(session, worker, enc, "capture_text", chars=len(body.text))
    session.commit()
    return _out(enc)


@router.get("/{encounter_id}/next-question", response_model=NextQuestionOut)
def next_question(
    encounter_id: str, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> NextQuestionOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    if enc.pathway_id is None:
        return NextQuestionOut(done=False, needs_pathway=True)
    key, question, remaining = svc.next_question(enc, rules)
    if key is None:
        return NextQuestionOut(done=True)
    spec = rules.registry.facts[key]
    if question is not None:
        ask = question.ask.model_dump()
        options = list(question.options)
        input_ = question.input
    else:  # a person-record fact the pathway needs, e.g. age
        ask = spec.label.model_dump()
        options = []
        input_ = None
    if not options and spec.type.value == "tristate":
        options = ["yes", "no", "unknown"]
    if spec.type.value == "enum" and not options:
        options = [*spec.values, "unknown"]
    return NextQuestionOut(
        done=False,
        fact_key=key,
        remaining=remaining,
        ask=ask,
        options=options,
        input=input_ or ("number" if spec.type.value == "number" else spec.type.value),
    )


@router.post("/{encounter_id}/answers", response_model=EncounterOut)
def answer(
    encounter_id: str, body: AnswerIn, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    svc.answer(enc, rules, body.fact_key, body.value, FactOrigin.clarification)
    _audit(
        session,
        worker,
        enc,
        "fact_set",
        keys=[body.fact_key],
        origin="clarification",
        via=body.answered_via,
    )
    session.commit()
    return _out(enc)


@router.patch("/{encounter_id}/facts", response_model=EncounterOut)
def edit_facts(
    encounter_id: str, body: FactsPatch, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    for edit in body.facts:
        svc.answer(enc, rules, edit.key, edit.value, FactOrigin.manual)
    _audit(session, worker, enc, "fact_set", keys=[e.key for e in body.facts], origin="manual")
    session.commit()
    return _out(enc)


@router.post("/{encounter_id}/confirm", response_model=EncounterOut)
def confirm(
    encounter_id: str, body: ConfirmIn, session: SessionDep, worker: WorkerDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    svc.confirm(enc, worker, body.checked_with_family)
    speech.apply_retention_on_confirm(enc, get_settings())
    _audit(session, worker, enc, "facts_confirmed", count=len(enc.facts))
    session.commit()
    return _out(enc)


@router.post("/{encounter_id}/triage", response_model=EncounterOut)
def triage(
    encounter_id: str, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    svc.triage(enc, rules)
    _audit(
        session,
        worker,
        enc,
        "triage",
        {"ruleset_version": rules.version},
        urgency=enc.triage_results[-1].urgency,
        fired=enc.triage_results[-1].result["fired"]
        and [f["id"] for f in enc.triage_results[-1].result["fired"]],
        missing=list(enc.triage_results[-1].result["missing_fact_keys"]),
    )
    session.commit()
    return _out(enc)


@router.post("/{encounter_id}/emergency", response_model=EncounterOut)
def emergency(
    encounter_id: str, body: EmergencyIn, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    svc.emergency(enc, worker, rules, body.danger_sign_ids)
    _audit(
        session,
        worker,
        enc,
        "emergency",
        {"ruleset_version": rules.version},
        signs=body.danger_sign_ids,
    )
    session.commit()
    return _out(enc)


@router.post("/{encounter_id}/extract", response_model=ExtractOut)
async def extract(
    encounter_id: str,
    session: SessionDep,
    worker: WorkerDep,
    rules: RulesDep,
    extractor: ExtractorDep,
) -> ExtractOut:
    """Suggest facts from the latest typed or transcribed account. AI failure is not an error:
    it returns 200 with ``degraded: true`` and the visit continues by hand."""
    enc = svc.get_encounter(session, worker, encounter_id)
    result = await xsvc.run_extraction(enc, rules, get_settings(), extractor)
    _audit(
        session,
        worker,
        enc,
        "extraction",
        {
            "provider": result.provider,
            "model_rev": result.model_rev,
            "prompt_version": result.prompt_version,
        },
        suggested=[f.key for f in result.facts],
        discarded=result.discarded,
        degraded=result.degraded,
        reason=result.reason,
    )
    session.commit()
    return ExtractOut(
        encounter=_out(enc),
        degraded=result.degraded,
        reason=result.reason,
        suggested=[
            SuggestedFactOut(
                key=f.key, value=f.value, evidence=f.evidence, approximate=f.approximate
            )
            for f in result.facts
        ],
        discarded=result.discarded,
        suggested_pathways=result.suggested_pathways,
        unparsed_concerns=result.unparsed_concerns,
    )


@router.post("/{encounter_id}/facts/{fact_key}/reject", response_model=EncounterOut)
def reject(
    encounter_id: str, fact_key: str, session: SessionDep, worker: WorkerDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    xsvc.reject_fact(enc, fact_key)
    _audit(session, worker, enc, "fact_rejected", keys=[fact_key])
    session.commit()
    return _out(enc)


@router.post("/{encounter_id}/parse-answer", response_model=ParseAnswerOut)
def parse_answer(
    encounter_id: str, body: ParseAnswerIn, session: SessionDep, worker: WorkerDep, rules: RulesDep
) -> ParseAnswerOut:
    """Parse a spoken or typed free answer into the fact's type, deterministically. Nothing is
    stored: the worker sees the parsed value and confirms it by submitting it as an answer."""
    svc.get_encounter(session, worker, encounter_id)
    spec = rules.registry.facts.get(body.fact_key)
    if spec is None:
        raise DomainError("unknown_fact", body.fact_key)
    if spec.type is FactType.tristate:
        v = parse_yes_no(body.text)
        return ParseAnswerOut(understood=v is not None, value=v)
    if spec.type is FactType.number:
        if spec.unit == "days":
            d = parse_duration_days(body.text)
            if d is None:
                n = parse_number(body.text)
                return ParseAnswerOut(understood=n is not None, value=n)
            return ParseAnswerOut(understood=True, value=d.value, approximate=d.approximate)
        n = parse_number(body.text)
        return ParseAnswerOut(understood=n is not None, value=n)
    text = body.text.strip().lower()
    match = [
        v
        for v in spec.values
        if v == text or text in (spec.value_labels[v].en.lower(), spec.value_labels[v].hi)
    ]
    return ParseAnswerOut(understood=len(match) == 1, value=match[0] if len(match) == 1 else None)


@router.post("/{encounter_id}/consents", response_model=ConsentOut, status_code=201)
def consent(
    encounter_id: str, body: ConsentIn, session: SessionDep, worker: WorkerDep
) -> ConsentOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    c = speech.record_consent(session, enc, worker, body.kind, body.granted)
    _audit(session, worker, enc, "consent", kind=body.kind, granted=body.granted)
    session.commit()
    return ConsentOut(kind=c.kind, granted=c.granted)


@router.post("/{encounter_id}/capture/audio", response_model=AudioCaptureOut)
async def capture_audio(
    encounter_id: str, audio: UploadFile, session: SessionDep, worker: WorkerDep, asr: AsrDep
) -> AudioCaptureOut:
    """Upload a recording; returns the transcript as a capture. ASR failure returns 200 with
    ``degraded: true`` and nothing stored: the worker types instead."""
    enc = svc.get_encounter(session, worker, encounter_id)
    settings = get_settings()
    data = await audio.read(settings.max_audio_bytes + 1)
    _, reason = await speech.capture_audio(session, enc, settings, asr or asr_for(settings), data)
    _audit(
        session,
        worker,
        enc,
        "capture_audio",
        {"asr": enc.captures[-1].asr_model_rev if enc.captures and reason is None else None},
        degraded=reason is not None,
        reason=reason,
    )
    session.commit()
    return AudioCaptureOut(encounter=_out(enc), degraded=reason is not None, reason=reason)


@router.post("/{encounter_id}/spoken-answer", response_model=SpokenAnswerOut)
async def spoken_answer(
    encounter_id: str, audio: UploadFile, session: SessionDep, worker: WorkerDep, asr: AsrDep
) -> SpokenAnswerOut:
    """Transcribe a spoken answer. Nothing is stored; the text goes to parse-answer."""
    enc = svc.get_encounter(session, worker, encounter_id)
    settings = get_settings()
    data = await audio.read(settings.max_audio_bytes + 1)
    text = await speech.transcribe_answer(session, enc, settings, asr or asr_for(settings), data)
    return SpokenAnswerOut(understood=bool(text), text=text)


@router.patch("/{encounter_id}/captures/{capture_id}", response_model=EncounterOut)
def edit_transcript(
    encounter_id: str, capture_id: str, body: TranscriptEdit, session: SessionDep, worker: WorkerDep
) -> EncounterOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    speech.edit_transcript(enc, capture_id, body.transcript)
    _audit(session, worker, enc, "transcript_edited", capture_id=capture_id)
    session.commit()
    return _out(enc)


def _output(o: OutputRow) -> OutputOut:
    return OutputOut(
        id=o.id, kind=o.kind, language=o.language, body=o.body, generated_by=o.generated_by,
        edited_by_worker=o.edited_by_worker, check_failures=list(o.check_failures),
    )  # fmt: skip


@router.get("/{encounter_id}/plan", response_model=PlanOut)
def plan(encounter_id: str, session: SessionDep, worker: WorkerDep, rules: RulesDep) -> PlanOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    p = osvc.plan(enc, rules, get_settings(), worker)
    _audit(
        session, worker, enc, "plan", facility_level=p.facility_level, target_window=p.target_window
    )
    session.commit()
    result = TriageResult.model_validate(svc.latest_triage(enc).result)  # type: ignore[union-attr]
    return PlanOut(
        urgency=result.urgency.value,
        facility_level=p.facility_level,
        facility_names=list(p.facility_names),
        target_window=p.target_window,
        bring_list=list(p.bring_list),
        return_precautions=result.return_precautions.model_dump()
        if result.return_precautions
        else None,
        review_status=result.review_status.value,
    )


@router.post("/{encounter_id}/outputs", response_model=list[OutputOut])
async def generate_outputs(
    encounter_id: str, session: SessionDep, worker: WorkerDep, rules: RulesDep, writer: WriterDep
) -> list[OutputOut]:
    """Clinician handoff (English) and family instructions (visit language). Templates always
    work; an optional LLM rewrite is used only if it passes the output checks."""
    enc = svc.get_encounter(session, worker, encounter_id)
    w = writer or writer_for(get_settings(), synthetic=enc.synthetic)
    rows = await osvc.generate(enc, rules, worker, w)
    _audit(
        session,
        worker,
        enc,
        "outputs_generated",
        {"writer": rows[0].writer if rows else None},
        kinds=[o.kind for o in rows],
        generated_by=[o.generated_by for o in rows],
        check_failures=[f for o in rows for f in o.check_failures],
    )
    session.commit()
    return [_output(o) for o in rows]


@router.get("/{encounter_id}/outputs", response_model=list[OutputOut])
def list_outputs(encounter_id: str, session: SessionDep, worker: WorkerDep) -> list[OutputOut]:
    enc = svc.get_encounter(session, worker, encounter_id)
    return [_output(o) for o in osvc.current_outputs(enc)]


@router.patch("/{encounter_id}/outputs/{output_id}", response_model=OutputOut)
def edit_output(
    encounter_id: str, output_id: str, body: OutputEdit, session: SessionDep, worker: WorkerDep
) -> OutputOut:
    enc = svc.get_encounter(session, worker, encounter_id)
    o = osvc.edit(enc, output_id, body.body)
    _audit(session, worker, enc, "output_edited", kind=o.kind)
    session.commit()
    return _output(o)
