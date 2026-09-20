from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class TeacherLoad(Base):
    __tablename__ = "teacher_loads"

    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "curriculum_subject_id",
            name="uq_teacher_curriculum_subject",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    curriculum_subject_id: Mapped[int] = mapped_column(
        ForeignKey(
            "curriculum_subjects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    lecture_hours: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    practice_hours: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    lab_hours: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    lecture_per_week: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    practice_per_week: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    lab_per_week: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    lecture_max_students: Mapped[int] = mapped_column(
        Integer,
        default=70,
        nullable=False,
    )

    practice_max_students: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    lab_max_students: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    teacher = relationship(
        "Teacher",
        back_populates="loads",
    )

    curriculum_subject = relationship(
        "CurriculumSubject",
        back_populates="teacher_loads",
    )

    assignments = relationship(
        "TeacherAssignment",
        back_populates="teacher_load",
        cascade="all, delete-orphan",
    )