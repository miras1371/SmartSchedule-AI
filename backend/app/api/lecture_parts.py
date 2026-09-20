from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.lecture_part import LecturePart
from backend.app.models.lecture_stream import LectureStream


router = APIRouter(
    prefix="/lecture-streams",
    tags=["Lecture Parts"],
)


@router.get("/{lecture_stream_id}/lecture-parts")
def list_lecture_parts(
    lecture_stream_id: int,
    version: int | None = None,
    db: Session = Depends(get_db),
):
    stream = (
        db.query(LectureStream)
        .filter(
            LectureStream.id == lecture_stream_id,
            LectureStream.is_active.is_(True),
        )
        .first()
    )

    if stream is None:
        raise HTTPException(
            status_code=404,
            detail="Лекционный поток не найден.",
        )

    query = db.query(LecturePart).filter(
        LecturePart.lecture_stream_id == stream.id,
    )

    if version is not None:
        query = query.filter(LecturePart.version == version)

    parts = query.order_by(
        LecturePart.version.desc(),
        LecturePart.part_number.asc(),
    ).all()

    return {
        "lecture_stream_id": stream.id,
        "lecture_stream_name": stream.name,
        "parts": [
            {
                "id": part.id,
                "name": part.name,
                "version": part.version,
                "part_number": part.part_number,
                "student_count": part.student_count,
            }
            for part in parts
        ],
    }
