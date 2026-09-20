from __future__ import annotations

import argparse
import random
from datetime import date

from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models import (
    AcademicPeriod,
    Classroom,
    Curriculum,
    CurriculumSubject,
    Group,
    LectureStream,
    LectureStreamGroup,
    LectureStreamStudent,
    LecturePart,
    LecturePartStudent,
    Specialty,
    Student,
    Subject,
    Teacher,
    TeacherLoad,
)
from backend.app.services.lesson_service import create_lessons_for_assignment
from backend.app.services.subgroup_service import create_subgroups_for_stream
from backend.app.services.lecture_part_service import (
    create_lecture_parts_for_stream,
)
from backend.app.services.teacher_assignment_service import (
    create_teacher_assignment,
)
from backend.app.models.academic_period import AcademicPeriod
from backend.app.models.classroom import Classroom
from backend.app.models.curriculum import Curriculum
from backend.app.models.curriculum_subject import CurriculumSubject
from backend.app.models.group import Group
from backend.app.models.lecture_stream import LectureStream
from backend.app.models.lecture_stream_group import LectureStreamGroup
from backend.app.models.lecture_stream_student import LectureStreamStudent
from backend.app.models.lesson import Lesson
from backend.app.models.lesson_target import LessonTarget
from backend.app.models.specialty import Specialty
from backend.app.models.student import Student
from backend.app.models.subgroup import Subgroup
from backend.app.models.subgroup_set import SubgroupSet
from backend.app.models.subgroup_student import SubgroupStudent
from backend.app.models.subject import Subject
from backend.app.models.teacher import Teacher
from backend.app.models.teacher_assignment import TeacherAssignment
from backend.app.models.teacher_assignment_target import TeacherAssignmentTarget
from backend.app.models.teacher_load import TeacherLoad

RANDOM_SEED = 42

MIN_GROUP_SIZE = 12
MAX_GROUP_SIZE = 30
MAX_GROUPS_PER_SPECIALTY = 9


SPECIALTY_DATA = [
    ("B057", "ИС", "Информационные системы"),
    ("B058", "КБ", "Кибербезопасность"),
    ("B059", "ТУ", "Технологии искусственного интеллекта"),
]


SUBJECT_DATA = [
    ("INF101", "Информационные технологии"),
    ("PROG101", "Программирование"),
    ("MATH101", "Математика"),
    ("DB101", "Базы данных"),
    ("WEB101", "Веб-технологии"),
]


TEACHER_DATA = [
    ("Иванов Иван Иванович", "Старший преподаватель", "Кафедра ИС"),
    ("Петров Петр Петрович", "Преподаватель", "Кафедра ИС"),
    ("Сидорова Анна Сергеевна", "Доцент", "Кафедра ИС"),
    ("Ким Алексей Владимирович", "Преподаватель", "Кафедра ИС"),
    ("Ахметова Динара Маратовна", "Старший преподаватель", "Кафедра ИС"),
    ("Нурланов Тимур Серикович", "Преподаватель", "Кафедра КБ"),
    ("Ибраева Айжан Маратовна", "Доцент", "Кафедра КБ"),
    ("Сериков Руслан Ерланович", "Преподаватель", "Кафедра ТУ"),
]


CLASSROOM_DATA = [
    ("301", 30, "ordinary", None),
    ("302", 28, "ordinary", "Проектор"),
    ("303", 30, "computer_lab", "30 компьютеров"),
    ("310", 30, "computer_lab", "30 компьютеров"),
    ("311", 30, "computer_lab", "30 компьютеров"),
    ("312", 30, "computer_lab", "30 компьютеров"),
    ("304", 24, "computer_lab", "24 компьютера"),
    ("305", 20, "computer_lab", "20 компьютеров"),
    ("309", 16, "computer_lab", "16 компьютеров"),
    ("306", 30, "ordinary", "Проектор"),
    ("307", 25, "ordinary", None),
    ("308", 30, "ordinary", "Проектор"),
    ("LECTURE-101", 120, "ordinary", "Проектор"),
    ("LECTURE-102", 120, "ordinary", "Проектор"),
]

