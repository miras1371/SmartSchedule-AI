from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class SubgroupSet(Base):
    __tablename__ = "subgroup_sets"

    __table_args__ = (
        UniqueConstraint(
            "lecture_stream_id",
            "academic_period_id",
            "version",
            name="uq_subgroup_set_stream_period_version",
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

    academic_period_id: Mapped[int] = mapped_column(
        ForeignKey(
            "academic_periods.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    lecture_stream = relationship(
        "LectureStream",
        back_populates="subgroup_sets",
    )

    subgroups = relationship(
        "Subgroup",
        back_populates="subgroup_set",
    )