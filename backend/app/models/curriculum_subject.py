from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class CurriculumSubject(Base):
    __tablename__ = "curriculum_subjects"

    __table_args__ = (
        UniqueConstraint(
            "curriculum_id",
            "subject_id",
            name="uq_curriculum_subject",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    curriculum_id: Mapped[int] = mapped_column(
        ForeignKey("curricula.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
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

    curriculum = relationship(
        "Curriculum",
        back_populates="subjects",
    )

    subject = relationship(
        "Subject",
        back_populates="curriculum_subjects",
    )

    teacher_loads = relationship(
        "TeacherLoad",
        back_populates="curriculum_subject",
        cascade="all, delete-orphan",
    )