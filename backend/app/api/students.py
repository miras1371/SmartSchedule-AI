from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.models.group import Group
from backend.app.models.lecture_stream import LectureStream
from backend.app.models.lecture_stream_student import LectureStreamStudent
from backend.app.models.student import Student
from backend.app.schemas.student import StudentUpdate, StudentsCreate


router = APIRouter(
    prefix="/groups",
    tags=["Students"],
)


class GroupPayload(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    specialty_id: int
    course: int = Field(ge=1, le=10)
    language: str = Field(min_length=1, max_length=50)


def group_response(group: Group):
    return {
        "id": group.id,
        "name": group.name,
        "specialty_id": group.specialty_id,
        "course": group.course,
        "language": group.language,
        "student_count": group.student_count,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_group(data: GroupPayload, db: Session = Depends(get_db)):
    from backend.app.models.specialty import Specialty
    if db.query(Group).filter(Group.name == data.name).first():
        raise HTTPException(status_code=400, detail="Группа с таким названием уже существует")
    if db.query(Specialty).filter(Specialty.id == data.specialty_id).first() is None:
        raise HTTPException(status_code=404, detail="Специальность не найдена")
    group = Group(**data.model_dump(), student_count=0)
    db.add(group)
    db.commit()
    db.refresh(group)
    return {"group": group_response(group)}


@router.patch("/{group_id}")
def update_group(group_id: int, data: GroupPayload, db: Session = Depends(get_db)):
    from backend.app.models.specialty import Specialty
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    if db.query(Group).filter(Group.name == data.name, Group.id != group_id).first():
        raise HTTPException(status_code=400, detail="Группа с таким названием уже существует")
    if db.query(Specialty).filter(Specialty.id == data.specialty_id).first() is None:
        raise HTTPException(status_code=404, detail="Специальность не найдена")
    for field, value in data.model_dump().items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return {"group": group_response(group)}


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    if group.students or group.teacher_assignments:
        raise HTTPException(status_code=409, detail="Нельзя удалить группу с привязанными студентами или назначениями преподавателей.")
    db.delete(group)
    db.commit()


def serialize_student(student: Student):
    return {
        "id": student.id,
        "full_name": student.full_name,
        "group_id": student.group_id,
        "group_name": student.group.name if student.group else None,
    }


@router.get("/students")
def list_students(
    group_id: int | None = None,
    lecture_stream_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Student).join(Group)
    if group_id is not None:
        query = query.filter(Student.group_id == group_id)
    if lecture_stream_id is not None:
        query = query.join(LectureStreamStudent).filter(
            LectureStreamStudent.lecture_stream_id == lecture_stream_id,
        )
    students = query.order_by(Group.name, Student.full_name).all()
    stream_links = db.query(LectureStreamStudent).filter(
        LectureStreamStudent.student_id.in_([student.id for student in students]),
    ).all() if students else []
    streams = {
        student_id: [] for student_id in [student.id for student in students]
    }
    stream_map = {
        stream.id: stream.name
        for stream in db.query(LectureStream).filter(
            LectureStream.id.in_([link.lecture_stream_id for link in stream_links]),
        ).all()
    }
    for link in stream_links:
        streams[link.student_id].append({
            "id": link.lecture_stream_id,
            "name": stream_map.get(link.lecture_stream_id),
        })
    return {
        "count": len(students),
        "students": [
            {**serialize_student(student), "streams": streams[student.id]}
            for student in students
        ],
    }


@router.patch("/students/{student_id}")
def update_student(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Студент не найден")
    group = db.query(Group).filter(Group.id == data.group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    old_group_id = student.group_id
    if old_group_id != data.group_id and group.student_count >= 25:
        raise HTTPException(
            status_code=400,
            detail="В группе не может быть больше 25 студентов",
        )
    student.full_name = data.full_name.strip()
    student.group_id = data.group_id
    if old_group_id != data.group_id:
        old_group = db.query(Group).filter(Group.id == old_group_id).first()
        if old_group:
            old_group.student_count = max(0, old_group.student_count - 1)
        group.student_count += 1

    streams = db.query(LectureStream).filter(
        LectureStream.id.in_(data.lecture_stream_ids),
        LectureStream.is_active.is_(True),
    ).all() if data.lecture_stream_ids else []
    if len(streams) != len(set(data.lecture_stream_ids)):
        raise HTTPException(status_code=400, detail="Один из потоков не найден")
    db.query(LectureStreamStudent).filter(
        LectureStreamStudent.student_id == student.id,
    ).delete(synchronize_session=False)
    for index, stream in enumerate(streams, start=1):
        db.add(LectureStreamStudent(
            lecture_stream_id=stream.id,
            student_id=student.id,
            list_order=index,
        ))
    db.commit()
    db.refresh(student)
    return serialize_student(student)


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=404, detail="Студент не найден")
    group = db.query(Group).filter(Group.id == student.group_id).first()
    if group:
        group.student_count = max(0, group.student_count - 1)
    db.delete(student)
    db.commit()


@router.post(
    "/{group_id}/students",
    status_code=status.HTTP_201_CREATED,
)
def create_students(
    group_id: int,
    data: StudentsCreate,
    db: Session = Depends(get_db),
):
    group = (
        db.query(Group)
        .filter(Group.id == group_id)
        .first()
    )

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Группа не найдена",
        )

    if not data.students:
        raise HTTPException(
            status_code=400,
            detail="Список студентов не может быть пустым",
        )

    if len(data.students) + group.student_count > 25:
        raise HTTPException(
            status_code=400,
            detail="В группе не может быть больше 25 студентов",
        )

    students = []

    for student_data in data.students:
        student = Student(
            full_name=student_data.full_name.strip(),
            group_id=group.id,
        )

        db.add(student)
        students.append(student)

    group.student_count += len(students)

    db.commit()

    for student in students:
        db.refresh(student)

    return {
        "message": "Студенты успешно добавлены",
        "group_id": group.id,
        "group_name": group.name,
        "student_count": group.student_count,
        "students": [
            {
                "id": student.id,
                "full_name": student.full_name,
                "group_id": student.group_id,
            }
            for student in students
        ],
    }