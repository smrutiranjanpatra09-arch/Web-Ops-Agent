# Phase 30.3: one Gemini call that turns a run's already-computed changes +
# signals into an executive summary + bullet list, for the Completion journey
# stage and the future Phase 35 PDF report. Computed on demand (idempotent,
# cheap) - nothing new is persisted here.
from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.models.snapshot import Change
from backend.app.models.signal import Signal

DIGEST_SYSTEM_PROMPT = """You are the run-digest module of a governed web operations \
agent for MakeMyTrip. You are given a structured, already-computed list of changes and \
signals detected during one monitoring run. Do not invent facts and do not compute any \
numbers yourself - only summarize what is given. Return ONLY JSON matching this shape:

{
  "executive_summary": "one paragraph, 2-4 sentences, what happened in this run and why it matters",
  "bullets": ["what changed / why it matters / what to do", "..."]
}"""


class RunDigest(BaseModel):
    generated_by: str = "deterministic"
    run_id: str
    executive_summary: str
    bullets: list[str]


def _deterministic_digest(run_id: str, changes: list[Change], signals: list[Signal]) -> RunDigest:
    relevant = [c for c in changes if c.business_relevant]
    if not relevant:
        return RunDigest(
            run_id=run_id,
            executive_summary=f"No business-relevant changes were detected during run {run_id}.",
            bullets=[],
        )

    bullets = [
        f"{c.entity_name}: {c.change_type.replace('_', ' ')} "
        f"({c.previous_value} -> {c.current_value})."
        for c in relevant
    ]
    review_flags = sum(1 for s in signals if s.requires_human_review)
    summary = (
        f"{len(relevant)} business-relevant change(s) detected across this run"
        f"{', ' + str(review_flags) + ' flagged for human review' if review_flags else ''}."
    )
    return RunDigest(run_id=run_id, executive_summary=summary, bullets=bullets)


def generate_run_digest(db: Session, run_id: str) -> RunDigest:
    changes = db.query(Change).filter(Change.run_id == run_id).all()
    signals = db.query(Signal).filter(Signal.run_id == run_id).all()

    fallback = _deterministic_digest(run_id, changes, signals)

    try:
        from agents.llm import active_provider, call_structured

        provider = active_provider()
        changes_text = "\n".join(
            f"- {c.entity_name}: {c.change_type} (prev={c.previous_value}, current={c.current_value}, "
            f"delta_pct={c.delta_pct}, significance={c.significance})"
            for c in changes if c.business_relevant
        )
        signals_text = "\n".join(
            f"- {s.signal_type} (severity={s.severity}, owner={s.owner}, "
            f"requires_human_review={s.requires_human_review})"
            for s in signals
        )
        if not changes_text and not signals_text:
            return fallback

        user_prompt = (
            f"Run: {run_id}\n"
            f"Changes:\n{changes_text or '(none)'}\n"
            f"Signals:\n{signals_text or '(none)'}"
        )
        raw = call_structured(
            DIGEST_SYSTEM_PROMPT, user_prompt,
            node="digest", purpose=f"Digest run {run_id}", run_id=run_id,
            input_ref_ids={"change_ids": [c.id for c in changes], "signal_ids": [s.id for s in signals]},
        )
        return RunDigest(generated_by=provider or "deterministic", run_id=run_id, **raw)
    except Exception:
        return fallback
