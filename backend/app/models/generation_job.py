from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        Index(
            "uq_generation_jobs_active_period",
            "academic_period_id",
            unique=True,
            postgresql_where=(
                "status IN ('queued', 'running')"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    academic_period_id: Mapped[int] = mapped_column(
        ForeignKey("academic_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schedule_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedule_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        server_default="queued",
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    academic_period = relationship("AcademicPeriod")
    schedule_version = relationship("ScheduleVersion")
