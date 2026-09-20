from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class Curriculum(Base):
    __tablename__ = "curricula"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
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

    semester: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    academic_year: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    specialty = relationship(
        "Specialty",
        back_populates="curricula",
    )

    subjects = relationship(
        "CurriculumSubject",
        back_populates="curriculum",
        cascade="all, delete-orphan",
    )

    academic_period_id: Mapped[int] = mapped_column(
        ForeignKey("academic_periods.id"),
        nullable=False,
        index=True,
    )

    academic_period = relationship(
        "AcademicPeriod",
        back_populates="curricula",
    )