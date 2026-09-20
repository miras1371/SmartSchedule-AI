from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.academic_period import AcademicPeriod
from backend.app.models.lecture_stream import LectureStream
from backend.app.models.subgroup_set import SubgroupSet
from backend.app.services.subgroup_service import (
    create_subgroups_for_stream,
)


router = APIRouter(
    prefix="/lecture-streams",
    tags=["Subgroups"],
)


@router.post("/{lecture_stream_id}/subgroups")
def create_stream_subgroups(
    lecture_stream_id: int,
    academic_period_id: int,
    db: Session = Depends(get_db),
):
    academic_period = (
        db.query(AcademicPeriod)
        .filter(AcademicPeriod.id == academic_period_id)
        .first()
    )

    if academic_period is None:
        raise HTTPException(
            status_code=404,
            detail="Академический период не найден.",
        )

    lecture_stream = (
        db.query(LectureStream)
        .filter(
            LectureStream.id == lecture_stream_id,
            LectureStream.is_active.is_(True),
        )
        .first()
    )

    if lecture_stream is None:
        raise HTTPException(
            status_code=404,
            detail="Лекционный поток не найден.",
        )

    active_set = (
        db.query(SubgroupSet)
        .filter(
            SubgroupSet.lecture_stream_id == lecture_stream.id,
            SubgroupSet.academic_period_id == academic_period_id,
            SubgroupSet.status == "active",
        )
        .first()
    )

    if active_set is not None:
        raise HTTPException(
            status_code=400,
            detail="Для этого лекционного потока уже существует активный набор подгрупп.",
        )

    try:
        subgroups = create_subgroups_for_stream(
            db=db,
            lecture_stream=lecture_stream,
            academic_period_id=academic_period_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    subgroup_set = (
        db.query(SubgroupSet)
        .filter(
            SubgroupSet.id == subgroups[0].subgroup_set_id,
        )
        .first()
    )

    return {
        "message": "Подгруппы успешно созданы.",
        "lecture_stream_id": lecture_stream.id,
        "lecture_stream_name": lecture_stream.name,
        "academic_period_id": academic_period.id,
        "academic_period_name": academic_period.name,
        "subgroup_set_id": subgroup_set.id,
        "version": subgroup_set.version,
        "subgroups": [
            {
                "id": subgroup.id,
                "name": subgroup.name,
                "group_id": subgroup.group_id,
                "subgroup_number": subgroup.subgroup_number,
                "student_count": subgroup.student_count,
            }
            for subgroup in subgroups
        ],
    }