import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import jwt
from fastapi import HTTPException
from ortools.sat.python import cp_model

from backend.app.api.schedules import (
    ScheduleGenerateRequest,
    _generation_job_response,
    _item_response,
    _target_group_ids,
    archive_schedule_version,
    get_generation_status,
    publish_schedule_version,
)
from backend.app.api.management import (
    CurriculumSubjectPayload,
    delete_curriculum_subject,
)
from backend.app.api.teacher_loads import (
    delete_teacher_load,
    delete_teacher_load_with_assignments,
)
from backend.app.core.auth import create_access_token, hash_password, verify_password
from backend.app.models.generation_job import GenerationJob
from backend.app.models.user import User
from backend.app.models.schedule_version import ScheduleVersion
from backend.app.scheduler.data_loader import (
    SchedulingClassroom,
    SchedulingData,
    SchedulingLesson,
    SchedulingTarget,
    SchedulingTimeSlot,
)
from backend.app.scheduler.scheduler import LessonPlacement, ScheduleGenerator
from backend.app.services.schedule_validation_service import _target_student_ids


class SchedulerDiagnosticsTests(unittest.TestCase):
    def test_rejects_target_without_compatible_classroom(self):
        target = SchedulingTarget(
            target_type="lab",
            target_id=1,
            lesson_target_id=10,
            student_count=20,
            teacher_id=1,
            teacher_assignment_id=1,
            resource_keys=(("group", 1),),
            student_ids=(1,),
        )
        lesson = SchedulingLesson(
            lesson_id=1,
            lesson_type="lab",
            hours=1,
            subject_id=1,
            targets=(target,),
        )
        data = SchedulingData(
            academic_period_id=1,
            lessons=(lesson,),
            time_slots=(
                SchedulingTimeSlot(
                    time_slot_id=1,
                    day_of_week=1,
                    lesson_number=1,
                    start_time=SimpleNamespace(),
                    end_time=SimpleNamespace(),
                ),
            ),
            classrooms=(
                SchedulingClassroom(
                    classroom_id=1,
                    name="101",
                    capacity=30,
                    room_type="ordinary",
                    equipment=None,
                ),
            ),
        )
        generator = ScheduleGenerator(Mock(), 1)
        generator.data = data
        generator._prepare_indexes()

        with self.assertRaisesRegex(ValueError, "нет подходящей аудитории"):
            generator._validate_input_data()


class SchedulerStudentQualityTests(unittest.TestCase):
    def _generator(self, lesson_count: int, days: int) -> ScheduleGenerator:
        lessons = tuple(
            SchedulingLesson(
                lesson_id=lesson_id,
                lesson_type="practice",
                hours=1,
                subject_id=lesson_id,
                targets=(
                    SchedulingTarget(
                        target_type="full_group",
                        target_id=1,
                        lesson_target_id=lesson_id,
                        student_count=1,
                        teacher_id=lesson_id,
                        teacher_assignment_id=lesson_id,
                        resource_keys=(("group", 1),),
                        student_ids=(1,),
                    ),
                ),
            )
            for lesson_id in range(1, lesson_count + 1)
        )
        slots = tuple(
            SchedulingTimeSlot(
                time_slot_id=(day - 1) * 7 + number,
                day_of_week=day,
                lesson_number=number,
                start_time=SimpleNamespace(),
                end_time=SimpleNamespace(),
            )
            for day in range(1, days + 1)
            for number in range(1, 8)
        )
        data = SchedulingData(
            academic_period_id=1,
            lessons=lessons,
            time_slots=slots,
            classrooms=(
                SchedulingClassroom(
                    classroom_id=1,
                    name="101",
                    capacity=30,
                    room_type="ordinary",
                    equipment=None,
                ),
            ),
        )
        generator = ScheduleGenerator(Mock(), 1)
        generator.data = data
        generator._prepare_indexes()
        generator._create_variables()
        generator._add_each_lesson_exactly_one_slot()
        generator._add_student_conflicts_and_daily_limit()
        return generator

    def test_seven_student_lessons_do_not_fit_into_one_day(self):
        generator = self._generator(lesson_count=7, days=1)
        solver = cp_model.CpSolver()

        self.assertEqual(solver.Solve(generator.model), cp_model.INFEASIBLE)

    def test_student_never_receives_more_than_six_lessons_per_day(self):
        generator = self._generator(lesson_count=7, days=2)
        solver = cp_model.CpSolver()

        self.assertIn(
            solver.Solve(generator.model),
            (cp_model.FEASIBLE, cp_model.OPTIMAL),
        )
        daily_counts = []
        for slot_ids in generator.day_slots.values():
            daily_counts.append(
                sum(
                    solver.Value(generator.lesson_slot_bool[(lesson_id, slot_id)])
                    for lesson_id in range(1, 8)
                    for slot_id in slot_ids
                )
            )
        self.assertLessEqual(max(daily_counts), 6)

    def test_gap_objective_places_lessons_in_adjacent_slots(self):
        generator = self._generator(lesson_count=2, days=1)
        generator._add_objective()
        solver = cp_model.CpSolver()

        self.assertIn(
            solver.Solve(generator.model),
            (cp_model.FEASIBLE, cp_model.OPTIMAL),
        )
        selected = sorted(
            generator.slot_number[slot_id]
            for lesson_id in range(1, 3)
            for slot_id in generator.day_slots[1]
            if solver.Value(generator.lesson_slot_bool[(lesson_id, slot_id)])
        )
        self.assertEqual(selected[1] - selected[0], 1)

    def test_classroom_objective_selects_smallest_suitable_room(self):
        target = SchedulingTarget(
            target_type="full_group",
            target_id=1,
            lesson_target_id=1,
            student_count=12,
            teacher_id=1,
            teacher_assignment_id=1,
            resource_keys=(("group", 1),),
            student_ids=tuple(range(1, 13)),
        )
        lesson = SchedulingLesson(
            lesson_id=1,
            lesson_type="practice",
            hours=1,
            subject_id=1,
            targets=(target,),
        )
        slot = SchedulingTimeSlot(
            time_slot_id=1,
            day_of_week=1,
            lesson_number=1,
            start_time=SimpleNamespace(),
            end_time=SimpleNamespace(),
        )
        rooms = (
            SchedulingClassroom(1, "20", 20, "ordinary", None),
            SchedulingClassroom(2, "80", 80, "lecture", None),
        )
        generator = ScheduleGenerator(Mock(), 1)
        generator.data = SchedulingData(1, (lesson,), (slot,), rooms)
        generator._prepare_indexes()
        placements = generator._optimize_classroom_assignments((
            LessonPlacement(1, 1, {1: 2}),
        ))

        self.assertEqual(
            placements[0].classroom_by_target[1],
            1,
        )


