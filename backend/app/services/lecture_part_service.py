from sqlalchemy.orm import Session

from backend.app.models.lecture_part import LecturePart
from backend.app.models.lecture_part_student import LecturePartStudent
from backend.app.models.lecture_stream import LectureStream
from backend.app.models.lecture_stream_student import LectureStreamStudent
from backend.app.models.student import Student


MAX_LECTURE_PART_SIZE = 70


def calculate_lecture_part_sizes(
    student_count: int,
    max_part_size: int = MAX_LECTURE_PART_SIZE,
) -> list[int]:
    if student_count <= 0:
        raise ValueError(
            "Количество студентов потока должно быть больше нуля."
        )

    if max_part_size <= 0:
        raise ValueError(
            "Максимальный размер лекционной части должен быть больше нуля."
        )

    part_count = (
        student_count + max_part_size - 1
    ) // max_part_size
    base_size = student_count // part_count
    remainder = student_count % part_count

    return [
        base_size + (1 if index < remainder else 0)
        for index in range(part_count)
    ]


def create_lecture_parts_for_stream(
    db: Session,
    lecture_stream: LectureStream,
    version: int = 1,
    max_part_size: int = MAX_LECTURE_PART_SIZE,
) -> list[LecturePart]:
    stream_students = (
        db.query(LectureStreamStudent)
        .join(Student, Student.id == LectureStreamStudent.student_id)
        .filter(
            LectureStreamStudent.lecture_stream_id
            == lecture_stream.id,
        )
        .order_by(
            Student.group_id.asc(),
            Student.full_name.asc(),
            LectureStreamStudent.list_order.asc(),
        )
        .all()
    )

    if not stream_students:
        raise ValueError(
            f"В потоке {lecture_stream.name} нет студентов."
        )

    existing_parts = (
        db.query(LecturePart)
        .filter(
            LecturePart.lecture_stream_id == lecture_stream.id,
            LecturePart.version == version,
        )
        .count()
    )
    if existing_parts:
        raise ValueError(
            f"Для потока {lecture_stream.name} уже существует "
            f"версия лекционных частей {version}."
        )

    sizes = calculate_lecture_part_sizes(
        student_count=len(stream_students),
        max_part_size=max_part_size,
    )

    parts: list[LecturePart] = []
    student_index = 0

    for part_number, part_size in enumerate(sizes, start=1):
        part = LecturePart(
            lecture_stream_id=lecture_stream.id,
            version=version,
            part_number=part_number,
            name=(
                f"{lecture_stream.name} — "
                f"Лекционная часть {part_number}"
            ),
            student_count=part_size,
        )
        db.add(part)
        db.flush()
        parts.append(part)

        selected_students = stream_students[
            student_index:student_index + part_size
        ]
        for stream_student in selected_students:
            db.add(
                LecturePartStudent(
                    lecture_part_id=part.id,
                    student_id=stream_student.student_id,
                    list_order=stream_student.list_order,
                )
            )
        student_index += part_size

    db.commit()
    for part in parts:
        db.refresh(part)

    return parts