def reset_test_data(db: Session, prefix: str) -> None:
    print()
    print("=" * 70)
    print(f"ОЧИСТКА ПРЕДЫДУЩЕГО ТЕСТОВОГО НАБОРА: {prefix}")
    print("=" * 70)

    specialty_ids = [
        row[0]
        for row in db.query(Specialty.id)
        .filter(Specialty.code.like(f"{prefix}_%"))
        .all()
    ]

    group_ids = [
        row[0]
        for row in db.query(Group.id)
        .filter(Group.name.like(f"{prefix}-%"))
        .all()
    ]

    student_ids = [
        row[0]
        for row in db.query(Student.id)
        .filter(Student.full_name.like(f"{prefix}%"))
        .all()
    ]

    subject_ids = [
        row[0]
        for row in db.query(Subject.id)
        .filter(Subject.code.like(f"{prefix}_%"))
        .all()
    ]

    teacher_ids = [
        row[0]
        for row in db.query(Teacher.id)
        .filter(Teacher.full_name.like(f"{prefix}%"))
        .all()
    ]

    classroom_ids = [
        row[0]
        for row in db.query(Classroom.id)
        .filter(Classroom.name.like(f"{prefix}-%"))
        .all()
    ]

    academic_period_ids = [
        row[0]
        for row in db.query(AcademicPeriod.id)
        .filter(AcademicPeriod.name.like(f"{prefix}%"))
        .all()
    ]

    curriculum_ids = [
        row[0]
        for row in db.query(Curriculum.id)
        .filter(Curriculum.specialty_id.in_(specialty_ids))
        .all()
    ]

    lecture_stream_ids = [
        row[0]
        for row in db.query(LectureStream.id)
        .filter(LectureStream.specialty_id.in_(specialty_ids))
        .all()
    ]

    subgroup_set_ids = [
        row[0]
        for row in db.query(SubgroupSet.id)
        .filter(SubgroupSet.lecture_stream_id.in_(lecture_stream_ids))
        .all()
    ]

    subgroup_ids = [
        row[0]
        for row in db.query(Subgroup.id)
        .filter(Subgroup.subgroup_set_id.in_(subgroup_set_ids))
        .all()
    ]

    lecture_part_ids = [
        row[0]
        for row in db.query(LecturePart.id)
        .filter(
            LecturePart.lecture_stream_id.in_(lecture_stream_ids)
        )
        .all()
    ]

    teacher_load_ids = [
        row[0]
        for row in db.query(TeacherLoad.id)
        .filter(TeacherLoad.teacher_id.in_(teacher_ids))
        .all()
    ]

    assignment_ids = [
        row[0]
        for row in db.query(TeacherAssignment.id)
        .filter(TeacherAssignment.teacher_load_id.in_(teacher_load_ids))
        .all()
    ]

    lesson_ids = [
        row[0]
        for row in db.query(Lesson.id)
        .join(LessonTarget, LessonTarget.lesson_id == Lesson.id)
        .filter(LessonTarget.teacher_assignment_id.in_(assignment_ids))
        .distinct()
        .all()
    ]

    if lesson_ids:
        db.query(LessonTarget).filter(
            LessonTarget.lesson_id.in_(lesson_ids)
        ).delete(synchronize_session=False)

        db.query(Lesson).filter(
            Lesson.id.in_(lesson_ids)
        ).delete(synchronize_session=False)

    if assignment_ids:
        db.query(TeacherAssignmentTarget).filter(
            TeacherAssignmentTarget.teacher_assignment_id.in_(assignment_ids)
        ).delete(synchronize_session=False)

        db.query(TeacherAssignment).filter(
            TeacherAssignment.id.in_(assignment_ids)
        ).delete(synchronize_session=False)

    if teacher_load_ids:
        db.query(TeacherLoad).filter(
            TeacherLoad.id.in_(teacher_load_ids)
        ).delete(synchronize_session=False)

    if subgroup_ids:
        db.query(SubgroupStudent).filter(
            SubgroupStudent.subgroup_id.in_(subgroup_ids)
        ).delete(synchronize_session=False)

        db.query(Subgroup).filter(
            Subgroup.id.in_(subgroup_ids)
        ).delete(synchronize_session=False)

    if lecture_part_ids:
        db.query(LecturePartStudent).filter(
            LecturePartStudent.lecture_part_id.in_(lecture_part_ids)
        ).delete(synchronize_session=False)

        db.query(LecturePart).filter(
            LecturePart.id.in_(lecture_part_ids)
        ).delete(synchronize_session=False)

    if subgroup_set_ids:
        db.query(SubgroupSet).filter(
            SubgroupSet.id.in_(subgroup_set_ids)
        ).delete(synchronize_session=False)

    if lecture_stream_ids:
        db.query(LectureStreamStudent).filter(
            LectureStreamStudent.lecture_stream_id.in_(lecture_stream_ids)
        ).delete(synchronize_session=False)

        db.query(LectureStreamGroup).filter(
            LectureStreamGroup.lecture_stream_id.in_(lecture_stream_ids)
        ).delete(synchronize_session=False)

        db.query(LectureStream).filter(
            LectureStream.id.in_(lecture_stream_ids)
        ).delete(synchronize_session=False)

    if curriculum_ids:
        db.query(CurriculumSubject).filter(
            CurriculumSubject.curriculum_id.in_(curriculum_ids)
        ).delete(synchronize_session=False)

        db.query(Curriculum).filter(
            Curriculum.id.in_(curriculum_ids)
        ).delete(synchronize_session=False)

    if student_ids:
        db.query(Student).filter(
            Student.id.in_(student_ids)
        ).delete(synchronize_session=False)

    if group_ids:
        db.query(Group).filter(
            Group.id.in_(group_ids)
        ).delete(synchronize_session=False)

    if classroom_ids:
        db.query(Classroom).filter(
            Classroom.id.in_(classroom_ids)
        ).delete(synchronize_session=False)

    if teacher_ids:
        db.query(Teacher).filter(
            Teacher.id.in_(teacher_ids)
        ).delete(synchronize_session=False)

    if subject_ids:
        db.query(Subject).filter(
            Subject.id.in_(subject_ids)
        ).delete(synchronize_session=False)

    if specialty_ids:
        db.query(Specialty).filter(
            Specialty.id.in_(specialty_ids)
        ).delete(synchronize_session=False)

    if academic_period_ids:
        db.query(AcademicPeriod).filter(
            AcademicPeriod.id.in_(academic_period_ids)
        ).delete(synchronize_session=False)

    db.commit()

    print("Предыдущий тестовый набор удалён.")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Генерация тестовых данных SmartSchedule AI."
    )

    parser.add_argument(
        "--students",
        type=int,
        choices=[200, 400],
        default=200,
        help="Количество студентов: 200 или 400.",
    )

    return parser.parse_args()


