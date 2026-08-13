from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.task import TaskTemplate
from backend.app.schemas.schedule import TaskTemplateCreateRequest, TaskTemplateResponse

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _to_response(t: TaskTemplate) -> TaskTemplateResponse:
    return TaskTemplateResponse(
        id=t.id, name=t.name, workflow_type=t.workflow_type, description=t.description,
        path_template=t.path_template, objective_template=t.objective_template,
        wait_selector=t.wait_selector, default_frequency=t.default_frequency,
        owner_team=t.owner_team, requires_approval=t.requires_approval,
    )


@router.post("", response_model=TaskTemplateResponse)
def create_template(req: TaskTemplateCreateRequest, db: Session = Depends(get_db)):
    template = TaskTemplate(
        name=req.name, workflow_type=req.workflow_type, description=req.description,
        path_template=req.path_template, objective_template=req.objective_template,
        wait_selector=req.wait_selector, expected_fields=",".join(req.expected_fields),
        default_frequency=req.default_frequency, owner_team=req.owner_team,
        requires_approval=req.requires_approval, stop_conditions=",".join(req.stop_conditions),
    )
    db.add(template)
    db.commit()
    return _to_response(template)


@router.get("", response_model=list[TaskTemplateResponse])
def list_templates(db: Session = Depends(get_db)):
    return [_to_response(t) for t in db.query(TaskTemplate).order_by(TaskTemplate.name).all()]


@router.get("/{template_id}", response_model=TaskTemplateResponse)
def get_template(template_id: str, db: Session = Depends(get_db)):
    template = db.get(TaskTemplate, template_id)
    if template is None:
        raise HTTPException(404, f"Template '{template_id}' not found.")
    return _to_response(template)
