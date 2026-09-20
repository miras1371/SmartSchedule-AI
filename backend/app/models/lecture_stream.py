from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class LectureStream(Base):
    __tablename__ = "lecture_streams"

    __table_args__ = (
        UniqueConstraint(
            "specialty_id",
            "academic_period_id",
            "name",
            name="uq_lecture_stream_specialty_period_name",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    specialty_id: Mapped[int] = mapped_column(
        ForeignKey(
            "specialties.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    academic_period_id: Mapped[int] = mapped_column(
        ForeignKey(
            "academic_periods.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    groups = relationship(
        "LectureStreamGroup",
        back_populates="lecture_stream",
        cascade="all, delete-orphan",
    )

    students = relationship(
        "LectureStreamStudent",
        back_populates="lecture_stream",
        cascade="all, delete-orphan",
    )

    subgroup_sets = relationship(
        "SubgroupSet",
        back_populates="lecture_stream",
        cascade="all, delete-orphan",
    )

    lecture_parts = relationship(
        "LecturePart",
        back_populates="lecture_stream",
        cascade="all, delete-orphan",
    )