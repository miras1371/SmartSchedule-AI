from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.lesson_target import LessonTarget
from backend.app.models.subgroup_bundle import SubgroupBundle


router = APIRouter(
    prefix="/subgroup-bundles",
    tags=["Subgroup Bundles"],
)


@router.get("/")
def get_subgroup_bundles(
    db: Session = Depends(get_db),
):
    bundles = (
        db.query(SubgroupBundle)
        .order_by(SubgroupBundle.id)
        .all()
    )

    result = []
    for bundle in bundles:
        target = (
            db.query(LessonTarget)
            .filter(
                LessonTarget.subgroup_bundle_id == bundle.id,
            )
            .first()
        )

        result.append(
            {
                "id": bundle.id,
                "lesson_id": bundle.lesson_id,
                "lesson_type": (
                    bundle.lesson.lesson_type
                    if bundle.lesson is not None
                    else None
                ),
                "student_count": bundle.student_count,
                "target_id": target.id if target is not None else None,
                "teacher_assignment_id": (
                    target.teacher_assignment_id
                    if target is not None
                    else None
                ),
                "members": [
                    {
                        "subgroup_id": member.subgroup_id,
                        "name": member.subgroup.name,
                        "student_count": member.subgroup.student_count,
                    }
                    for member in bundle.members
                ],
            }
        )

    return {
        "count": len(result),
        "subgroup_bundles": result,
    }
