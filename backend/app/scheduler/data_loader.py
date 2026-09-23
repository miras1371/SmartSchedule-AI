from dataclasses import dataclass
from datetime import time

from sqlalchemy.orm import Session, selectinload

from backend.app.models.classroom import Classroom
from backend.app.models.curriculum import Curriculum
from backend.app.models.curriculum_subject import CurriculumSubject
from backend.app.models.group import Group
from backend.app.models.lesson import Lesson
from backend.app.models.lesson_target import LessonTarget
from backend.app.models.lecture_part import LecturePart
from backend.app.models.lecture_part_student import LecturePartStudent
from backend.app.models.student import Student
from backend.app.models.subgroup import Subgroup
from backend.app.models.subgroup_bundle import SubgroupBundle
from backend.app.models.subgroup_bundle_member import SubgroupBundleMember
from backend.app.models.teacher_assignment import TeacherAssignment
from backend.app.models.teacher_load import TeacherLoad
from backend.app.models.time_slot import TimeSlot
from backend.app.models.subgroup_student import SubgroupStudent
from backend.app.services.teacher_assignment_service import (
    validate_weekly_load,
)


@dataclass(frozen=True)
class SchedulingTarget:
    target_type: str
    target_id: int
    lesson_target_id: int
    student_count: int
    teacher_id: int
    teacher_assignment_id: int
    resource_keys: tuple[tuple[str, int], ...]
    student_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class SchedulingLesson:
    lesson_id: int
    lesson_type: str
    hours: int
    subject_id: int
    targets: tuple[SchedulingTarget, ...]


@dataclass(frozen=True)
class SchedulingTimeSlot:
    time_slot_id: int
    day_of_week: int
    lesson_number: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class SchedulingClassroom:
    classroom_id: int
    name: str
    capacity: int
    room_type: str
    equipment: str | None


@dataclass(frozen=True)
class SchedulingData:
    academic_period_id: int
    lessons: tuple[SchedulingLesson, ...]
    time_slots: tuple[SchedulingTimeSlot, ...]
    classrooms: tuple[SchedulingClassroom, ...]


def load_scheduling_data(
    db: Session,
    academic_period_id: int,
) -> SchedulingData:
    lessons = _load_lessons(
        db=db,
        academic_period_id=academic_period_id,
    )

    time_slots = _load_time_slots(db)

    classrooms = _load_classrooms(db)

    if not lessons:
        raise ValueError(
            f"Для учебного периода id={academic_period_id} "
            "не найдено ни одного занятия."
        )

    if not time_slots:
        raise ValueError(
            "Для генерации расписания не найдено ни одного "
            "временного слота."
        )

    if not classrooms:
        raise ValueError(
            "Для генерации расписания не найдено ни одной "
            "активной аудитории."
        )

    return SchedulingData(
        academic_period_id=academic_period_id,
        lessons=tuple(lessons),
        time_slots=tuple(time_slots),
        classrooms=tuple(classrooms),
    )


def _load_lessons(
    db: Session,
    academic_period_id: int,
) -> list[SchedulingLesson]:
    lessons = (
        db.query(Lesson)
        .join(
            LessonTarget,
            LessonTarget.lesson_id == Lesson.id,
        )
        .join(
            TeacherAssignment,
            TeacherAssignment.id == LessonTarget.teacher_assignment_id,
        )
        .join(
            TeacherLoad,
            TeacherLoad.id == TeacherAssignment.teacher_load_id,
        )
        .join(
            CurriculumSubject,
            CurriculumSubject.id == TeacherLoad.curriculum_subject_id,
        )
        .join(
            Curriculum,
            Curriculum.id == CurriculumSubject.curriculum_id,
        )
        .filter(
            Curriculum.academic_period_id == academic_period_id,
        )
        .options(
            selectinload(Lesson.targets).options(
                selectinload(LessonTarget.teacher_assignment)
                .selectinload(TeacherAssignment.teacher_load)
                .selectinload(TeacherLoad.curriculum_subject)
                .selectinload(CurriculumSubject.curriculum),
                selectinload(LessonTarget.group).selectinload(Group.students),
                selectinload(LessonTarget.subgroup)
                .selectinload(Subgroup.students)
                .selectinload(SubgroupStudent.student)
                .selectinload(Student.group),
                selectinload(LessonTarget.lecture_part)
                .selectinload(LecturePart.students)
                .selectinload(LecturePartStudent.student)
                .selectinload(Student.group),
                selectinload(LessonTarget.subgroup_bundle)
                .selectinload(SubgroupBundle.members)
                .selectinload(SubgroupBundleMember.subgroup)
                .selectinload(Subgroup.students)
                .selectinload(SubgroupStudent.student)
                .selectinload(Student.group),
            )
        )
        .distinct()
        .order_by(
            Lesson.id,
        )
        .all()
    )

    result: list[SchedulingLesson] = []

    for lesson in lessons:
        if not lesson.targets:
            raise ValueError(
                f"Занятие id={lesson.id} не имеет целей."
            )

        targets: list[SchedulingTarget] = []
        subject_ids: set[int] = set()

        for lesson_target in lesson.targets:
            scheduling_target = _build_scheduling_target(
                target=lesson_target,
            )

            assignment = lesson_target.teacher_assignment

            if assignment is None:
                raise ValueError(
                    f"Для цели занятия id={lesson_target.id} "
                    f"не найден TeacherAssignment "
                    f"id={scheduling_target.teacher_assignment_id}."
                )

            if assignment.teacher_load is None:
                raise ValueError(
                    f"Для назначения id={assignment.id} "
                    "не найден TeacherLoad."
                )

            teacher_load = assignment.teacher_load
            validate_weekly_load(teacher_load)

            if teacher_load.curriculum_subject is None:
                raise ValueError(
                    f"Для TeacherLoad id={teacher_load.id} "
                    "не найден CurriculumSubject."
                )

            curriculum_subject = teacher_load.curriculum_subject

            if curriculum_subject.curriculum is None:
                raise ValueError(
                    f"Для CurriculumSubject id="
                    f"{curriculum_subject.id} "
                    "не найден Curriculum."
                )

            curriculum = curriculum_subject.curriculum

            if curriculum.academic_period_id != academic_period_id:
                raise ValueError(
                    f"Занятие id={lesson.id} содержит цель "
                    f"из другого учебного периода: "
                    f"{curriculum.academic_period_id}."
                )

            subject_ids.add(
                curriculum_subject.subject_id
            )

            targets.append(scheduling_target)

        if len(subject_ids) != 1:
            raise ValueError(
                f"Занятие id={lesson.id} связано "
                "с несколькими учебными предметами."
            )

        result.append(
            SchedulingLesson(
                lesson_id=lesson.id,
                lesson_type=lesson.lesson_type,
                hours=lesson.hours,
                subject_id=next(iter(subject_ids)),
                targets=tuple(targets),
            )
        )

    return result


