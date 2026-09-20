from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class LectureStreamStudent(Base):
    __tablename__ = "lecture_stream_students"

    __table_args__ = (
        UniqueConstraint(
            "lecture_stream_id",
            "student_id",
            name="uq_lecture_stream_student",
        ),
        UniqueConstraint(
            "lecture_stream_id",
            "list_order",
            name="uq_lecture_stream_student_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    lecture_stream_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lecture_streams.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    list_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    lecture_stream = relationship(
        "LectureStream",
        back_populates="students",
    )

    student = relationship(
        "Student",
    )