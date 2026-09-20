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
    - группа/подгруппа не может посещать два занятия одновременно;
    - аудитория не может использоваться двумя target одновременно;
    - два target одного занятия не могут использовать одну аудиторию.

    После успешной базовой генерации можно добавлять дополнительные
    soft constraints и оптимизацию окон.
    """

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

        self._add_classroom_conflicts()

        print("[Scheduler] OK: ограничения аудиторий")

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
            raise ValueError(
                "OR-Tools не смог построить допустимое расписание. "
                f"Статус solver: {solver.StatusName(status)}."
            )

        # --------------------------------------------------------
        # 7. Извлечение решения
        # --------------------------------------------------------
        placements = self._extract_solution()

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
        Пока НЕ вызывается в generate().

        Оставлено для следующего этапа, когда базовая
        выполнимость будет подтверждена.

        Приоритеты будущей оптимизации:

        1. уменьшение количества рабочих дней;
        2. уменьшение окон;
        3. уменьшение поздних пар;
        4. более равномерное распределение нагрузки.
        """

        assert self.data is not None

        objective_terms = []

        # --------------------------------------------------------
        # 1. Поздние пары
        # --------------------------------------------------------

        for lesson in self.data.lessons:

            for slot in self.data.time_slots:

                slot_number = slot.lesson_number

                if slot_number >= 7:
                    penalty = 120
                elif slot_number >= 6:
                    penalty = 80
                elif slot_number >= 5:
                    penalty = 35
                elif slot_number >= 4:
                    penalty = 10
                else:
                    penalty = 0

                if penalty > 0:

                    objective_terms.append(
                        penalty
                        * self.lesson_slot_bool[
                            (
                                lesson.lesson_id,
                                slot.time_slot_id,
                            )
                        ]
                    )

        # --------------------------------------------------------
        # 2. Суббота
        # --------------------------------------------------------

        for lesson in self.data.lessons:

            for slot in self.data.time_slots:

                if slot.day_of_week == 6:

                    objective_terms.append(
                        80
                        * self.lesson_slot_bool[
                            (
                                lesson.lesson_id,
                                slot.time_slot_id,
                            )
                        ]
                    )

        # --------------------------------------------------------
        # 3. Окна
        # --------------------------------------------------------

        objective_terms.extend(
            self._build_gap_penalties()
        )

        if objective_terms:
            self.model.Minimize(
                sum(objective_terms)
            )

    # ============================================================
    # GAP PENALTIES
    # ============================================================

    def _build_gap_penalties(self):
        assert self.data is not None

        penalties = []

        resources: dict[
            tuple[str, int],
            set[int],
        ] = defaultdict(set)

        for lesson in self.data.lessons:

            for target in lesson.targets:

                resources[
                    (
                        target.target_type,
                        target.target_id,
                    )
                ].add(
                    lesson.lesson_id
                )

        for resource_key, lesson_ids in (
            resources.items()
        ):

            lesson_ids_list = sorted(
                lesson_ids
            )

            if len(lesson_ids_list) < 2:
                continue

            for day_of_week, slot_ids in (
                self.day_slots.items()
            ):

                if len(slot_ids) < 3:
                    continue

                for first_index in range(
                    len(slot_ids)
                ):

                    first_slot_id = (
                        slot_ids[first_index]
                    )

                    for second_index in range(
                        first_index + 2,
                        len(slot_ids),
                    ):

                        second_slot_id = (
                            slot_ids[second_index]
                        )

                        distance = (
                            second_index
                            - first_index
                        )

                        gap_size = distance - 1

                        if gap_size == 1:
                            penalty = 8
                        elif gap_size == 2:
                            penalty = 30
                        elif gap_size == 3:
                            penalty = 70
                        else:
                            penalty = 120

                        # ------------------------------------------------
                        # Используется ли ресурс в первом слоте?
                        # ------------------------------------------------

                        first_variables = [
                            self.lesson_slot_bool[
                                (
                                    lesson_id,
                                    first_slot_id,
                                )
                            ]
                            for lesson_id in lesson_ids_list
                        ]

                        first_day_used = (
                            self.model.NewBoolVar(
                                (
                                    f"resource_"
                                    f"{resource_key[0]}_"
                                    f"{resource_key[1]}_"
                                    f"day_{day_of_week}_"
                                    f"slot_{first_slot_id}"
                                )
                            )
                        )

                        self.model.Add(
                            first_day_used
                            == cp_model.LinearExpr.Sum(
                                first_variables
                            )
                        )

                        # ------------------------------------------------
                        # Используется ли ресурс во втором слоте?
                        # ------------------------------------------------

                        second_variables = [
                            self.lesson_slot_bool[
                                (
                                    lesson_id,
                                    second_slot_id,
                                )
                            ]
                            for lesson_id in lesson_ids_list
                        ]

                        second_day_used = (
                            self.model.NewBoolVar(
                                (
                                    f"resource_"
                                    f"{resource_key[0]}_"
                                    f"{resource_key[1]}_"
                                    f"day_{day_of_week}_"
                                    f"slot_{second_slot_id}"
                                )
                            )
                        )

                        self.model.Add(
                            second_day_used
                            == cp_model.LinearExpr.Sum(
                                second_variables
                            )
                        )

                        # ------------------------------------------------
                        # Окно
                        # ------------------------------------------------

                        gap_variable = (
                            self.model.NewBoolVar(
                                (
                                    f"gap_"
                                    f"{resource_key[0]}_"
                                    f"{resource_key[1]}_"
                                    f"{day_of_week}_"
                                    f"{first_slot_id}_"
                                    f"{second_slot_id}"
                                )
                            )
                        )

                        self.model.Add(
                            gap_variable
                            >= (
                                first_day_used
                                + second_day_used
                                - 1
                            )
                        )

                        self.model.Add(
                            gap_variable
                            <= first_day_used
                        )

                        self.model.Add(
                            gap_variable
                            <= second_day_used
                        )

                        penalties.append(
                            penalty
                            * gap_variable
                        )

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

        lesson_ids = [
            placement.lesson_id
            for placement in placement_list
        ]

        # --------------------------------------------------------
        # Сбрасываем старые аудитории
        # --------------------------------------------------------

        if lesson_ids:

            self.db.query(
                LessonTarget
            ).filter(
                LessonTarget.lesson_id.in_(
                    lesson_ids
                )
            ).update(
                {
                    LessonTarget.classroom_id: None,
                },
                synchronize_session=False,
            )

        # --------------------------------------------------------
        # Сохраняем расписание
        # --------------------------------------------------------

        for placement in placement_list:

            schedule_item = ScheduleItem(
                schedule_version_id=version.id,
                lesson_id=placement.lesson_id,
                time_slot_id=placement.time_slot_id,
            )

            self.db.add(
                schedule_item
            )

            # ----------------------------------------------------
            # Сохраняем аудитории targets
            # ----------------------------------------------------

            for (
                target_id,
                classroom_id,
            ) in placement.classroom_by_target.items():

                target = (
                    self.db.query(
                        LessonTarget
                    )
                    .filter(
                        LessonTarget.id
                        == target_id,

                        LessonTarget.lesson_id
                        == placement.lesson_id,
                    )
                    .first()
                )

                if target is None:
                    raise ValueError(
                        f"LessonTarget "
                        f"id={target_id} "
                        f"для Lesson "
                        f"#{placement.lesson_id} "
                        "не найден."
                    )

                target.classroom_id = (
                    classroom_id
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