from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.classroom import Classroom
from backend.app.models.lesson_target import LessonTarget


router = APIRouter(
    prefix="/lesson-targets",
    tags=["Lesson Targets"],
)


class ClassroomAssignment(BaseModel):
    classroom_id: int = Field(gt=0)


@router.put("/{target_id}/classroom")
def assign_classroom(
    target_id: int,
    data: ClassroomAssignment,
    db: Session = Depends(get_db),
):
    target = (
        db.query(LessonTarget)
        .filter(LessonTarget.id == target_id)
        .first()
    )

    if target is None:
        raise HTTPException(
            status_code=404,
            detail="Цель занятия не найдена.",
        )

    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == data.classroom_id,
            Classroom.is_active.is_(True),
        )
        .first()
    )

    if classroom is None:
        raise HTTPException(
            status_code=404,
            detail="Активная аудитория не найдена.",
        )

    if target.target_type == "full_group":
        if target.group is None:
            raise HTTPException(
                status_code=400,
                detail="Для цели не найдена группа.",
            )

        student_count = target.group.student_count

    elif target.target_type == "subgroup":
        if target.subgroup is None:
            raise HTTPException(
                status_code=400,
                detail="Для цели не найдена подгруппа.",
            )

        student_count = target.subgroup.student_count

    elif target.target_type == "lecture_part":
        if target.lecture_part is None:
            raise HTTPException(
                status_code=400,
                detail="Для цели не найдена лекционная часть.",
            )

        student_count = target.lecture_part.student_count

    elif target.target_type == "subgroup_bundle":
        if target.subgroup_bundle is None:
            raise HTTPException(
                status_code=400,
                detail="Для цели не найдено объединение подгрупп.",
            )

        student_count = target.subgroup_bundle.student_count

    else:
        raise HTTPException(
            status_code=400,
            detail="Неизвестный тип цели занятия.",
        )

    if classroom.capacity < student_count:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Аудитория {classroom.name} рассчитана "
                f"на {classroom.capacity} студентов, "
                f"но для цели требуется {student_count}."
            ),
        )

    lesson = target.lesson

    if lesson is None:
        raise HTTPException(
            status_code=400,
            detail="Для цели не найдено занятие.",
        )

    if lesson.lesson_type == "lab":
        if classroom.room_type != "computer_lab":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Для лабораторного занятия требуется "
                    "аудитория типа computer_lab."
                ),
            )

    existing_target = (
        db.query(LessonTarget)
        .filter(
            LessonTarget.classroom_id == classroom.id,
            LessonTarget.lesson_id == lesson.id,
            LessonTarget.id != target.id,
        )
        .first()
    )

    if existing_target is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Аудитория {classroom.name} уже занята "
                "другой целью этого занятия."
            ),
        )

    target.classroom_id = classroom.id

    db.commit()
    db.refresh(target)

    return {
        "message": "Аудитория успешно назначена.",
        "lesson_target_id": target.id,
        "lesson_id": target.lesson_id,
        "teacher_assignment_id": target.teacher_assignment_id,
        "target_type": target.target_type,
        "group_id": target.group_id,
        "subgroup_id": target.subgroup_id,
        "lecture_part_id": target.lecture_part_id,
        "subgroup_bundle_id": target.subgroup_bundle_id,
        "classroom": {
            "id": classroom.id,
            "name": classroom.name,
            "capacity": classroom.capacity,
            "room_type": classroom.room_type,
            "equipment": classroom.equipment,
        },
    }