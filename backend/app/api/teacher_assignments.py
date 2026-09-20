from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.services.teacher_assignment_service import (
    create_teacher_assignment,
)


router = APIRouter(
    prefix="/teacher-assignments",
    tags=["Teacher Assignments"],
)


class AssignmentTargetRequest(BaseModel):
    group_id: int | None = None
    subgroup_id: int | None = None
    lecture_part_id: int | None = None


class CreateTeacherAssignmentRequest(BaseModel):
    teacher_load_id: int

    target_type: str

    targets: list[AssignmentTargetRequest] = Field(
        min_length=1,
    )

    lecture_hours: int = 0
    practice_hours: int = 0
    lab_hours: int = 0


@router.post("/")
def create_assignment(
    request: CreateTeacherAssignmentRequest,
    db: Session = Depends(get_db),
):
    try:
        assignment = create_teacher_assignment(
            db=db,
            teacher_load_id=request.teacher_load_id,
            target_type=request.target_type,
            targets=[
                target.model_dump()
                for target in request.targets
            ],
            lecture_hours=request.lecture_hours,
            practice_hours=request.practice_hours,
            lab_hours=request.lab_hours,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "message": (
            "Назначение преподавателя "
            "успешно создано"
        ),
        "assignment": {
            "id": assignment.id,
            "teacher_load_id": (
                assignment.teacher_load_id
            ),
            "target_type": assignment.target_type,
            "group_id": assignment.group_id,
            "subgroup_id": assignment.subgroup_id,
            "lecture_hours": (
                assignment.lecture_hours
            ),
            "practice_hours": (
                assignment.practice_hours
            ),
            "lab_hours": assignment.lab_hours,
            "targets": [
                {
                    "id": target.id,
                    "target_type": target.target_type,
                    "group_id": target.group_id,
                    "subgroup_id": target.subgroup_id,
                    "lecture_part_id": target.lecture_part_id,
                }
                for target in assignment.targets
            ],
        },
    }