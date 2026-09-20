import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
from fastapi import HTTPException

from backend.app.api.schedules import (
    ScheduleGenerateRequest,
    _generation_job_response,
    _target_group_ids,
    archive_schedule_version,
    get_generation_status,
    publish_schedule_version,
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
from backend.app.scheduler.scheduler import ScheduleGenerator


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


class AuthTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        password = "admin123"
        hashed = hash_password(password)

        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

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


if __name__ == "__main__":
    unittest.main()
