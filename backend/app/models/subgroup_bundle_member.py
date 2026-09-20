from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class SubgroupBundleMember(Base):
    __tablename__ = "subgroup_bundle_members"
    __table_args__ = (
        UniqueConstraint("bundle_id", "subgroup_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bundle_id: Mapped[int] = mapped_column(
        ForeignKey("subgroup_bundles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subgroup_id: Mapped[int] = mapped_column(
        ForeignKey("subgroups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    bundle = relationship("SubgroupBundle", back_populates="members")
    subgroup = relationship("Subgroup")
