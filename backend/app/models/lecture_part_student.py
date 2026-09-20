from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class LecturePartStudent(Base):
    __tablename__ = "lecture_part_students"

    __table_args__ = (
        UniqueConstraint(
            "lecture_part_id",
            "student_id",
            name="uq_lecture_part_student",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    lecture_part_id: Mapped[int] = mapped_column(
        ForeignKey("lecture_parts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    list_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    lecture_part = relationship(
        "LecturePart",
        back_populates="students",
    )

    student = relationship("Student")
