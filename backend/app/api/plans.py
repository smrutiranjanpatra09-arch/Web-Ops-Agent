from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.plan import Plan

router = APIRouter(prefix="/api/plans", tags=["plans"])


def _to_response(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "task_id": plan.task_id,
        "objective": plan.objective,
        "status": plan.status,
        "risk_notes": plan.risk_notes,
        "stop_conditions": plan.stop_conditions.split("; ") if plan.stop_conditions else [],
        "rejection_reason": plan.rejection_reason,
        "steps": [
            {"step_order": s.step_order, "action": s.action, "target": s.target, "notes": s.notes}
            for s in sorted(plan.steps, key=lambda s: s.step_order)
        ],
    }


@router.get("/{plan_id}")
def get_plan(plan_id: str, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, f"Plan '{plan_id}' not found.")
    return _to_response(plan)
