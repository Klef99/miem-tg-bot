from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from models import *
from database import connection
from asyncio import run

@connection
async def create_user(data: UserData, session: AsyncSession) -> int:
    user = User(username=data.username, tg_id=data.tg_id, role=data.role)
    session.add(user)
    await session.commit()
    return user.id


@connection
async def get_user_by_tg_id(tg_id: int, session: AsyncSession) -> User:
    user = await session.execute(select(User).where(User.tg_id == tg_id).options(joinedload(User.events), joinedload(User.points)))
    return user.scalars().first() if user else None

@connection
async def get_only_user_by_tg_id(tg_id: int, session: AsyncSession):
    user = await session.execute(select(User).where(User.tg_id == tg_id))
    return user.scalars().first() if user else None

@connection
async def add_point_to_user(data: PointData, session: AsyncSession) -> None:
    point_user = PointUser(point_id=data.point_id, user_id=data.user_id)
    session.add(point_user)
    await session.commit()
    return point_user.id


@connection
async def create_event(data: EventData, session: AsyncSession) -> int:
    event = Event(name=data.name, desc=data.desc, org_id=data.org_id)
    session.add(event)
    await session.commit()
    return event.id

@connection
async def create_point(data: PointData, session: AsyncSession) -> int:
    point = Point(name=data.name, event_id=data.event_id, reward=data.reward)
    session.add(point)
    await session.commit()
    return point.id

@connection
async def add_many_points(points_data: list[PointData], session: AsyncSession) -> int:
    points_list = [
        Point(
            name=point_data.name,
            event_id=point_data.event_id,
            reward=point_data.reward
        )
        for point_data in points_data
    ]
    session.add_all(points_list)
    await session.commit()
    return len(points_list)

@connection
async def get_all_events(session: AsyncSession) -> list["Event"]:
    events = await session.execute(select(Event).options(joinedload(Event.points)))
    return events.unique().scalars().all()

@connection
async def get_event_by_id(event_id: int, session: AsyncSession) -> Event | None:
    event = await session.execute(select(Event).where(Event.id == event_id).options(joinedload(Event.points)))
    return event.scalars().first() if event else None

@connection
async def get_all_users(session: AsyncSession) -> list["User"]:
    users = await session.execute(select(User).options(joinedload(User.events), joinedload(User.points)))
    return users.unique().scalars().all()

@connection
async def update_event(data: EventData, event_id: int, session: AsyncSession) -> int:
    event = await session.execute(update(Event).where(Event.id == event_id).values(name=data.name, desc=data.desc, org_id=data.org_id))
    await session.commit()
    return 1 if event.rowcount == 1 else -1
