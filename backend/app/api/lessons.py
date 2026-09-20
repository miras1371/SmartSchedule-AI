from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.lesson import Lesson
from backend.app.models.teacher_assignment import TeacherAssignment
from backend.app.services.lesson_service import (
    create_lessons_for_assignment,
    create_lessons_from_assignments,
)


router = APIRouter(
    prefix="/teacher-assignments",
    tags=["Lessons"],
)


class CommonLessonCreate(BaseModel):
    assignment_ids: list[int] = Field(
        min_length=2,
    )


@router.post("/{assignment_id}/lessons")
def generate_lessons(
    assignment_id: int,
    db: Session = Depends(get_db),
):
    assignment = (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.id == assignment_id
        )
        .first()
    )

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Назначение преподавателя не найдено",
        )

    try:
        lessons = create_lessons_for_assignment(
            db=db,
            assignment=assignment,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "message": "Занятия успешно созданы",
        "assignment_id": assignment.id,
        "lessons_count": len(lessons),
        "lessons": [
            {
                "id": lesson.id,
                "lesson_type": lesson.lesson_type,
                "hours": lesson.hours,
                "lesson_number": lesson.lesson_number,
            }
            for lesson in lessons
        ],
    }


@router.post("/lessons/common")
def generate_common_lessons(
    data: CommonLessonCreate,
    db: Session = Depends(get_db),
):
    assignments = (
        db.query(TeacherAssignment)
        .filter(
            TeacherAssignment.id.in_(
                data.assignment_ids
            )
        )
        .all()
    )

    found_ids = {
        assignment.id
        for assignment in assignments
    }

    missing_ids = [
        assignment_id
        for assignment_id in data.assignment_ids
        if assignment_id not in found_ids
    ]

    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                "Следующие назначения преподавателей "
                f"не найдены: {missing_ids}"
            ),
        )

    assignments_by_id = {
        assignment.id: assignment
        for assignment in assignments
    }

    ordered_assignments = [
        assignments_by_id[assignment_id]
        for assignment_id in data.assignment_ids
    ]

    try:
        lessons = create_lessons_from_assignments(
            db=db,
            assignments=ordered_assignments,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return {
        "message": "Общие занятия успешно созданы",
        "assignment_ids": data.assignment_ids,
        "lessons_count": len(lessons),
        "lessons": [
            {
                "id": lesson.id,
                "lesson_type": lesson.lesson_type,
                "hours": lesson.hours,
                "lesson_number": lesson.lesson_number,
                "targets": [
                    {
                        "id": target.id,
                        "teacher_assignment_id": (
                            target.teacher_assignment_id
                        ),
                        "target_type": target.target_type,
                        "group_id": target.group_id,
                        "subgroup_id": target.subgroup_id,
                        "lecture_part_id": target.lecture_part_id,
                        "subgroup_bundle_id": (
                            target.subgroup_bundle_id
                        ),
                    }
                    for target in lesson.targets
                ],
            }
            for lesson in lessons
        ],
    }