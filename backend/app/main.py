from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from sqlalchemy import text

from backend.app.core.auth import ensure_default_admin_user, require_admin_access
from backend.app.core.database import (
    Base,
    engine,
    SessionLocal,
    settings,
)

from backend.app.models import (
    User,
    Group,
    Student,
    LectureStream,
    LectureStreamGroup,
    LectureStreamStudent,
    LecturePart,
    LecturePartStudent,
    SubgroupBundle,
    SubgroupBundleMember,
    Subgroup,
    SubgroupSet,
    SubgroupStudent,
    Specialty,
    Subject,
    Curriculum,
    CurriculumSubject,
    Teacher,
    TeacherLoad,
    TeacherAssignment,
    TeacherAssignmentTarget,
    Lesson,
    LessonTarget,
    AcademicPeriod,
    Classroom,
    TimeSlot,
    ScheduleVersion,
    ScheduleItem,
    ScheduleItemClassroom,
    GenerationJob,
)

from backend.app.api.auth import router as auth_router
from backend.app.api.students import router as students_router
from backend.app.api.subgroups import router as subgroups_router
from backend.app.api.lessons import router as lessons_router
from backend.app.api.teacher_assignments import (
    router as teacher_assignments_router,
)
from backend.app.api.teacher_loads import (
    router as teacher_loads_router,
)
from backend.app.api.classrooms import router as classrooms_router
from backend.app.api.lesson_targets import router as lesson_targets_router
from backend.app.api.lecture_parts import router as lecture_parts_router
from backend.app.api.subgroup_bundles import (
    router as subgroup_bundles_router,
)
from backend.app.api.schedules import router as schedules_router
from backend.app.api.catalog import router as catalog_router
from backend.app.api.constraints import router as constraints_router
from backend.app.api.teachers import router as teachers_router
from backend.app.api.management import router as management_router

from backend.app.services.time_slot_service import (
    create_default_time_slots,
)


if settings.APP_ENV.lower() != "production":
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE teacher_loads ADD COLUMN IF NOT EXISTS language VARCHAR(50) NOT NULL DEFAULT 'Русский'"))


def initialize_time_slots() -> None:
    db = SessionLocal()

    try:
        create_default_time_slots(db)
    finally:
        db.close()


if settings.APP_ENV.lower() != "production":
    initialize_time_slots()

ensure_default_admin_user()

app = FastAPI(    title="SmartSchedule AI",
    description="Система интеллектуального формирования университетского расписания",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.middleware("http")(require_admin_access)

app.include_router(auth_router)
app.include_router(students_router)
app.include_router(subgroups_router)
app.include_router(lessons_router)
app.include_router(teacher_assignments_router)
app.include_router(teacher_loads_router)
app.include_router(classrooms_router)
app.include_router(lesson_targets_router)
app.include_router(lecture_parts_router)
app.include_router(subgroup_bundles_router)
app.include_router(schedules_router)
app.include_router(catalog_router)
app.include_router(constraints_router)
app.include_router(teachers_router)
app.include_router(management_router)

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "SmartSchedule AI работает",
    }


frontend_directory = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