class GenerationApiTests(unittest.TestCase):
    def test_generation_request_rejects_non_positive_period(self):
        with self.assertRaises(ValueError):
            ScheduleGenerateRequest(academic_period_id=0)

    def test_status_endpoint_returns_not_found_for_unknown_job(self):
        db = Mock()
        db.get.return_value = None

        with self.assertRaises(HTTPException) as context:
            get_generation_status("missing", db)

        self.assertEqual(context.exception.status_code, 404)

    def test_job_response_contains_persistent_fields(self):
        job = GenerationJob(
            id="job-1",
            academic_period_id=21,
            status="generated",
            schedule_version_id=7,
            error=None,
        )

        response = _generation_job_response(job)

        self.assertEqual(response["job_id"], "job-1")
        self.assertEqual(response["version_id"], 7)
        self.assertEqual(response["status"], "generated")

    def test_invalid_version_cannot_be_published(self):
        version = ScheduleVersion(
            id=7,
            academic_period_id=21,
            version_number=1,
            name="Test",
            status="generated",
        )
        db = Mock()
        db.get.return_value = version

        with patch(
            "backend.app.api.schedules.validate_schedule_version",
            return_value={"valid": False, "issues_count": 1, "issues": []},
        ):
            with self.assertRaises(HTTPException) as context:
                publish_schedule_version(7, db)

        self.assertEqual(context.exception.status_code, 409)
        db.commit.assert_not_called()

    def test_published_version_cannot_be_archived_directly(self):
        version = ScheduleVersion(
            id=7,
            academic_period_id=21,
            version_number=1,
            name="Test",
            status="published",
        )
        db = Mock()
        db.get.return_value = version

        with self.assertRaises(HTTPException) as context:
            archive_schedule_version(7, db)

        self.assertEqual(context.exception.status_code, 409)
        db.commit.assert_not_called()

    def test_item_response_uses_version_specific_classroom(self):
        stale_room = SimpleNamespace(id=1, name="Старая", capacity=80, room_type="lecture")
        version_room = SimpleNamespace(id=2, name="Новая", capacity=30, room_type="ordinary")
        teacher = SimpleNamespace(id=1, full_name="Преподаватель")
        subject = SimpleNamespace(id=1, code="SUB", name="Предмет")
        load = SimpleNamespace(
            teacher=teacher,
            curriculum_subject=SimpleNamespace(subject=subject),
        )
        target = SimpleNamespace(
            id=7,
            target_type="full_group",
            group_id=1,
            group=SimpleNamespace(id=1, name="Группа"),
            subgroup_id=None,
            subgroup=None,
            lecture_part_id=None,
            lecture_part=None,
            subgroup_bundle_id=None,
            subgroup_bundle=None,
            classroom=stale_room,
            teacher_assignment=SimpleNamespace(teacher_load=load),
        )
        lesson = SimpleNamespace(
            id=9,
            lesson_type="practice",
            hours=1,
            lesson_number=1,
            targets=[target],
        )
        item = SimpleNamespace(
            id=5,
            lesson=lesson,
            time_slot=SimpleNamespace(
                id=3,
                day_of_week=1,
                lesson_number=1,
                start_time=SimpleNamespace(),
                end_time=SimpleNamespace(),
            ),
            classroom_assignments=[
                SimpleNamespace(lesson_target_id=7, classroom=version_room)
            ],
        )

        response = _item_response(item)

        self.assertEqual(response["targets"][0]["classroom"]["id"], 2)