def calculate_group_sizes(
    student_count: int,
) -> list[int]:
    group_count = (
        student_count + MAX_GROUP_SIZE - 1
    ) // MAX_GROUP_SIZE

    if group_count > MAX_GROUPS_PER_SPECIALTY:
        raise ValueError(
            f"Для {student_count} студентов требуется "
            f"{group_count} групп. "
            f"Максимум: {MAX_GROUPS_PER_SPECIALTY}."
        )

    while (
        group_count > 1
        and student_count / group_count < MIN_GROUP_SIZE
    ):
        group_count -= 1

    base_size = student_count // group_count
    remainder = student_count % group_count

    sizes = []

    for index in range(group_count):
        size = base_size + (
            1 if index < remainder else 0
        )

        if not (
            MIN_GROUP_SIZE
            <= size
            <= MAX_GROUP_SIZE
        ):
            raise ValueError(
                f"Недопустимый размер группы: {size}."
            )

        sizes.append(size)

    return sizes


def get_specialty_student_counts(
    total_students: int,
) -> dict[str, int]:
    """
    Распределение студентов:

    200:
        ИС = 100
        КБ = 50
        ТУ = 50

    400:
        ИС = 200
        КБ = 100
        ТУ = 100
    """

    information_systems = total_students // 2
    cybersecurity = total_students // 4
    ai = (
        total_students
        - information_systems
        - cybersecurity
    )

    return {
        "ИС": information_systems,
        "КБ": cybersecurity,
        "ТУ": ai,
    }


def create_academic_period(
    db: Session,
    total_students: int,
) -> AcademicPeriod:
    period = AcademicPeriod(
        name=(
            f"TEST{total_students} — "
            "2026/2027 — 1 семестр"
        ),
        academic_year="2026-2027",
        semester=1,
        start_date=date(2026, 9, 1),
        end_date=date(2027, 1, 31),
        weeks=18,
    )

    db.add(period)
    db.flush()

    return period


