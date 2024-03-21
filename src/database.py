from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Apartment(Base):
    __tablename__ = "apartments"
    id: Mapped[str] = mapped_column(primary_key=True)
    address: Mapped[str]
    location: Mapped[str]
    size: Mapped[str]
    area: Mapped[float]
    rent: Mapped[int]
    free_from: Mapped[datetime]
    url: Mapped[str]
    updated: Mapped[datetime] = mapped_column(server_default=func.now())
    notified: Mapped[bool] = mapped_column(default=False)
    time_to_school: Mapped[str]
    time_to_center: Mapped[str]
    time_to_bar: Mapped[str]
