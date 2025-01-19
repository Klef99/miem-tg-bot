from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
import enum
from dataclasses import dataclass

class RoleEnum(enum.StrEnum):
    PARTICIPANT = "участник"
    ORGANIZER = "организатор"
    ADMIN = "администратор"
    UNREGISTER = "незарегистрированный"

@dataclass
class UserData:
    username: str
    tg_id: int
    role: RoleEnum

@dataclass
class PointData:
    name: str
    event_id: int
    reward: int

@dataclass
class PointUserData:
    point_id: int
    user_id: int

@dataclass
class EventData:
    name: str
    desc: str
    org_id: int


class User(Base):
    username: Mapped[str] = mapped_column(unique=True, nullable=False)
    tg_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    role: Mapped[RoleEnum] = mapped_column(default=RoleEnum.PARTICIPANT, server_default="'PARTICIPANT'")
    
    events: Mapped[list["Event"]] = relationship(
        "Event",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    points: Mapped[list["Point"]] = relationship(
        secondary="pointusers",
        back_populates="users"
    )

class Event(Base):
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    desc: Mapped[str]
    org_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user: Mapped["User"] = relationship(
        "User",
        back_populates="events"
    )
    points: Mapped[list["Point"]] = relationship(
        "Point",
        back_populates="event",
        cascade="all, delete-orphan"
    )

class Point(Base):
    name: Mapped[str] = mapped_column(nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id'), nullable=False)
    reward: Mapped[int] = mapped_column(nullable=False)
    event: Mapped["Event"] = relationship(
        "Event",
        back_populates="points"
    )
    users: Mapped[list["User"]] = relationship(
        secondary="pointusers",
        back_populates="points"
    )

class PointUser(Base):
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    point_id: Mapped[int] = mapped_column(ForeignKey("points.id"))