def create_specialties(
    db: Session,
    total_students: int,
) -> list[Specialty]:
    specialties = []

    for code, short_name, name in SPECIALTY_DATA:
        specialty = Specialty(
            code=f"TEST{total_students}_{code}",
            name=(
                f"TEST{total_students} — "
                f"{name}"
            ),
        )

        db.add(specialty)
        db.flush()

        specialties.append(
            (
                specialty,
                short_name,
            )
        )

    return specialties


def create_groups_and_students(
    db: Session,
    specialties: list[tuple[Specialty, str]],
    total_students: int,
) -> tuple[list[Group], list[Student]]:
    groups: list[Group] = []
    students: list[Student] = []

    specialty_counts = get_specialty_student_counts(
        total_students
    )

    student_number = 1

    for specialty, short_name in specialties:
        specialty_student_count = specialty_counts[
            short_name
        ]

        group_sizes = calculate_group_sizes(
            specialty_student_count
        )

        for group_number, group_size in enumerate(
            group_sizes,
            start=1,
        ):
            if group_number % 2 == 1:
                language = "Казахский"
            else:
                language = "Русский"

            group = Group(
                name=(
                    f"TEST{total_students}-"
                    f"{short_name}-"
                    f"{group_number:02d}"
                ),
                specialty_id=specialty.id,
                course=1,
                language=language,
                student_count=group_size,
            )

            db.add(group)
            db.flush()

            groups.append(group)

            for _ in range(group_size):
                student = Student(
                    full_name=(
                        f"TEST{total_students} "
                        f"Студент "
                        f"{student_number:04d}"
                    ),
                    group_id=group.id,
                )

                db.add(student)
                students.append(student)

                student_number += 1

    db.flush()

    return groups, students


def create_lecture_streams(
    db: Session,
    period: AcademicPeriod,
    specialties: list[tuple[Specialty, str]],
    groups: list[Group],
    students: list[Student],
    total_students: int,
) -> list[LectureStream]:
    streams: list[LectureStream] = []

    students_by_group: dict[
        int,
        list[Student],
    ] = {}

    for student in students:
        students_by_group.setdefault(
            student.group_id,
            [],
        ).append(student)

    specialty_by_id = {
        specialty.id: (
            specialty,
            short_name,
        )
        for specialty, short_name in specialties
    }

    groups_by_specialty_language: dict[
        tuple[int, str],
        list[Group],
    ] = {}

    for group in groups:
        key = (
            group.specialty_id,
            group.language,
        )

        groups_by_specialty_language.setdefault(
            key,
            [],
        ).append(group)

    for specialty, short_name in specialties:
        for language in (
            "Казахский",
            "Русский",
        ):
            stream_groups = groups_by_specialty_language.get(
                (
                    specialty.id,
                    language,
                ),
                [],
            )

            if not stream_groups:
                continue

            stream = LectureStream(
                name=(
                    f"TEST{total_students} — "
                    f"{short_name} — "
                    f"{language}"
                ),
                specialty_id=specialty.id,
                academic_period_id=period.id,
                is_active=True,
            )

            db.add(stream)
            db.flush()

            streams.append(stream)

            list_order = 1

            for group in sorted(
                stream_groups,
                key=lambda item: item.name,
            ):
                db.add(
                    LectureStreamGroup(
                        lecture_stream_id=stream.id,
                        group_id=group.id,
                    )
                )

                for student in students_by_group[
                    group.id
                ]:
                    db.add(
                        LectureStreamStudent(
                            lecture_stream_id=stream.id,
                            student_id=student.id,
                            list_order=list_order,
                        )
                    )

                    list_order += 1

    db.flush()

    return streams


def create_subjects(
    db: Session,
    total_students: int,
) -> list[Subject]:
    subjects = []

    for code, name in SUBJECT_DATA:
        subject = Subject(
            code=f"TEST{total_students}_{code}",
            name=(
                f"TEST{total_students} — "
                f"{name}"
            ),
        )

        db.add(subject)
        db.flush()

        subjects.append(subject)

    return subjects


