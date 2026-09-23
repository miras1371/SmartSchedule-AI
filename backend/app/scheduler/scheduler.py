from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from ortools.sat.python import cp_model
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.academic_period import AcademicPeriod
from backend.app.models.lesson_target import LessonTarget
from backend.app.models.schedule_item import ScheduleItem
from backend.app.models.schedule_item_classroom import ScheduleItemClassroom
from backend.app.models.schedule_version import ScheduleVersion
from backend.app.scheduler.data_loader import (
    SchedulingData,
    SchedulingLesson,
    SchedulingTarget,
    load_scheduling_data,
)


@dataclass(frozen=True)
class LessonPlacement:
    lesson_id: int
    time_slot_id: int
    classroom_by_target: dict[int, int]


class ScheduleGenerator:
    """
    OR-Tools генератор расписания.

    Математическая модель:

        Lesson
            |
            +-- ровно один TimeSlot
            |
            +-- для каждого Target:
                    ровно одна Classroom
                    в выбранном TimeSlot

    Жёсткие ограничения:
    - каждое занятие получает ровно один слот;
    - каждый target получает ровно одну аудиторию;
    - аудитория соответствует вместимости;
    - лаборатория проводится только в computer_lab;
    - преподаватель не может вести два занятия одновременно;
    - студент не может посещать два занятия одновременно;
    - у студента не может быть больше 6 занятий в день;
    - группа/подгруппа не может посещать два занятия одновременно;
    - аудитория не может использоваться двумя занятиями одновременно;
    - цели лекции находятся вместе, цели практики/лабораторной — раздельно.

    Время занятий и аудитории оптимизируются последовательно: сначала
    удобство студентов, затем заполненность и баланс помещений.
    """

    MAX_STUDENT_LESSONS_PER_DAY = 6


    def __init__(
        self,
        db: Session,
        academic_period_id: int,
    ) -> None:
        self.db = db
        self.academic_period_id = academic_period_id

        self.data: SchedulingData | None = None
        self.model = cp_model.CpModel()

        # --------------------------------------------------------
        # Lesson -> Slot
        # --------------------------------------------------------
        self.lesson_slot_bool: dict[
            tuple[int, int],
            cp_model.IntVar,
        ] = {}

        # --------------------------------------------------------
        # Lesson + Target + Slot + Classroom
        #
        # ВАЖНО:
        # slot_id является частью ключа.
        # Именно этого не хватало в предыдущей версии.
        # --------------------------------------------------------
        self.lesson_target_classroom_bool: dict[
            tuple[int, int, int, int],
            cp_model.IntVar,
        ] = {}

        self.lesson_by_id: dict[int, SchedulingLesson] = {}
        self.slot_by_id = {}
        self.classroom_by_id = {}

        self.target_resource_key: dict[
            tuple[int, int],
            tuple[str, int],
        ] = {}

        self.teacher_lessons: dict[
            int,
            list[int],
        ] = defaultdict(list)

        self.resource_lessons: dict[
            tuple[str, int],
            list[int],
        ] = defaultdict(list)

        self.student_lessons: dict[int, list[int]] = defaultdict(list)

        self.slot_day: dict[int, int] = {}
        self.slot_number: dict[int, int] = {}
        self.day_slots: dict[int, list[int]] = defaultdict(list)

        self.solver: cp_model.CpSolver | None = None

    # ============================================================
    # PUBLIC API
    # ============================================================

    def generate(self) -> ScheduleVersion:
        print(
            f"[Scheduler] Начало генерации "
            f"для academic_period_id={self.academic_period_id}"
        )

        # --------------------------------------------------------
        # 1. Загрузка данных
        # --------------------------------------------------------
        self.data = load_scheduling_data(
            self.db,
            academic_period_id=self.academic_period_id,
        )

        # --------------------------------------------------------
        # 2. Индексы
        # --------------------------------------------------------
        self._prepare_indexes()

        # --------------------------------------------------------
        # 3. Проверка входных данных
        # --------------------------------------------------------
        self._validate_input_data()

        self._create_variables()

        print("[Scheduler] Проверка базовой модели...")

        self._add_each_lesson_exactly_one_slot()

        print("[Scheduler] OK: каждое занятие получает один слот")

        self._add_each_target_exactly_one_classroom()

        print("[Scheduler] OK: аудитории назначаются")

        self._add_teacher_conflicts()

        print("[Scheduler] OK: ограничения преподавателей")

        self._add_group_and_subgroup_conflicts()

        print("[Scheduler] OK: ограничения групп/подгрупп")

        self._add_student_conflicts_and_daily_limit()

        print("[Scheduler] OK: ограничения студентов и дневной лимит")

        self._add_classroom_conflicts()

        print("[Scheduler] OK: ограничения аудиторий")

        # Hard constraints are complete at this point; only then apply
        # the deterministic soft objective to choose the better solution.
        self._add_objective()

        print(
            f"[Scheduler] Занятий: {len(self.data.lessons)}"
        )
        print(
            f"[Scheduler] Слотов: {len(self.data.time_slots)}"
        )
        print(
            f"[Scheduler] Аудиторий: {len(self.data.classrooms)}"
        )

        # --------------------------------------------------------
        # 6. OR-Tools
        #
        # Пока сначала проверяем базовую выполнимость.
        # Это важно для диагностики.
        # --------------------------------------------------------
        solver = cp_model.CpSolver()

        solver.parameters.max_time_in_seconds = 60.0
        solver.parameters.num_search_workers = 8
        solver.parameters.log_search_progress = False

        self.solver = solver

        status = solver.Solve(self.model)

        print(
            f"[Scheduler] Статус OR-Tools: "
            f"{solver.StatusName(status)}"
        )

        if status not in (
            cp_model.OPTIMAL,
            cp_model.FEASIBLE,
        ):
            explanation = (
                "Проверьте доступные временные слоты, конфликты "
                "преподавателей/групп и подходящие аудитории."
            )
            raise ValueError(
                "OR-Tools не смог построить допустимое расписание. "
                f"Статус solver: {solver.StatusName(status)}. "
                f"{explanation}"
            )

        # --------------------------------------------------------
        # 7. Извлечение решения
        # --------------------------------------------------------
        placements = self._extract_solution()

        # Classroom choice is optimized only after lesson times are fixed.
        # This keeps room efficiency from competing with student convenience
        # during the much larger timetable search.
        placements = self._optimize_classroom_assignments(placements)

        # --------------------------------------------------------
        # 8. Сохранение
        # --------------------------------------------------------
        version = self._save_schedule(
            placements=placements,
            status="generated",
        )

        print(
            f"[Scheduler] Расписание сохранено: "
            f"version_id={version.id}"
        )

        return version

    # ============================================================
    # PREPARATION
    # ============================================================

    def _prepare_indexes(self) -> None:
        assert self.data is not None

        self.lesson_by_id = {
            lesson.lesson_id: lesson
            for lesson in self.data.lessons
        }

        self.slot_by_id = {
            slot.time_slot_id: slot
            for slot in self.data.time_slots
        }

        self.classroom_by_id = {
            classroom.classroom_id: classroom
            for classroom in self.data.classrooms
        }

        self.slot_day = {
            slot.time_slot_id: slot.day_of_week
            for slot in self.data.time_slots
        }

        self.slot_number = {
            slot.time_slot_id: slot.lesson_number
            for slot in self.data.time_slots
        }

        self.day_slots = defaultdict(list)

        for slot in self.data.time_slots:
            self.day_slots[
                slot.day_of_week
            ].append(
                slot.time_slot_id
            )

        for slots in self.day_slots.values():
            slots.sort(
                key=lambda slot_id: self.slot_number[slot_id]
            )

        # --------------------------------------------------------
        # Индексы преподавателей и ресурсов
        # --------------------------------------------------------

        self.teacher_lessons = defaultdict(list)
        self.resource_lessons = defaultdict(list)
        self.student_lessons = defaultdict(list)
        self.target_resource_key = {}

        for lesson in self.data.lessons:
            for target in lesson.targets:

                resource_keys = target.resource_keys

                self.target_resource_key[
                    (
                        lesson.lesson_id,
                        target.target_id,
                    )
                ] = resource_keys[0]

                for resource_key in resource_keys:
                    self.resource_lessons[
                        resource_key
                    ].append(
                        lesson.lesson_id
                    )

                self.teacher_lessons[
                    target.teacher_id
                ].append(
                    lesson.lesson_id
                )

                for student_id in target.student_ids:
                    self.student_lessons[student_id].append(
                        lesson.lesson_id
                    )

    # ============================================================
    # INPUT VALIDATION
    # ============================================================

    def _validate_input_data(self) -> None:
        assert self.data is not None

        if not self.data.lessons:
            raise ValueError(
                "Нет занятий для генерации."
            )

        if not self.data.time_slots:
            raise ValueError(
                "Нет временных слотов для генерации."
            )

        if not self.data.classrooms:
            raise ValueError(
                "Нет активных аудиторий."
            )

        diagnostics: list[str] = []
        slot_count = len(self.data.time_slots)
        lesson_ids_by_teacher: dict[int, set[int]] = defaultdict(set)
        lesson_ids_by_resource: dict[tuple[str, int], set[int]] = defaultdict(set)
        lesson_ids_by_student: dict[int, set[int]] = defaultdict(set)

        for lesson in self.data.lessons:

            if lesson.hours <= 0:
                raise ValueError(
                    f"Lesson #{lesson.lesson_id}: "
                    "количество часов должно быть больше нуля."
                )

            if not lesson.targets:
                raise ValueError(
                    f"Lesson #{lesson.lesson_id}: "
                    "нет целей занятия."
                )

            target_ids = set()

            for target in lesson.targets:

                if target.target_id in target_ids:
                    raise ValueError(
                        f"Lesson #{lesson.lesson_id}: "
                        f"цель id={target.target_id} "
                        "указана несколько раз."
                    )

                target_ids.add(target.target_id)

                if target.student_count <= 0:
                    raise ValueError(
                        f"Lesson #{lesson.lesson_id}: "
                        f"цель id={target.target_id} "
                        "имеет некорректное количество студентов."
                    )

                if not target.student_ids:
                    raise ValueError(
                        f"Lesson #{lesson.lesson_id}: "
                        f"цель id={target.target_id} не содержит студентов."
                    )

                if target.teacher_id <= 0:
                    raise ValueError(
                        f"Lesson #{lesson.lesson_id}: "
                        f"цель id={target.target_id} "
                        "имеет некорректного преподавателя."
                    )

                lesson_ids_by_teacher[target.teacher_id].add(
                    lesson.lesson_id
                )
                for resource_key in target.resource_keys:
                    lesson_ids_by_resource[resource_key].add(
                        lesson.lesson_id
                    )
                for student_id in target.student_ids:
                    lesson_ids_by_student[student_id].add(
                        lesson.lesson_id
                    )

                valid_classrooms = self._get_valid_classrooms(
                    lesson=lesson,
                    target=target,
                )
                if not valid_classrooms:
                    diagnostics.append(
                        f"занятие #{lesson.lesson_id}, цель "
                        f"#{target.lesson_target_id}: нет подходящей "
                        "аудитории по типу или вместимости"
                    )

            if lesson.lesson_type not in {
                "lecture",
                "practice",
                "lab",
            }:
                raise ValueError(
                    f"Lesson #{lesson.lesson_id}: "
                    f"неизвестный тип занятия "
                    f"{lesson.lesson_type!r}."
                )

        for classroom in self.data.classrooms:

            if classroom.capacity <= 0:
                raise ValueError(
                    f"Аудитория {classroom.name}: "
                    "вместимость должна быть больше нуля."
                )

        for teacher_id, lesson_ids in lesson_ids_by_teacher.items():
            if len(lesson_ids) > slot_count:
                diagnostics.append(
                    f"преподаватель #{teacher_id} имеет "
                    f"{len(lesson_ids)} занятий, но доступно только "
                    f"{slot_count} временных слотов"
                )

        for resource_key, lesson_ids in lesson_ids_by_resource.items():
            if len(lesson_ids) > slot_count:
                diagnostics.append(
                    f"ресурс {resource_key[0]}:{resource_key[1]} имеет "
                    f"{len(lesson_ids)} занятий, но доступно только "
                    f"{slot_count} временных слотов"
                )

        daily_capacity = (
            len(self.day_slots) * self.MAX_STUDENT_LESSONS_PER_DAY
        )
        for student_id, lesson_ids in lesson_ids_by_student.items():
            if len(lesson_ids) > daily_capacity:
                diagnostics.append(
                    f"студент #{student_id} имеет {len(lesson_ids)} занятий, "
                    f"но при лимите {self.MAX_STUDENT_LESSONS_PER_DAY} в день "
                    f"можно разместить только {daily_capacity}"
                )

        if diagnostics:
            details = "; ".join(diagnostics[:10])
            if len(diagnostics) > 10:
                details += f"; и ещё {len(diagnostics) - 10} проблем"
            raise ValueError(
                "Предварительная диагностика расписания выявила "
                f"невыполнимые ограничения: {details}."
            )

    # ============================================================
    # VARIABLES
    # ============================================================

    def _create_variables(self) -> None:
        assert self.data is not None

        slot_ids = [
            slot.time_slot_id
            for slot in self.data.time_slots
        ]

        for lesson in self.data.lessons:

            lesson_id = lesson.lesson_id

            # ----------------------------------------------------
            # Lesson -> Slot
            # ----------------------------------------------------

            for slot_id in slot_ids:

                variable = self.model.NewBoolVar(
                    f"lesson_{lesson_id}_slot_{slot_id}"
                )

                self.lesson_slot_bool[
                    (
                        lesson_id,
                        slot_id,
                    )
                ] = variable

            # ----------------------------------------------------
            # Lesson + Target + Slot + Classroom
            # ----------------------------------------------------

            for target in lesson.targets:

                valid_classrooms = (
                    self._get_valid_classrooms(
                        lesson=lesson,
                        target=target,
                    )
                )

                if not valid_classrooms:
                    raise ValueError(
                        f"Lesson #{lesson_id}, "
                        f"target #{target.target_id}: "
                        "не найдена подходящая аудитория."
                    )

                for slot_id in slot_ids:

                    for classroom_id in valid_classrooms:

                        variable = self.model.NewBoolVar(
                            (
                                f"lesson_{lesson_id}_"
                                f"target_{target.target_id}_"
                                f"slot_{slot_id}_"
                                f"room_{classroom_id}"
                            )
                        )

                        self.lesson_target_classroom_bool[
                            (
                                lesson_id,
                                target.target_id,
                                slot_id,
                                classroom_id,
                            )
                        ] = variable

    # ============================================================
    # CLASSROOM VALIDATION
    # ============================================================

    def _get_valid_classrooms(
        self,
        lesson: SchedulingLesson,
        target: SchedulingTarget,
    ) -> list[int]:
        assert self.data is not None

        result: list[int] = []

        # Для лекции все targets находятся в одной аудитории,
        # поэтому аудитория должна вместить всех студентов лекции.
        if lesson.lesson_type == "lecture":
            required_capacity = sum(
                lesson_target.student_count
                for lesson_target in lesson.targets
            )
        else:
            # Для практики/лаборатории каждый target
            # получает отдельную аудиторию.
            required_capacity = target.student_count

        for classroom in self.data.classrooms:

            # Вместимость
            if classroom.capacity < required_capacity:
                continue

            # Лаборатории только в компьютерных аудиториях
            if lesson.lesson_type == "lab":
                if classroom.room_type != "computer_lab":
                    continue

            result.append(classroom.classroom_id)

        return result

    # ============================================================
    # HARD CONSTRAINTS
    # ============================================================

    def _add_hard_constraints(self) -> None:

        # 1. Каждое занятие ровно в одном слоте
        self._add_each_lesson_exactly_one_slot()

        # 2. Каждый target получает ровно одну аудиторию
        #    в выбранном слоте
        self._add_each_target_exactly_one_classroom()

        # 3. Преподаватель не может вести два занятия одновременно
        self._add_teacher_conflicts()

        # 4. Группа/подгруппа не может посещать два занятия
        #    одновременно
        self._add_group_and_subgroup_conflicts()

        # 5. Одна аудитория не может использоваться
        #    двумя target одновременно
        self._add_classroom_conflicts()

    # ============================================================
    # LESSON -> SLOT
    # ============================================================

    def _add_each_lesson_exactly_one_slot(self) -> None:
        assert self.data is not None

        for lesson in self.data.lessons:

            variables = [
                self.lesson_slot_bool[
                    (
                        lesson.lesson_id,
                        slot.time_slot_id,
                    )
                ]
                for slot in self.data.time_slots
            ]

            self.model.AddExactlyOne(
                variables
            )

    # ============================================================
    # TARGET -> CLASSROOM
    # ============================================================

    def _add_each_target_exactly_one_classroom(
        self,
    ) -> None:
        assert self.data is not None

        for lesson in self.data.lessons:
            lesson_id = lesson.lesson_id

            # ---------------------------------------------------------
            # ЛЕКЦИЯ
            #
            # Все targets одной лекции должны находиться
            # в ОДНОЙ и той же аудитории.
            # ---------------------------------------------------------
            if lesson.lesson_type == "lecture":
                if not lesson.targets:
                    continue

                first_target = lesson.targets[0]

                valid_classrooms = self._get_valid_classrooms(
                    lesson=lesson,
                    target=first_target,
                )

                if not valid_classrooms:
                    raise ValueError(
                        f"Lesson #{lesson_id}: "
                        "не найдена подходящая аудитория для лекции."
                    )

                for slot in self.data.time_slots:
                    slot_id = slot.time_slot_id

                    lesson_slot_variable = (
                        self.lesson_slot_bool[
                            (
                                lesson_id,
                                slot_id,
                            )
                        ]
                    )

                    # -------------------------------------------------
                    # Все targets лекции используют одну и ту же
                    # аудиторию.
                    # -------------------------------------------------
                    for classroom_id in valid_classrooms:
                        first_variable = (
                            self.lesson_target_classroom_bool[
                                (
                                    lesson_id,
                                    first_target.target_id,
                                    slot_id,
                                    classroom_id,
                                )
                            ]
                        )

                        for target in lesson.targets[1:]:
                            target_variable = (
                                self.lesson_target_classroom_bool[
                                    (
                                        lesson_id,
                                        target.target_id,
                                        slot_id,
                                        classroom_id,
                                    )
                                ]
                            )

                            self.model.Add(
                                target_variable == first_variable
                            )

                    # -------------------------------------------------
                    # Если занятие выбрано в этом слоте,
                    # должна быть выбрана ровно одна аудитория.
                    #
                    # Если слот не выбран -> аудитория не выбрана.
                    # -------------------------------------------------
                    first_target_variables = [
                        self.lesson_target_classroom_bool[
                            (
                                lesson_id,
                                first_target.target_id,
                                slot_id,
                                classroom_id,
                            )
                        ]
                        for classroom_id in valid_classrooms
                    ]

                    self.model.Add(
                        cp_model.LinearExpr.Sum(
                            first_target_variables
                        )
                        == lesson_slot_variable
                    )

            # ---------------------------------------------------------
            # ПРАКТИКА / ЛАБОРАТОРИЯ
            #
            # Каждый target может иметь отдельную аудиторию.
            # ---------------------------------------------------------
            else:
                for target in lesson.targets:
                    target_id = target.target_id

                    valid_classrooms = (
                        self._get_valid_classrooms(
                            lesson=lesson,
                            target=target,
                        )
                    )

                    if not valid_classrooms:
                        raise ValueError(
                            f"Lesson #{lesson_id}, "
                            f"target #{target_id}: "
                            "не найдена подходящая аудитория."
                        )

                    for slot in self.data.time_slots:
                        slot_id = slot.time_slot_id

                        lesson_slot_variable = (
                            self.lesson_slot_bool[
                                (
                                    lesson_id,
                                    slot_id,
                                )
                            ]
                        )

                        classroom_variables = [
                            self.lesson_target_classroom_bool[
                                (
                                    lesson_id,
                                    target_id,
                                    slot_id,
                                    classroom_id,
                                )
                            ]
                            for classroom_id in valid_classrooms
                        ]

                        # Если lesson выбран в этом слоте,
                        # target получает ровно одну аудиторию.
                        self.model.Add(
                            cp_model.LinearExpr.Sum(
                                classroom_variables
                            )
                            == lesson_slot_variable
                        )

    # ============================================================
    # TEACHER CONFLICTS
    # ============================================================

    def _add_teacher_conflicts(self) -> None:
        assert self.data is not None

        lessons_by_teacher: dict[
            int,
            set[int],
        ] = defaultdict(set)

        for lesson in self.data.lessons:

            for target in lesson.targets:

                lessons_by_teacher[
                    target.teacher_id
                ].add(
                    lesson.lesson_id
                )

        for teacher_id, lesson_ids in (
            lessons_by_teacher.items()
        ):

            lesson_ids_list = sorted(
                lesson_ids
            )

            for slot in self.data.time_slots:

                variables = [
                    self.lesson_slot_bool[
                        (
                            lesson_id,
                            slot.time_slot_id,
                        )
                    ]
                    for lesson_id in lesson_ids_list
                ]

                if variables:
                    self.model.Add(
                        sum(variables) <= 1
                    )

    # ============================================================
    # GROUP / SUBGROUP CONFLICTS
    # ============================================================

    def _add_group_and_subgroup_conflicts(
        self,
    ) -> None:
        assert self.data is not None

        resources: dict[
            tuple[str, int],
            set[int],
        ] = defaultdict(set)

        for lesson in self.data.lessons:

            for target in lesson.targets:

                for resource_key in target.resource_keys:
                    resources[resource_key].add(
                        lesson.lesson_id
                    )

        for resource_key, lesson_ids in (
            resources.items()
        ):

            lesson_ids_list = sorted(
                lesson_ids
            )

            for slot in self.data.time_slots:

                variables = [
                    self.lesson_slot_bool[
                        (
                            lesson_id,
                            slot.time_slot_id,
                        )
                    ]
                    for lesson_id in lesson_ids_list
                ]

                if variables:
                    self.model.Add(
                        sum(variables) <= 1
                    )

    def _student_lesson_cohorts(
        self,
    ) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
        """Group students with identical lesson sets to keep CP-SAT compact."""
        students_by_lessons: dict[tuple[int, ...], list[int]] = defaultdict(list)
        for student_id, lesson_ids in self.student_lessons.items():
            key = tuple(sorted(set(lesson_ids)))
            if key:
                students_by_lessons[key].append(student_id)
        return [
            (tuple(sorted(student_ids)), lesson_ids)
            for lesson_ids, student_ids in sorted(students_by_lessons.items())
        ]

    def _add_student_conflicts_and_daily_limit(self) -> None:
        """Prevent individual clashes and cap every student's day at 6 lessons."""
        assert self.data is not None

        for _, lesson_ids in self._student_lesson_cohorts():
            for slot in self.data.time_slots:
                self.model.Add(
                    sum(
                        self.lesson_slot_bool[(lesson_id, slot.time_slot_id)]
                        for lesson_id in lesson_ids
                    )
                    <= 1
                )

            for slot_ids in self.day_slots.values():
                self.model.Add(
                    sum(
                        self.lesson_slot_bool[(lesson_id, slot_id)]
                        for lesson_id in lesson_ids
                        for slot_id in slot_ids
                    )
                    <= self.MAX_STUDENT_LESSONS_PER_DAY
                )

    # ============================================================
    # CLASSROOM CONFLICTS
    # ============================================================

    def _add_classroom_conflicts(self) -> None:
        """
        Одна аудитория может использоваться только одним занятием
        в одном временном слоте.

        Важно:
        лекция может иметь несколько targets, но все они используют
        одну и ту же аудиторию. Поэтому для лекции аудитория считается
        занятой один раз на уровне lesson, а не отдельно для каждого target.
        """

        assert self.data is not None

        for slot in self.data.time_slots:

            slot_id = slot.time_slot_id

            for classroom in self.data.classrooms:

                classroom_id = classroom.classroom_id

                variables = []

                for lesson in self.data.lessons:

                    # ------------------------------------------------
                    # ЛЕКЦИЯ
                    # ------------------------------------------------
                    #
                    # У лекции несколько targets могут находиться
                    # в одной аудитории одновременно.
                    #
                    # Поэтому добавляем только первый target.
                    #
                    if lesson.lesson_type == "lecture":

                        if not lesson.targets:
                            continue

                        first_target = lesson.targets[0]

                        key = (
                            lesson.lesson_id,
                            first_target.target_id,
                            slot_id,
                            classroom_id,
                        )

                        variable = (
                            self.lesson_target_classroom_bool.get(
                                key
                            )
                        )

                        if variable is not None:
                            variables.append(variable)

                    # ------------------------------------------------
                    # ПРАКТИКА / ЛАБОРАТОРНАЯ
                    # ------------------------------------------------
                    #
                    # Каждый target может занимать отдельную
                    # аудиторию, поэтому здесь учитываем каждый target.
                    #
                    else:

                        for target in lesson.targets:

                            key = (
                                lesson.lesson_id,
                                target.target_id,
                                slot_id,
                                classroom_id,
                            )

                            variable = (
                                self.lesson_target_classroom_bool.get(
                                    key
                                )
                            )

                            if variable is not None:
                                variables.append(variable)

                if variables:
                    self.model.Add(
                        sum(variables) <= 1
                    )
    # ============================================================
    # OBJECTIVE
    # ============================================================

    def _add_objective(self) -> None:
        """
        Выбирает более удобное из допустимых расписаний.

        Жёсткие ограничения добавляются до objective, поэтому оптимизация
        не может заменить проверку конфликтов или вместимости.
        """

        assert self.data is not None

        student_objective_terms = []
        student_count_by_lesson: dict[int, int] = defaultdict(int)
        for lesson_ids in self.student_lessons.values():
            for lesson_id in set(lesson_ids):
                student_count_by_lesson[lesson_id] += 1

        # Penalize late lessons per affected student, not per database row.
        late_penalties = {
            4: 2,
            5: 6,
            6: 15,
            7: 35,
            8: 65,
            9: 100,
            10: 150,
            11: 210,
            12: 280,
            13: 360,
        }
        for lesson in self.data.lessons:
            affected_students = student_count_by_lesson[lesson.lesson_id]
            for slot in self.data.time_slots:
                penalty = late_penalties.get(slot.lesson_number, 0)
                if penalty:
                    student_objective_terms.append(
                        penalty
                        * affected_students
                        * self.lesson_slot_bool[
                            (lesson.lesson_id, slot.time_slot_id)
                        ]
                    )

        # Real student gaps have the highest priority. Day-use and sixth-
        # lesson penalties then compact the week without creating overloads.
        student_objective_terms.extend(
            self._build_student_quality_penalties()
        )

        student_objective = (
            cp_model.LinearExpr.Sum(student_objective_terms)
            if student_objective_terms
            else 0
        )
        self.model.Minimize(student_objective)

    def _optimize_classroom_assignments(
        self,
        placements: Iterable[LessonPlacement],
    ) -> list[LessonPlacement]:
        """Optimize rooms with lesson times fixed by the main solver."""
        assert self.data is not None

        placement_list = list(placements)
        slot_by_lesson = {
            placement.lesson_id: placement.time_slot_id
            for placement in placement_list
        }
        room_model = cp_model.CpModel()
        event_variables: dict[
            tuple[int, int],
            cp_model.IntVar,
        ] = {}
        event_targets: dict[int, tuple[int, ...]] = {}
        room_variables: dict[int, list[cp_model.IntVar]] = defaultdict(list)
        slot_room_variables: dict[
            tuple[int, int],
            list[cp_model.IntVar],
        ] = defaultdict(list)
        capacity_waste_terms = []
        event_index = 0

        for lesson in self.data.lessons:
            slot_id = slot_by_lesson[lesson.lesson_id]
            if lesson.lesson_type == "lecture":
                if not lesson.targets:
                    continue
                target = lesson.targets[0]
                required_capacity = sum(
                    item.student_count for item in lesson.targets
                )
                targets = tuple(
                    item.lesson_target_id for item in lesson.targets
                )
                event_specs = ((target, targets, required_capacity),)
            else:
                event_specs = tuple(
                    (
                        target,
                        (target.lesson_target_id,),
                        target.student_count,
                    )
                    for target in lesson.targets
                )

            for target, target_ids, required_capacity in event_specs:
                valid_classrooms = self._get_valid_classrooms(
                    lesson=lesson,
                    target=target,
                )
                event_targets[event_index] = target_ids
                choices = []
                for classroom_id in valid_classrooms:
                    variable = room_model.NewBoolVar(
                        f"event_{event_index}_room_{classroom_id}"
                    )
                    event_variables[(event_index, classroom_id)] = variable
                    choices.append(variable)
                    room_variables[classroom_id].append(variable)
                    slot_room_variables[(slot_id, classroom_id)].append(variable)
                    capacity_waste_terms.append(
                        (
                            self.classroom_by_id[classroom_id].capacity
                            - required_capacity
                        )
                        * variable
                    )
                room_model.Add(cp_model.LinearExpr.Sum(choices) == 1)
                event_index += 1

        for variables in slot_room_variables.values():
            room_model.Add(cp_model.LinearExpr.Sum(variables) <= 1)

        assignment_count = event_index
        usage_variables = []
        for classroom in self.data.classrooms:
            variables = room_variables[classroom.classroom_id]
            usage = room_model.NewIntVar(
                0,
                assignment_count,
                f"room_{classroom.classroom_id}_weekly_usage",
            )
            room_model.Add(
                usage
                == (
                    cp_model.LinearExpr.Sum(variables)
                    if variables
                    else 0
                )
            )
            usage_variables.append(usage)

        max_usage = room_model.NewIntVar(
            0,
            assignment_count,
            "maximum_weekly_room_usage",
        )
        if usage_variables:
            room_model.AddMaxEquality(max_usage, usage_variables)
        else:
            room_model.Add(max_usage == 0)

        # One fewer empty seat is more important than any possible change in
        # the balancing tie-breaker.
        balance_scale = assignment_count + 1
        capacity_waste = (
            cp_model.LinearExpr.Sum(capacity_waste_terms)
            if capacity_waste_terms
            else 0
        )
        room_model.Minimize(balance_scale * capacity_waste + max_usage)

        room_solver = cp_model.CpSolver()
        room_solver.parameters.max_time_in_seconds = 10.0
        room_solver.parameters.num_search_workers = 8
        status = room_solver.Solve(room_model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise ValueError(
                "Не удалось оптимально распределить аудитории для "
                "построенного расписания."
            )

        classrooms_by_lesson: dict[int, dict[int, int]] = defaultdict(dict)
        lesson_by_event: dict[int, int] = {}
        event_index = 0
        for lesson in self.data.lessons:
            event_count = 1 if lesson.lesson_type == "lecture" else len(lesson.targets)
            for _ in range(event_count):
                lesson_by_event[event_index] = lesson.lesson_id
                event_index += 1

        for (current_event, classroom_id), variable in event_variables.items():
            if room_solver.Value(variable) != 1:
                continue
            lesson_id = lesson_by_event[current_event]
            for lesson_target_id in event_targets[current_event]:
                classrooms_by_lesson[lesson_id][lesson_target_id] = classroom_id

        return [
            LessonPlacement(
                lesson_id=placement.lesson_id,
                time_slot_id=placement.time_slot_id,
                classroom_by_target=classrooms_by_lesson[placement.lesson_id],
            )
            for placement in placement_list
        ]

    # ============================================================
    # STUDENT QUALITY PENALTIES
    # ============================================================

    def _build_student_quality_penalties(self):
        assert self.data is not None

        penalties = []

        for cohort_index, (student_ids, lesson_ids) in enumerate(
            self._student_lesson_cohorts()
        ):
            cohort_size = len(student_ids)
            for day_of_week, slot_ids in self.day_slots.items():
                day_variables = [
                    self.lesson_slot_bool[(lesson_id, slot_id)]
                    for lesson_id in lesson_ids
                    for slot_id in slot_ids
                ]
                day_count = cp_model.LinearExpr.Sum(day_variables)

                day_used = self.model.NewBoolVar(
                    f"cohort_{cohort_index}_day_{day_of_week}_used"
                )
                self.model.Add(day_count >= 1).OnlyEnforceIf(day_used)
                self.model.Add(day_count == 0).OnlyEnforceIf(day_used.Not())
                penalties.append(100 * cohort_size * day_used)
                if day_of_week == 6:
                    penalties.append(600 * cohort_size * day_used)

                sixth_lesson = self.model.NewBoolVar(
                    f"cohort_{cohort_index}_day_{day_of_week}_sixth"
                )
                self.model.Add(day_count >= 6).OnlyEnforceIf(sixth_lesson)
                self.model.Add(day_count <= 5).OnlyEnforceIf(
                    sixth_lesson.Not()
                )
                penalties.append(220 * cohort_size * sixth_lesson)

                if len(slot_ids) < 3:
                    continue

                slot_used = []
                for slot_id in slot_ids:
                    occupied = self.model.NewBoolVar(
                        f"cohort_{cohort_index}_slot_{slot_id}_used"
                    )
                    self.model.Add(
                        occupied
                        == sum(
                            self.lesson_slot_bool[(lesson_id, slot_id)]
                            for lesson_id in lesson_ids
                        )
                    )
                    slot_used.append(occupied)

                for index in range(1, len(slot_ids) - 1):
                    has_before = self.model.NewBoolVar(
                        f"cohort_{cohort_index}_slot_{slot_ids[index]}_before"
                    )
                    before = cp_model.LinearExpr.Sum(slot_used[:index])
                    self.model.Add(before >= has_before)
                    self.model.Add(before <= index * has_before)

                    has_after = self.model.NewBoolVar(
                        f"cohort_{cohort_index}_slot_{slot_ids[index]}_after"
                    )
                    after_count = len(slot_ids) - index - 1
                    after = cp_model.LinearExpr.Sum(slot_used[index + 1:])
                    self.model.Add(after >= has_after)
                    self.model.Add(after <= after_count * has_after)

                    gap = self.model.NewBoolVar(
                        f"cohort_{cohort_index}_slot_{slot_ids[index]}_gap"
                    )
                    self.model.Add(gap <= has_before)
                    self.model.Add(gap <= has_after)
                    self.model.Add(gap + slot_used[index] <= 1)
                    self.model.Add(
                        gap
                        >= has_before + has_after - slot_used[index] - 1
                    )
                    penalties.append(1000 * cohort_size * gap)

        return penalties

    # ============================================================
    # SOLUTION EXTRACTION
    # ============================================================

    def _extract_solution(
        self,
    ) -> list[LessonPlacement]:

        assert self.data is not None
        assert self.solver is not None

        placements: list[LessonPlacement] = []

        for lesson in self.data.lessons:

            # ----------------------------------------------------
            # Определяем выбранный слот
            # ----------------------------------------------------

            selected_slot_id: int | None = None

            for slot in self.data.time_slots:

                variable = self.lesson_slot_bool[
                    (
                        lesson.lesson_id,
                        slot.time_slot_id,
                    )
                ]

                if self.solver.Value(variable) == 1:

                    selected_slot_id = (
                        slot.time_slot_id
                    )

                    break

            if selected_slot_id is None:
                raise ValueError(
                    f"Не удалось определить слот "
                    f"для Lesson #{lesson.lesson_id}."
                )

            # ----------------------------------------------------
            # Определяем аудитории targets
            # ----------------------------------------------------

            classrooms: dict[int, int] = {}

            # ---------------------------------------------------------
            # ЛЕКЦИЯ
            #
            # Все targets получают одну и ту же аудиторию.
            # ---------------------------------------------------------
            if lesson.lesson_type == "lecture":

                selected_classroom_id: int | None = None

                # Для лекции все targets должны использовать
                # одну и ту же аудиторию.
                #
                # Проверяем все target-переменные, а не только
                # первый target. Это делает извлечение решения
                # устойчивым к структуре модели.

                for target in lesson.targets:

                    valid_classrooms = self._get_valid_classrooms(
                        lesson=lesson,
                        target=target,
                    )

                    for classroom_id in valid_classrooms:

                        variable = (
                            self.lesson_target_classroom_bool[
                                (
                                    lesson.lesson_id,
                                    target.target_id,
                                    selected_slot_id,
                                    classroom_id,
                                )
                            ]
                        )

                        if self.solver.Value(variable) == 1:
                            selected_classroom_id = classroom_id
                            break

                    if selected_classroom_id is not None:
                        break

                if selected_classroom_id is None:
                    raise ValueError(
                        f"Не удалось определить аудиторию "
                        f"для лекции Lesson #{lesson.lesson_id}, "
                        f"slot #{selected_slot_id}."
                    )

                # Все targets лекции получают одну и ту же аудиторию.
                for target in lesson.targets:
                    classrooms[
                        target.lesson_target_id
                    ] = selected_classroom_id

            # ---------------------------------------------------------
            # ПРАКТИКА / ЛАБОРАТОРИЯ
            # ---------------------------------------------------------
            else:

                for target in lesson.targets:

                    valid_classrooms = (
                        self._get_valid_classrooms(
                            lesson=lesson,
                            target=target,
                        )
                    )

                    selected_classroom_id: int | None = None

                    for classroom_id in valid_classrooms:

                        variable = (
                            self.lesson_target_classroom_bool[
                                (
                                    lesson.lesson_id,
                                    target.target_id,
                                    selected_slot_id,
                                    classroom_id,
                                )
                            ]
                        )

                        if self.solver.Value(variable) == 1:
                            selected_classroom_id = classroom_id
                            break

                    if selected_classroom_id is None:
                        raise ValueError(
                            f"Не удалось определить аудиторию "
                            f"для Lesson #{lesson.lesson_id}, "
                            f"target #{target.target_id}, "
                            f"slot #{selected_slot_id}."
                        )

                    classrooms[target.lesson_target_id] = (
                        selected_classroom_id
                    )

            placements.append(
                LessonPlacement(
                    lesson_id=lesson.lesson_id,
                    time_slot_id=selected_slot_id,
                    classroom_by_target=classrooms,
                )
            )

        return placements

    # ============================================================
    # SAVE
    # ============================================================

    def _save_schedule(
        self,
        placements: Iterable[LessonPlacement],
        status: str,
    ) -> ScheduleVersion:

        # --------------------------------------------------------
        # Проверяем учебный период
        # --------------------------------------------------------

        academic_period_exists = (
            self.db.query(
                AcademicPeriod.id
            )
            .filter(
                AcademicPeriod.id
                == self.academic_period_id,
            )
            .first()
        )

        if academic_period_exists is None:
            raise ValueError(
                f"Учебный период "
                f"id={self.academic_period_id} "
                "не найден."
            )

        # --------------------------------------------------------
        # Следующий номер версии
        # --------------------------------------------------------

        max_version = (
            self.db.query(
                func.max(
                    ScheduleVersion.version_number
                )
            )
            .filter(
                ScheduleVersion.academic_period_id
                == self.academic_period_id,
            )
            .scalar()
        )

        next_version = (
            (max_version or 0)
            + 1
        )

        # --------------------------------------------------------
        # Создание версии
        # --------------------------------------------------------

        version = ScheduleVersion(
            academic_period_id=self.academic_period_id,
            version_number=next_version,
            name=f"Расписание {next_version}",
            status=status,
        )

        self.db.add(version)
        self.db.flush()

        placement_list = list(
            placements
        )

        # --------------------------------------------------------
        # Сохраняем расписание
        # --------------------------------------------------------

        target_ids = [
            target_id
            for placement in placement_list
            for target_id in placement.classroom_by_target
        ]
        targets_by_id = {
            target.id: target
            for target in self.db.query(LessonTarget)
            .filter(LessonTarget.id.in_(target_ids))
            .all()
        } if target_ids else {}

        for placement in placement_list:

            schedule_item = ScheduleItem(
                schedule_version_id=version.id,
                lesson_id=placement.lesson_id,
                time_slot_id=placement.time_slot_id,
            )

            self.db.add(
                schedule_item
            )
            self.db.flush()

            # ----------------------------------------------------
            # Сохраняем аудитории targets
            # ----------------------------------------------------

            for (
                target_id,
                classroom_id,
            ) in placement.classroom_by_target.items():

                target = targets_by_id.get(target_id)

                if target is None or target.lesson_id != placement.lesson_id:
                    raise ValueError(
                        f"LessonTarget "
                        f"id={target_id} "
                        f"для Lesson "
                        f"#{placement.lesson_id} "
                        "не найден."
                    )

                self.db.add(
                    ScheduleItemClassroom(
                        schedule_item_id=schedule_item.id,
                        lesson_target_id=target_id,
                        classroom_id=classroom_id,
                    )
                )

        self.db.commit()

        self.db.refresh(
            version
        )

        return version


# ================================================================
# CONVENIENCE FUNCTION
# ================================================================

def generate_schedule(
    db: Session,
    academic_period_id: int,
) -> ScheduleVersion:
    """
    Удобная функция для вызова генератора из API,
    тестов или других сервисов.
    """

    generator = ScheduleGenerator(
        db=db,
        academic_period_id=academic_period_id,
    )

    return generator.generate()
