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
    GenerationJob,
    ScheduleVersion,
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
DEMO_SPECIALTY_CODE = "B057"
DEMO_SPECIALTY_SHORT_NAME = "ИС"
DEMO_EMAIL_DOMAIN = "demo.smartschedule.local"
DEMO_CLASSROOM_NAMES = {
    "101", "102", "103", "104", "201", "202",
    "301", "302", "303", "304", "305", "401", "402",
}
ACADEMIC_WEEKS = 18

SPECIALTY_DATA = [
    (DEMO_SPECIALTY_CODE, DEMO_SPECIALTY_SHORT_NAME, "Информационные системы"),
]

SUBJECT_DATA = [
    ("MATH101", "Математика", 4, 4, 0),
    ("PROG101", "Программирование", 2, 2, 4),
    ("DB101", "Базы данных", 2, 2, 2),
    ("OS101", "Операционные системы", 2, 2, 2),
    ("NET101", "Компьютерные сети", 2, 2, 2),
    ("ALGO101", "Алгоритмы и структуры данных", 2, 4, 2),
    ("SEC101", "Информационная безопасность", 2, 2, 2),
    ("WEB101", "Веб-разработка", 2, 2, 4),
]


TEACHER_DATA = [
    ("Иванова Анна Сергеевна", "Доцент", "Кафедра ИС"),
    ("Петров Алексей Олегович", "Старший преподаватель", "Кафедра ИС"),
    ("Сидоров Дмитрий Андреевич", "Преподаватель", "Кафедра ИС"),
    ("Ким Алина Сериковна", "Доцент", "Кафедра ИС"),
    ("Ахметов Руслан Маратович", "Старший преподаватель", "Кафедра ИС"),
    ("Нурланова Дана Ерлановна", "Преподаватель", "Кафедра ИС"),
    ("Омаров Ермек Бауыржанович", "Доцент", "Кафедра ИС"),
    ("Серикова Анастасия Викторовна", "Преподаватель", "Кафедра ИС"),
]


CLASSROOM_DATA = [
    ("101", 30, "ordinary", None),
    ("102", 30, "ordinary", "Проектор"),
    ("103", 25, "ordinary", None),
    ("104", 28, "ordinary", "Проектор"),
    ("201", 30, "ordinary", None),
    ("202", 28, "ordinary", "Проектор"),
    ("301", 14, "computer_lab", "14 компьютеров"),
    ("302", 14, "computer_lab", "14 компьютеров"),
    ("303", 14, "computer_lab", "14 компьютеров"),
    ("304", 16, "computer_lab", "16 компьютеров"),
    ("305", 16, "computer_lab", "16 компьютеров"),
    ("401", 70, "ordinary", "Проектор"),
    ("402", 70, "ordinary", "Проектор"),
]