def create_curricula(
    db: Session,
    period: AcademicPeriod,
    specialties: list[tuple[Specialty, str]],
    subjects: list[Subject],
) -> list[Curriculum]:
    curricula = []

    for specialty, _ in specialties:
        curriculum = Curriculum(
            specialty_id=specialty.id,
            course=1,
            semester=1,
            academic_year="2026-2027",
            academic_period_id=period.id,
        )

        db.add(curriculum)
        db.flush()

        curricula.append(curriculum)

        for subject in subjects:
            if subject.code.endswith("PROG101"):
                lecture_hours = 36
                practice_hours = 0
                lab_hours = 36

            elif subject.code.endswith("DB101"):
                lecture_hours = 36
                practice_hours = 0
                lab_hours = 36

            else:
                lecture_hours = 36
                practice_hours = 36
                lab_hours = 0

            curriculum_subject = CurriculumSubject(
                curriculum_id=curriculum.id,
                subject_id=subject.id,
                hours=(
                    lecture_hours
                    + practice_hours
                    + lab_hours
                ),
                lecture_hours=lecture_hours,
                practice_hours=practice_hours,
                lab_hours=lab_hours,
                lecture_per_week=2,
                practice_per_week=(
                    2 if practice_hours > 0 else 0
                ),
                lab_per_week=(
                    2 if lab_hours > 0 else 0
                ),
                lecture_max_students=70,
                practice_max_students=30,
                lab_max_students=30,
            )

            db.add(curriculum_subject)

    db.flush()

    return curricula


def create_teachers(
    db: Session,
    total_students: int,
) -> list[Teacher]:
    teachers = []

    for index, (
        full_name,
        position,
        department,
    ) in enumerate(TEACHER_DATA, start=1):
        teacher = Teacher(
            full_name=(
                f"TEST{total_students} — "
                f"{full_name}"
            ),
            position=position,
            department=department,
            email=(
                f"test{total_students}"
                f".teacher{index}"
                f"@smartschedule.local"
            ),
            is_active=True,
        )

        db.add(teacher)
        db.flush()

        teachers.append(teacher)

    return teachers


def create_teacher_loads(
    db: Session,
    teachers: list[Teacher],
    curricula: list[Curriculum],
) -> list[TeacherLoad]:
    loads = []

    curriculum_subjects = []

    for curriculum in curricula:
        curriculum_subjects.extend(
            curriculum.subjects
        )

    for index, curriculum_subject in enumerate(
        curriculum_subjects
    ):
        teacher = teachers[
            index % len(teachers)
        ]

        load = TeacherLoad(
            teacher_id=teacher.id,
            curriculum_subject_id=(
                curriculum_subject.id
            ),
            lecture_hours=(
                curriculum_subject.lecture_hours
            ),
            practice_hours=(
                curriculum_subject.practice_hours
            ),
            lab_hours=(
                curriculum_subject.lab_hours
            ),
            lecture_per_week=(
                curriculum_subject.lecture_per_week
            ),
            practice_per_week=(
                curriculum_subject.practice_per_week
            ),
            lab_per_week=(
                curriculum_subject.lab_per_week
            ),
            lecture_max_students=(
                curriculum_subject.lecture_max_students
            ),
            practice_max_students=(
                curriculum_subject.practice_max_students
            ),
            lab_max_students=(
                curriculum_subject.lab_max_students
            ),
        )

        db.add(load)
        db.flush()

        loads.append(load)

    return loads


def create_subgroups(
    db: Session,
    streams: list[LectureStream],
    period: AcademicPeriod,
) -> dict[int, list]:
    """
    Подгруппы создаются ОДИН РАЗ для каждого
    лекционного потока.

    Один и тот же набор подгрупп затем используется
    всеми предметами этого потока.
    """

    subgroups_by_stream: dict[int, list] = {}

    for stream in streams:
        subgroups = create_subgroups_for_stream(
            db=db,
            lecture_stream=stream,
            academic_period_id=period.id,
        )

        subgroups_by_stream[
            stream.id
        ] = subgroups

    return subgroups_by_stream


