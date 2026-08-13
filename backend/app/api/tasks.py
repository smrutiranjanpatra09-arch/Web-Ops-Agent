from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.task import Task
from backend.app.schemas.task import TaskCreateRequest, TaskResponse
from backend.app.services.run_service import create_task

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

VALID_WORKFLOWS = {
    "hotel_pricing_watch", "competitor_offer_tracking", "campaign_page_monitoring",
    "partner_update_review", "travel_trend_scanning",
}


@router.post("", response_model=TaskResponse)
def create_task_endpoint(req: TaskCreateRequest, db: Session = Depends(get_db)):
    if req.workflow_type not in VALID_WORKFLOWS:
        raise HTTPException(400, f"Unknown workflow_type '{req.workflow_type}'. Choose from: {sorted(VALID_WORKFLOWS)}")
    task = create_task(
        db, objective=req.objective, workflow_type=req.workflow_type, entity_key=req.entity_key,
        target_url=req.target_url, source_id=req.source_id, template_id=req.template_id, owner=req.owner,
        risk_level=req.risk_level, review_required=req.review_required, completion_criteria=req.completion_criteria,
    )
    return TaskResponse(
        id=task.id, objective=task.objective, workflow_type=task.workflow_type,
        entity_key=task.entity_key, owner=task.owner, risk_level=task.risk_level,
        review_required=task.review_required, created_at=task.created_at.isoformat(),
    )


@router.get("", response_model=list[TaskResponse])
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    return [
        TaskResponse(
            id=t.id, objective=t.objective, workflow_type=t.workflow_type, entity_key=t.entity_key,
            owner=t.owner, risk_level=t.risk_level, review_required=t.review_required,
            created_at=t.created_at.isoformat(),
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(404, f"Task '{task_id}' not found.")
    return TaskResponse(
        id=task.id, objective=task.objective, workflow_type=task.workflow_type, entity_key=task.entity_key,
        owner=task.owner, risk_level=task.risk_level, review_required=task.review_required,
        created_at=task.created_at.isoformat(),
    )
