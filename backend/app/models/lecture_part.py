from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class LecturePart(Base):
    __tablename__ = "lecture_parts"

    __table_args__ = (
        UniqueConstraint(
            "lecture_stream_id",
            "version",
            "part_number",
            name="uq_lecture_part_stream_version_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    lecture_stream_id: Mapped[int] = mapped_column(
        ForeignKey("lecture_streams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    part_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    student_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    lecture_stream = relationship(
        "LectureStream",
        back_populates="lecture_parts",
    )

    students = relationship(
        "LecturePartStudent",
        back_populates="lecture_part",
        cascade="all, delete-orphan",
    )