def create_assignments_and_lessons(
    db: Session,
    loads: list[TeacherLoad],
    groups: list[Group],
    streams: list[LectureStream],
    subgroups_by_stream: dict[int, list],
    lecture_parts_by_stream: dict[int, list],
) -> int:
    lessons_created = 0

    groups_by_specialty: dict[
        int,
        list[Group],
    ] = {}

    for group in groups:
        groups_by_specialty.setdefault(
            group.specialty_id,
            [],
        ).append(group)

    streams_by_specialty_language: dict[
        tuple[int, str],
        LectureStream,
    ] = {}

    for stream in streams:
        stream_groups = stream.groups

        if not stream_groups:
            continue

        language = stream_groups[0].group.language

        streams_by_specialty_language[
            (
                stream.specialty_id,
                language,
            )
        ] = stream

    for load in loads:
        curriculum_subject = (
            load.curriculum_subject
        )

        curriculum = (
            curriculum_subject.curriculum
        )

        specialty_groups = groups_by_specialty[
            curriculum.specialty_id
        ]

        # -------------------------------------------------
        # Лекция.
        #
        # Лекция проводится отдельно для каждого
        # языкового потока.
        # -------------------------------------------------

        if load.lecture_hours > 0:
            languages = sorted(
                {
                    group.language
                    for group in specialty_groups
                }
            )

            lecture_hours = (
                load.lecture_per_week
                // len(languages)
            )

            if lecture_hours <= 0:
                raise ValueError(
                    "Недостаточно лекционных часов "
                    "для распределения по языковым потокам."
                )

            for language in languages:
                stream = (
                    streams_by_specialty_language[
                        (
                            curriculum.specialty_id,
                            language,
                        )
                    ]
                )

                lecture_parts = lecture_parts_by_stream[stream.id]

                assignment = create_teacher_assignment(
                    db=db,
                    teacher_load_id=load.id,
                    target_type="lecture_part",
                    lecture_hours=lecture_hours,
                    practice_hours=0,
                    lab_hours=0,
                    targets=[
                        {
                            "target_type": "lecture_part",
                            "lecture_part_id": part.id,
                        }
                        for part in lecture_parts
                    ],
                )

                lessons = create_lessons_for_assignment(
                    db=db,
                    assignment=assignment,
                )

                lessons_created += len(lessons)

        # -------------------------------------------------
        # Практика / лабораторные.
        #
        # Используем уже созданные фиксированные
        # подгруппы соответствующего потока.
        # -------------------------------------------------

        if (
            load.practice_hours > 0
            or load.lab_hours > 0
        ):
            languages = sorted(
                {
                    group.language
                    for group in specialty_groups
                }
            )

            for language in languages:
                stream = (
                    streams_by_specialty_language[
                        (
                            curriculum.specialty_id,
                            language,
                        )
                    ]
                )

                subgroups = subgroups_by_stream[
                    stream.id
                ]

                practice_hours = (
                    load.practice_per_week
                )

                lab_hours = load.lab_hours
                lab_hours = load.lab_per_week

                if practice_hours > 0:
                    assignment = create_teacher_assignment(
                        db=db,
                        teacher_load_id=load.id,
                        target_type="subgroup",
                        lecture_hours=0,
                        practice_hours=(
                            practice_hours
                            // len(languages)
                        ),
                        lab_hours=0,
                        targets=[
                            {
                                "target_type": "subgroup",
                                "subgroup_id": subgroup.id,
                            }
                            for subgroup in subgroups
                        ],
                    )

                    lessons = (
                        create_lessons_for_assignment(
                            db=db,
                            assignment=assignment,
                        )
                    )

                    lessons_created += len(
                        lessons
                    )

                if lab_hours > 0:
                    assignment = create_teacher_assignment(
                        db=db,
                        teacher_load_id=load.id,
                        target_type="subgroup",
                        lecture_hours=0,
                        practice_hours=0,
                        lab_hours=(
                            lab_hours
                            // len(languages)
                        ),
                        targets=[
                            {
                                "target_type": "subgroup",
                                "subgroup_id": subgroup.id,
                            }
                            for subgroup in subgroups
                        ],
                    )

                    lessons = (
                        create_lessons_for_assignment(
                            db=db,
                            assignment=assignment,
                        )
                    )

                    lessons_created += len(
                        lessons
                    )

    return lessons_created


def create_classrooms(
    db: Session,
    total_students: int,
) -> list[Classroom]:
    classrooms = []

    for index, (
        name,
        capacity,
        room_type,
        equipment,
    ) in enumerate(
        CLASSROOM_DATA,
        start=1,
    ):
        classroom = Classroom(
            name=(
                f"TEST{total_students}-{name}"
            ),
            capacity=capacity,
            room_type=room_type,
            equipment=equipment,
            is_active=True,
        )

        db.add(classroom)
        db.flush()

        classrooms.append(classroom)

    return classrooms


def print_group_statistics(
    groups: list[Group],
) -> None:
    print()
    print("Группы:")

    for group in groups:
        print(
            f"  {group.name}: "
            f"{group.student_count} студентов, "
            f"{group.language}"
        )