def reset_demo_data(db: Session) -> None:
    print()
    print("=" * 70)
    print("ОЧИСТКА ПРЕДЫДУЩЕГО ДЕМО-НАБОРА")
    print("=" * 70)

    specialty_ids = [
        row[0]
        for row in db.query(Specialty.id)
        .filter(
            (Specialty.code.like("TEST%"))
            | (Specialty.code == DEMO_SPECIALTY_CODE)
            | (Specialty.name == "Информационные системы")
        )
        .all()
    ]

    group_ids = [
        row[0]
        for row in db.query(Group.id)
        .filter(
            (Group.name.like("TEST%"))
            | (Group.name.like("ИС-%"))
        )
        .all()
    ]

    student_ids = [
        row[0]
        for row in db.query(Student.id)
        .filter(
            (Student.full_name.like("TEST%"))
            | (Student.group_id.in_(group_ids))
        )
        .all()
    ]

    subject_ids = [
        row[0]
        for row in db.query(Subject.id)
        .filter(
            (Subject.code.like("TEST%"))
            | (Subject.code.in_([code for code, *_ in SUBJECT_DATA]))
        )
        .all()
    ]

    teacher_ids = [
        row[0]
        for row in db.query(Teacher.id)
        .filter(
            (Teacher.full_name.like("TEST%"))
            | (Teacher.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
        )
        .all()
    ]

    classroom_ids = [
        row[0]
        for row in db.query(Classroom.id)
        .filter(
            (Classroom.name.like("TEST%"))
            | (Classroom.name.in_(DEMO_CLASSROOM_NAMES))
        )
        .all()
    ]

    academic_period_ids = [
        row[0]
        for row in db.query(AcademicPeriod.id)
        .filter(
            (AcademicPeriod.name.like("TEST%"))
            | (AcademicPeriod.name == "2026/2027 — 1 семестр")
            | (AcademicPeriod.name == "1 семестр 2026-2027")
        )
        .all()
    ]

    curriculum_ids = [
        row[0]
        for row in db.query(Curriculum.id)
        .filter(
            (Curriculum.specialty_id.in_(specialty_ids))
            | (Curriculum.academic_period_id.in_(academic_period_ids))
        )
        .all()
    ]

    lecture_stream_ids = [
        row[0]
        for row in db.query(LectureStream.id)
        .filter(LectureStream.specialty_id.in_(specialty_ids))
        .all()
    ]
    legacy_stream_ids = [
        row[0]
        for row in db.query(LectureStream.id)
        .filter(LectureStream.name.like("ИС-% / ИС-%"))
        .all()
    ]
    lecture_stream_ids = sorted(
        set(lecture_stream_ids).union(legacy_stream_ids)
    )

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

    if academic_period_ids:
        period_version_ids = [
            row[0]
            for row in db.query(ScheduleVersion.id)
            .filter(ScheduleVersion.academic_period_id.in_(academic_period_ids))
            .all()
        ]
        db.query(GenerationJob).filter(
            GenerationJob.academic_period_id.in_(academic_period_ids)
        ).delete(synchronize_session=False)
        if period_version_ids:
            db.query(ScheduleVersion).filter(
                ScheduleVersion.id.in_(period_version_ids)
            ).delete(synchronize_session=False)

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
        removable_specialty_ids = [
            specialty_id
            for specialty_id in specialty_ids
            if db.query(Group.id)
            .filter(Group.specialty_id == specialty_id)
            .first()
            is None
            and db.query(Curriculum.id)
            .filter(Curriculum.specialty_id == specialty_id)
            .first()
            is None
        ]
        if removable_specialty_ids:
            db.query(Specialty).filter(
                Specialty.id.in_(removable_specialty_ids)
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

    return parser.parse_args()


def create_academic_period(db: Session) -> AcademicPeriod:
    period = AcademicPeriod(
        name="2026/2027 — 1 семестр",
        academic_year="2026-2027",
        semester=1,
        start_date=date(2026, 9, 1),
        end_date=date(2027, 1, 31),
        weeks=18,
    )

    db.add(period)
    db.flush()

    return period


def create_specialties(db: Session) -> list[tuple[Specialty, str]]:
    specialties = []

    for code, short_name, name in SPECIALTY_DATA:
        specialty = Specialty(
            code=code,
            name=name,
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
) -> tuple[list[Group], list[Student]]:
    groups: list[Group] = []
    students: list[Student] = []

    specialty = specialties[0][0]
    group_data = [
        ("ИС-41", 24, "Казахский"),
        ("ИС-42", 24, "Русский"),
        ("ИС-43", 25, "Казахский"),
        ("ИС-44", 25, "Русский"),
        ("ИС-45", 24, "Казахский"),
        ("ИС-46", 24, "Русский"),
        ("ИС-47", 25, "Казахский"),
    ]
    surnames = [
        "Абдрахманов", "Ахметова", "Бекетов", "Сарсенова",
        "Нурланов", "Омарова", "Касымов", "Иванова",
        "Петров", "Ким", "Серикова", "Жумабаев",
    ]
    names = [
        "Алихан", "Аружан", "Данияр", "Алина", "Рустам",
        "Дана", "Мирас", "Анна", "Алексей", "Айдана",
        "Ермек", "Анастасия",
    ]
    student_number = 0
    for group_name, group_size, language in group_data:
        group = Group(
            name=group_name,
            specialty_id=specialty.id,
            course=4,
            language=language,
            student_count=group_size,
        )
        db.add(group)
        db.flush()
        groups.append(group)
        for index in range(group_size):
            suffix = student_number // len(surnames) + 1
            student = Student(
                full_name=(
                    f"{surnames[student_number % len(surnames)]} "
                    f"{names[student_number % len(names)]}"
                    f"{f' {suffix}' if suffix > 1 else ''}"
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
                name=f"ИС — {language} поток",
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
) -> list[Subject]:
    subjects = []

    for code, name, _, _, _ in SUBJECT_DATA:
        subject = Subject(
            code=code,
            name=name,
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
            course=4,
            semester=1,
            academic_year="2026-2027",
            academic_period_id=period.id,
        )

        db.add(curriculum)
        db.flush()

        curricula.append(curriculum)

        load_by_code = {
            code: (lecture, practice, lab)
            for code, _, lecture, practice, lab in SUBJECT_DATA
        }
        for subject in subjects:
            lecture_hours, practice_hours, lab_hours = load_by_code[
                subject.code
            ]

            weeks = period.weeks
            curriculum_subject = CurriculumSubject(
                curriculum_id=curriculum.id,
                subject_id=subject.id,
                hours=(
                    (lecture_hours + practice_hours + lab_hours) * weeks
                ),
                lecture_hours=lecture_hours * weeks,
                practice_hours=practice_hours * weeks,
                lab_hours=lab_hours * weeks,
                lecture_per_week=lecture_hours,
                practice_per_week=practice_hours,
                lab_per_week=lab_hours,
                lecture_max_students=70,
                practice_max_students=30,
                lab_max_students=16,
            )

            db.add(curriculum_subject)

    db.flush()

    return curricula


def create_teachers(
    db: Session,
) -> list[Teacher]:
    teachers = []

    for index, (
        full_name,
        position,
        department,
    ) in enumerate(TEACHER_DATA, start=1):
        teacher = Teacher(
            full_name=full_name,
            position=position,
            department=department,
            email=f"teacher{index}@{DEMO_EMAIL_DOMAIN}",
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
        # One lecture assignment is created for every language and
        # lecture part, while the curriculum stores the subject's
        # weekly value once.
        lecture_per_week = curriculum_subject.lecture_per_week * 4

        load = TeacherLoad(
            teacher_id=teacher.id,
            curriculum_subject_id=(
                curriculum_subject.id
            ),
            lecture_hours=lecture_per_week * ACADEMIC_WEEKS,
            practice_hours=(
                curriculum_subject.practice_hours
            ),
            lab_hours=(
                curriculum_subject.lab_hours
            ),
            lecture_per_week=lecture_per_week,
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
            lecture_hours //= len(lecture_parts_by_stream[stream.id])

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

                for part in lecture_parts:
                    assignment = create_teacher_assignment(
                        db=db,
                        teacher_load_id=load.id,
                        target_type="lecture_part",
                        lecture_hours=lecture_hours,
                        practice_hours=0,
                        lab_hours=0,
                        targets=[{
                            "target_type": "lecture_part",
                            "lecture_part_id": part.id,
                        }],
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

                lab_hours = load.lab_per_week

                practice_assignment_hours = practice_hours // len(languages)
                lab_assignment_hours = lab_hours // len(languages)
                subgroup_chunks = [
                    subgroups[index:index + 5]
                    for index in range(0, len(subgroups), 5)
                ]
                practice_base = practice_assignment_hours // len(subgroup_chunks)
                practice_extra = practice_assignment_hours % len(subgroup_chunks)
                lab_base = lab_assignment_hours // len(subgroup_chunks)
                lab_extra = lab_assignment_hours % len(subgroup_chunks)
                for chunk_index, subgroup_chunk in enumerate(subgroup_chunks):
                    chunk_practice_hours = practice_base + (
                        1 if chunk_index < practice_extra else 0
                    )
                    chunk_lab_hours = lab_base + (
                        1 if chunk_index < lab_extra else 0
                    )
                    if chunk_practice_hours <= 0 and chunk_lab_hours <= 0:
                        continue
                    assignment = create_teacher_assignment(
                        db=db,
                        teacher_load_id=load.id,
                        target_type="subgroup",
                        lecture_hours=0,
                        practice_hours=chunk_practice_hours,
                        lab_hours=chunk_lab_hours,
                        targets=[{
                            "target_type": "subgroup",
                            "subgroup_id": subgroup.id,
                        } for subgroup in subgroup_chunk],
                    )
                    lessons = create_lessons_for_assignment(
                        db=db,
                        assignment=assignment,
                    )
                    lessons_created += len(lessons)

    return lessons_created


def create_classrooms(
    db: Session,
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
            name=name,
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

    print("=" * 70)
    print("SmartSchedule AI — генератор демонстрационных данных")
    print("=" * 70)
    print(
        f"Размер тестового набора: "
        "171 студент, специальность «Информационные системы»"
    )
    print(
        "Перед генерацией будет очищен предыдущий набор "
        "SmartSchedule Demo."
    )
    print()

    db = SessionLocal()

    try:
        reset_demo_data(db=db)

        print("[1/10] Академический период...")
        period = create_academic_period(
            db,
        )

        print("[2/10] Специальности...")
        specialties = create_specialties(
            db,
        )

        print("[3/10] Группы и студенты...")
        groups, students = (
            create_groups_and_students(
                db=db,
                specialties=specialties,
            )
        )

        print("[4/10] Лекционные потоки...")
        streams = create_lecture_streams(
            db=db,
            period=period,
            specialties=specialties,
            groups=groups,
            students=students,
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
            "Демонстрационный набор сохранён в PostgreSQL."
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