from datetime import datetime

from sqlalchemy import ForeignKey, func
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


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str]
    max_rent: Mapped[int]
    min_area: Mapped[int]


class Destination(Base):
    __tablename__ = "destinations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE")
    )
    destination: Mapped[str]


class Distance(Base):
    __tablename__ = "distances"
    apartment_id: Mapped[int] = mapped_column(
        ForeignKey("apartments.id", ondelete="CASCADE"), primary_key=True
    )
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"), primary_key=True
    )
    time: Mapped[int]


class SubscribedApartments(Base):
    __tablename__ = "subscribed_apartments"
    apartment_id: Mapped[int] = mapped_column(
        ForeignKey("apartments.id", ondelete="CASCADE"), primary_key=True
    )
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), primary_key=True
    )
    notified: Mapped[bool] = mapped_column(default=False)
