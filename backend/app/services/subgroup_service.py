from sqlalchemy.orm import Session

from backend.app.models.lecture_stream import LectureStream
from backend.app.models.lecture_stream_student import LectureStreamStudent
from backend.app.models.subgroup import Subgroup
from backend.app.models.subgroup_set import SubgroupSet
from backend.app.models.subgroup_student import SubgroupStudent


def calculate_subgroup_sizes(student_count: int) -> list[int]:
    """
    Распределяет студентов потока на сбалансированное количество подгрупп.

    Целевой размер подгруппы:
    примерно 12–16 студентов.

    Порядок студентов сохраняется.
    Разница между размерами подгрупп не превышает 1 студента.
    """

    if student_count <= 0:
        raise ValueError(
            "Количество студентов должно быть больше нуля."
        )

    # Подбираем количество подгрупп так,
    # чтобы средний размер был максимально близок к 14.
    subgroup_count = max(1, round(student_count / 14))

    # Для небольших потоков не создаём лишние подгруппы.
    if subgroup_count > 1 and student_count / subgroup_count < 12:
        subgroup_count -= 1

    base_size = student_count // subgroup_count
    remainder = student_count % subgroup_count

    sizes = []

    for index in range(subgroup_count):
        size = base_size

        if index < remainder:
            size += 1

        sizes.append(size)

    return sizes


def create_subgroups_for_stream(
    db: Session,
    lecture_stream: LectureStream,
    academic_period_id: int,
) -> list[Subgroup]:
    """
    Создаёт набор постоянных подгрупп для лекционного потока.

    Подгруппы формируются один раз для версии SubgroupSet.
    Студенты распределяются последовательно согласно list_order.
    """

    stream_students = (
        db.query(LectureStreamStudent)
        .filter(
            LectureStreamStudent.lecture_stream_id
            == lecture_stream.id
        )
        .order_by(
            LectureStreamStudent.list_order.asc()
        )
        .all()
    )

    if not stream_students:
        raise ValueError(
            f"В потоке {lecture_stream.name} нет студентов."
        )

    existing_set = (
        db.query(SubgroupSet)
        .filter(
            SubgroupSet.lecture_stream_id == lecture_stream.id,
            SubgroupSet.academic_period_id == academic_period_id,
            SubgroupSet.status == "active",
        )
        .first()
    )

    if existing_set is not None:
        raise ValueError(
            "Для этого потока уже существует активный набор подгрупп."
        )

    last_set = (
        db.query(SubgroupSet)
        .filter(
            SubgroupSet.lecture_stream_id == lecture_stream.id,
            SubgroupSet.academic_period_id == academic_period_id,
        )
        .order_by(SubgroupSet.version.desc())
        .first()
    )

    next_version = (
        last_set.version + 1
        if last_set is not None
        else 1
    )

    subgroup_set = SubgroupSet(
        lecture_stream_id=lecture_stream.id,
        academic_period_id=academic_period_id,
        version=next_version,
        status="active",
    )

    db.add(subgroup_set)
    db.flush()

    sizes = calculate_subgroup_sizes(
        len(stream_students)
    )

    subgroups = []

    student_index = 0

    for subgroup_number, subgroup_size in enumerate(
        sizes,
        start=1,
    ):
        subgroup = Subgroup(
            subgroup_set_id=subgroup_set.id,
            name=(
                f"{lecture_stream.name} "
                f"— Подгруппа {subgroup_number}"
            ),
            subgroup_number=subgroup_number,
            student_count=subgroup_size,
        )

        db.add(subgroup)
        db.flush()

        subgroups.append(subgroup)

        selected_students = stream_students[
            student_index:
            student_index + subgroup_size
        ]

        selected_group_ids = {
            stream_student.student.group_id
            for stream_student in selected_students
            if stream_student.student is not None
        }
        if len(selected_group_ids) == 1:
            subgroup.group_id = selected_group_ids.pop()

        for stream_student in selected_students:
            db.add(
                SubgroupStudent(
                    subgroup_id=subgroup.id,
                    student_id=stream_student.student_id,
                )
            )

        student_index += subgroup_size

    db.commit()

    for subgroup in subgroups:
        db.refresh(subgroup)

    return subgroups