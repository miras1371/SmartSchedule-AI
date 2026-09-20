from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    specialty_id: Mapped[int] = mapped_column(
        ForeignKey("specialties.id"),
        nullable=False,
        index=True,
    )

    course: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    student_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    specialty = relationship(
        "Specialty",
        back_populates="groups",
    )

    students = relationship(
        "Student",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    teacher_assignments = relationship(
        "TeacherAssignment",
        back_populates="group",
        cascade="all, delete-orphan",
    )