def print_stream_statistics(
    streams: list[LectureStream],
    subgroups_by_stream: dict[int, list],
) -> None:
    print()
    print("Лекционные потоки и подгруппы:")

    for stream in streams:
        subgroups = subgroups_by_stream[
            stream.id
        ]

        print(
            f"  {stream.name}: "
            f"{len(subgroups)} подгрупп"
        )

        for subgroup in subgroups:
            print(
                f"      {subgroup.name}: "
                f"{subgroup.student_count} студентов"
            )

def main() -> None:
    args = parse_args()

    random.seed(RANDOM_SEED)

    total_students = args.students
    test_prefix = f"TEST{total_students}"

    print("=" * 70)
    print(
        "SmartSchedule AI — генератор тестовых данных"
    )
    print("=" * 70)
    print(
        f"Размер тестового набора: "
        f"{total_students} студентов"
    )
    print(
        f"Перед генерацией будет очищен предыдущий набор "
        f"{test_prefix}."
    )
    print()

    db = SessionLocal()

    try:
        reset_test_data(
            db=db,
            prefix=test_prefix,
        )

        print("[1/10] Академический период...")
        period = create_academic_period(
            db,
            total_students,
        )

        print("[2/10] Специальности...")
        specialties = create_specialties(
            db,
            total_students,
        )

        print("[3/10] Группы и студенты...")
        groups, students = (
            create_groups_and_students(
                db=db,
                specialties=specialties,
                total_students=total_students,
            )
        )

        print("[4/10] Лекционные потоки...")
        streams = create_lecture_streams(
            db=db,
            period=period,
            specialties=specialties,
            groups=groups,
            students=students,
            total_students=total_students,
        )

        print("[4.5/10] Части лекционных потоков...")
        lecture_parts_by_stream = {}
        for stream in streams:
            lecture_parts_by_stream[stream.id] = (
                create_lecture_parts_for_stream(
                    db=db,
                    lecture_stream=stream,
                )
            )

        print("[5/10] Предметы...")
        subjects = create_subjects(
            db,
            total_students,
        )

        print("[6/10] Учебные планы...")
        curricula = create_curricula(
            db=db,
            period=period,
            specialties=specialties,
            subjects=subjects,
        )

        print("[7/10] Преподаватели...")
        teachers = create_teachers(
            db,
            total_students,
        )

        print("[8/10] Нагрузка преподавателей...")
        loads = create_teacher_loads(
            db=db,
            teachers=teachers,
            curricula=curricula,
        )

        print("[9/10] Фиксированные подгруппы...")
        subgroups_by_stream = create_subgroups(
            db=db,
            streams=streams,
            period=period,
        )

        print("[10/10] Назначения, занятия и аудитории...")

        lessons_created = (
            create_assignments_and_lessons(
                db=db,
                loads=loads,
                groups=groups,
                streams=streams,
                subgroups_by_stream=(
                    subgroups_by_stream
                ),
                lecture_parts_by_stream=(
                    lecture_parts_by_stream
                ),
            )
        )

        classrooms = create_classrooms(
            db,
            total_students,
        )

        db.commit()

        print()
        print("=" * 70)
        print("ГЕНЕРАЦИЯ УСПЕШНО ЗАВЕРШЕНА")
        print("=" * 70)

        print(
            f"Студентов:       {len(students)}"
        )
        print(
            f"Групп:           {len(groups)}"
        )
        print(
            f"Потоков:         {len(streams)}"
        )
        print(
            f"Специальностей:  {len(specialties)}"
        )
        print(
            f"Предметов:       {len(subjects)}"
        )
        print(
            f"Учебных планов:  {len(curricula)}"
        )
        print(
            f"Преподавателей:  {len(teachers)}"
        )
        print(
            f"Нагрузок:        {len(loads)}"
        )
        print(
            f"Аудиторий:       {len(classrooms)}"
        )
        print(
            f"Занятий:         {lessons_created}"
        )

        print_group_statistics(groups)

        print_stream_statistics(
            streams,
            subgroups_by_stream,
        )

        print()
        print(
            "Тестовый набор сохранён в PostgreSQL."
        )

    except Exception:
        db.rollback()

        print()
        print("=" * 70)
        print("ОШИБКА ГЕНЕРАЦИИ")
        print("=" * 70)

        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()