def _build_scheduling_target(
    target: LessonTarget,
) -> SchedulingTarget:
    assignment = target.teacher_assignment

    if assignment is None:
        raise ValueError(
            f"Для LessonTarget id={target.id} "
            f"не найден TeacherAssignment "
            f"id={target.teacher_assignment_id}."
        )

    if assignment.teacher_load is None:
        raise ValueError(
            f"Для TeacherAssignment id={assignment.id} "
            "не найден TeacherLoad."
        )

    teacher_id = assignment.teacher_load.teacher_id

    if target.target_type == "full_group":
        if target.group is None:
            raise ValueError(
                f"LessonTarget id={target.id}: "
                "не найдена группа."
            )

        return SchedulingTarget(
            target_type="full_group",
            target_id=target.group_id,
            lesson_target_id=target.id,
            student_count=target.group.student_count,
            teacher_id=teacher_id,
            teacher_assignment_id=target.teacher_assignment_id,
            resource_keys=(("group", target.group_id),),
            student_ids=tuple(
                sorted(student.id for student in target.group.students)
            ),
        )

    if target.target_type == "subgroup":
        if target.subgroup is None:
            raise ValueError(
                f"LessonTarget id={target.id}: "
                "не найдена подгруппа."
            )

        return SchedulingTarget(
            target_type="subgroup",
            target_id=target.subgroup_id,
            lesson_target_id=target.id,
            student_count=target.subgroup.student_count,
            teacher_id=teacher_id,
            teacher_assignment_id=target.teacher_assignment_id,
            resource_keys=(("subgroup", target.subgroup_id),),
            student_ids=tuple(
                sorted(student.student_id for student in target.subgroup.students)
            ),
        )

    if target.target_type == "lecture_part":
        if target.lecture_part is None:
            raise ValueError(
                f"LessonTarget id={target.id}: "
                "не найдена лекционная часть."
            )

        return SchedulingTarget(
            target_type="lecture_part",
            target_id=target.lecture_part_id,
            lesson_target_id=target.id,
            student_count=target.lecture_part.student_count,
            teacher_id=teacher_id,
            teacher_assignment_id=target.teacher_assignment_id,
            resource_keys=(("lecture_part", target.lecture_part_id),),
            student_ids=tuple(
                sorted(
                    student.student_id
                    for student in target.lecture_part.students
                )
            ),
        )

    if target.target_type == "subgroup_bundle":
        if target.subgroup_bundle is None:
            raise ValueError(
                f"LessonTarget id={target.id}: "
                "не найдено объединение подгрупп."
            )
        bundle = target.subgroup_bundle
        resource_keys = {
            ("subgroup", member.subgroup_id)
            for member in bundle.members
        }

        return SchedulingTarget(
            target_type="subgroup_bundle",
            target_id=bundle.id,
            lesson_target_id=target.id,
            student_count=bundle.student_count,
            teacher_id=teacher_id,
            teacher_assignment_id=target.teacher_assignment_id,
            resource_keys=tuple(sorted(resource_keys)),
            student_ids=tuple(
                sorted(
                    {
                        student.student_id
                        for member in bundle.members
                        for student in member.subgroup.students
                    }
                )
            ),
        )

    raise ValueError(
        f"LessonTarget id={target.id}: "
        f"неизвестный target_type={target.target_type}."
    )


def _load_time_slots(
    db: Session,
) -> list[SchedulingTimeSlot]:
    slots = (
        db.query(TimeSlot)
        .filter(
            TimeSlot.is_active.is_(True),
        )
        .order_by(
            TimeSlot.day_of_week,
            TimeSlot.lesson_number,
        )
        .all()
    )

    return [
        SchedulingTimeSlot(
            time_slot_id=slot.id,
            day_of_week=slot.day_of_week,
            lesson_number=slot.lesson_number,
            start_time=slot.start_time,
            end_time=slot.end_time,
        )
        for slot in slots
    ]


def _load_classrooms(
    db: Session,
) -> list[SchedulingClassroom]:
    classrooms = (
        db.query(Classroom)
        .filter(
            Classroom.is_active.is_(True),
        )
        .order_by(
            Classroom.id,
        )
        .all()
    )

    return [
        SchedulingClassroom(
            classroom_id=classroom.id,
            name=classroom.name,
            capacity=classroom.capacity,
            room_type=classroom.room_type,
            equipment=classroom.equipment,
        )
        for classroom in classrooms
    ]
