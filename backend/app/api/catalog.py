from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.academic_period import AcademicPeriod
from backend.app.models.classroom import Classroom
from backend.app.models.group import Group
from backend.app.models.specialty import Specialty
from backend.app.models.subject import Subject
from backend.app.models.teacher import Teacher
from backend.app.models.teacher_load import TeacherLoad
from backend.app.models.curriculum_subject import CurriculumSubject
from backend.app.models.scheduling_constraint import SchedulingConstraint
from backend.app.models.lecture_stream import LectureStream
from backend.app.models.lecture_stream_group import LectureStreamGroup
from backend.app.models.time_slot import TimeSlot


router = APIRouter(prefix="/catalog", tags=["Catalog"])


@router.get("/overview")
def get_catalog_overview(db: Session = Depends(get_db)):
    periods = db.query(AcademicPeriod).order_by(AcademicPeriod.start_date.desc()).all()
    groups = db.query(Group).order_by(Group.name).all()
    specialties = db.query(Specialty).order_by(Specialty.code).all()
    subjects = db.query(Subject).order_by(Subject.name).all()
    teachers = db.query(Teacher).order_by(Teacher.full_name).all()
    classrooms = db.query(Classroom).order_by(Classroom.name).all()
    curricula = db.query(CurriculumSubject).all()
    loads = db.query(TeacherLoad).all()
    constraints = db.query(SchedulingConstraint).order_by(SchedulingConstraint.created_at.desc()).all()
    lecture_streams = db.query(LectureStream).filter(LectureStream.is_active.is_(True)).order_by(LectureStream.name).all()
    time_slots = db.query(TimeSlot).filter(TimeSlot.is_active.is_(True)).order_by(TimeSlot.day_of_week, TimeSlot.lesson_number).all()
    return {
        "periods": [
            {"id": item.id, "name": item.name, "academic_year": item.academic_year,
             "semester": item.semester, "start_date": item.start_date,
             "end_date": item.end_date, "weeks": item.weeks}
            for item in periods
        ],
        "groups": [
            {"id": item.id, "name": item.name, "course": item.course,
             "language": item.language, "student_count": item.student_count,
             "specialty_id": item.specialty_id,
             "specialty": item.specialty.code if item.specialty else None}
            for item in groups
        ],
        "lecture_streams": [
            {
                "id": item.id,
                "name": item.name,
                "academic_period_id": item.academic_period_id,
                "specialty_id": item.specialty_id,
                "group_ids": [link.group_id for link in item.groups],
            }
            for item in lecture_streams
        ],
        "time_slots": [
            {
                "id": item.id,
                "day_of_week": item.day_of_week,
                "lesson_number": item.lesson_number,
                "start_time": item.start_time,
                "end_time": item.end_time,
                "is_active": item.is_active,
            }
            for item in time_slots
        ],
        "specialties": [{"id": item.id, "code": item.code, "name": item.name} for item in specialties],
        "subjects": [{"id": item.id, "code": item.code, "name": item.name} for item in subjects],
        "teachers": [
            {"id": item.id, "full_name": item.full_name, "position": item.position,
             "department": item.department, "email": item.email, "is_active": item.is_active}
            for item in teachers
        ],
        "classrooms": [
            {"id": item.id, "name": item.name, "capacity": item.capacity,
             "room_type": item.room_type, "equipment": item.equipment,
             "is_active": item.is_active}
            for item in classrooms
        ],
        "curricula": [
            {"id": item.id, "curriculum_id": item.curriculum_id, "subject_id": item.subject_id,
             "subject": item.subject.name if item.subject else None, "hours": item.hours,
             "lecture_hours": item.lecture_hours, "practice_hours": item.practice_hours,
             "lab_hours": item.lab_hours}
            for item in curricula
        ],
        "qualifications": [
            {"id": item.id, "teacher_id": item.teacher_id,
             "teacher": item.teacher.full_name if item.teacher else None,
             "curriculum_subject_id": item.curriculum_subject_id,
             "subject": item.curriculum_subject.subject.name if item.curriculum_subject and item.curriculum_subject.subject else None,
             "lecture_hours": item.lecture_hours, "practice_hours": item.practice_hours,
             "lab_hours": item.lab_hours}
            for item in loads
        ],
        "constraints": [
            {"id": item.id, "constraint_type": item.constraint_type, "title": item.title,
             "description": item.description, "teacher_id": item.teacher_id,
             "classroom_id": item.classroom_id, "day_of_week": item.day_of_week,
             "start_time": item.start_time, "end_time": item.end_time,
             "is_active": item.is_active}
            for item in constraints
        ],
    }