class CurriculumManagementTests(unittest.TestCase):
    def test_curriculum_subject_hours_must_match_breakdown(self):
        with self.assertRaises(ValueError):
            CurriculumSubjectPayload(
                subject_id=1,
                hours=100,
                lecture_hours=36,
                practice_hours=36,
                lab_hours=36,
                lecture_per_week=2,
            )

    def test_curriculum_subject_requires_weekly_lessons(self):
        with self.assertRaises(ValueError):
            CurriculumSubjectPayload(
                subject_id=1,
                hours=108,
                lecture_hours=36,
                practice_hours=36,
                lab_hours=36,
            )

    def test_cannot_delete_curriculum_subject_with_teacher_loads(self):
        item = SimpleNamespace(curriculum_id=7, teacher_loads=[SimpleNamespace()])
        db = Mock()
        db.get.return_value = item

        with self.assertRaises(HTTPException) as context:
            delete_curriculum_subject(7, 11, db)

        self.assertEqual(context.exception.status_code, 409)
        db.delete.assert_not_called()


class TeacherLoadDeletionTests(unittest.TestCase):
    @staticmethod
    def _db_with_load(load):
        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = load
        return db

    def test_regular_delete_protects_assigned_lessons(self):
        load = SimpleNamespace(assignments=[SimpleNamespace(id=4)])
        db = self._db_with_load(load)

        with self.assertRaises(HTTPException) as context:
            delete_teacher_load(3, db)

        self.assertEqual(context.exception.status_code, 409)
        db.delete.assert_not_called()

    def test_forced_delete_removes_orphan_lesson_and_load(self):
        lesson = Mock()
        assignment = SimpleNamespace(id=4, lesson_targets=[])
        target = SimpleNamespace(
            lesson=lesson,
            teacher_assignment_id=assignment.id,
        )
        assignment.lesson_targets.append(target)
        lesson.targets = [target]
        load = SimpleNamespace(assignments=[assignment])
        db = self._db_with_load(load)

        delete_teacher_load_with_assignments(3, db)

        self.assertEqual(db.delete.call_args_list, [call(lesson), call(load)])
        db.commit.assert_called_once_with()


class AuthTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        password = "admin123"
        hashed = hash_password(password)

        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong-password", hashed))
        self.assertFalse(verify_password(password, "pbkdf2_sha256$malformed"))

    def test_admin_token_has_admin_claim(self):
        user = User(
            id=1,
            username="admin",
            password_hash="pbkdf2_sha256$test$abc",
            full_name="Администратор",
            is_active=True,
            is_admin=True,
        )

        token = create_access_token(user)
        payload = jwt.decode(token, "smart-schedule-admin-secret-key", algorithms=["HS256"])

        self.assertEqual(payload["username"], "admin")
        self.assertTrue(payload["is_admin"])


class ScheduleFilterTests(unittest.TestCase):
    def test_group_filter_resource_contains_selected_group(self):
        target = SimpleNamespace(
            group=SimpleNamespace(id=12),
            subgroup=None,
            lecture_part=None,
            subgroup_bundle=None,
        )

        self.assertEqual(_target_group_ids(target), {12})

    def test_validation_uses_exact_subgroup_students(self):
        target = SimpleNamespace(
            group=None,
            subgroup=SimpleNamespace(
                students=[SimpleNamespace(student_id=1), SimpleNamespace(student_id=3)]
            ),
            lecture_part=None,
            subgroup_bundle=None,
        )

        self.assertEqual(_target_student_ids(target), {1, 3})


if __name__ == "__main__":
    unittest.main()
