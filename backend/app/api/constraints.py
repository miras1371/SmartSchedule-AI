from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.classroom import Classroom
from backend.app.models.scheduling_constraint import SchedulingConstraint
from backend.app.models.teacher import Teacher


router = APIRouter(prefix="/constraints", tags=["Constraints"])


class ConstraintCreate(BaseModel):
    constraint_type: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1)
    teacher_id: int | None = None
    classroom_id: int | None = None
    day_of_week: int | None = Field(default=None, ge=1, le=6)
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")


def _response(item: SchedulingConstraint) -> dict:
    return {column.name: getattr(item, column.name) for column in SchedulingConstraint.__table__.columns}


@router.get("")
def list_constraints(db: Session = Depends(get_db)):
    items = db.query(SchedulingConstraint).order_by(SchedulingConstraint.created_at.desc()).all()
    return {"constraints": [_response(item) for item in items]}


@router.post("", status_code=201)
def create_constraint(data: ConstraintCreate, db: Session = Depends(get_db)):
    if data.teacher_id and db.get(Teacher, data.teacher_id) is None:
        raise HTTPException(status_code=404, detail="Преподаватель не найден.")
    if data.classroom_id and db.get(Classroom, data.classroom_id) is None:
        raise HTTPException(status_code=404, detail="Аудитория не найдена.")
    if data.start_time and data.end_time and data.start_time >= data.end_time:
        raise HTTPException(status_code=400, detail="Время окончания должно быть позже времени начала.")
    item = SchedulingConstraint(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"constraint": _response(item)}
