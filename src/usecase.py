import repo
from models import *
from ai_connector import gigaChatConnector as gcc
from asyncio import run
from main import logger

async def create_user(data: UserData) -> int:
    try:
        user = await repo.get_user_by_tg_id(data.tg_id)
        if user is not None:
            logger.warning(f"User already exists by tg_id: {data.tg_id}")
            return -2
        id = await repo.create_user(data)
        return id
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return -1

async def create_event(data: EventData, tg_id: int) -> int:
    try:
        pts = gcc.get_event_points(data.name, data.desc)
        if data.org_id is None:
            user = await repo.get_only_user_by_tg_id(tg_id)
            if not user:
                logger.warning(f"User not found by tg_id: {tg_id}")
                return -1
            data.org_id = user.id
        id = await repo.create_event(data)
        pts = [PointData(name=pt["title"], reward=pt["reward_points"], event_id=id) for pt in pts]
        st = await repo.add_many_points(pts)
        return id if st == len(pts) else -1
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return -1

async def add_point_to_user(data: PointUserData, tg_id: int) -> int:
    try:
        if data.user_id is None:
            user = await repo.get_only_user_by_tg_id(tg_id)
            if not user:
                logger.warning(f"User not found by tg_id: {tg_id}")
                return -1
            data.user_id = user.id
        id = await repo.add_point_to_user(data)
        return id
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return -1

async def get_all_user_events(tg_id: int) -> list['Event']:
    try:
        user = await repo.get_user_by_tg_id(tg_id)
        if not user:
            logger.warning(f"User not found by tg_id: {tg_id}")
            return []
        events = user.events
        return events
    except Exception as e:
        logger.error(f"Error getting user events: {e}")
        return []

async def get_all_events() -> list["Event"]:
    try:
        events = await repo.get_all_events()
        return events
    except Exception as e:
        logger.error(f"Error getting all events: {e}")
        return []
    
async def get_leaderboard():
    try:
        users = await repo.get_all_users()
        res = []
        for user in users:
            if user.role != RoleEnum.PARTICIPANT:
                continue
            points = sum([pt.reward for pt in user.points])
            res.append((user.username, points))
        return sorted(res, key=lambda x: x[1], reverse=True)
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        return []

async def update_event(data: EventData, event_id: int, tg_id: int):
    try:
        if data.org_id is None:
            user = await repo.get_user_by_tg_id(tg_id)
            if not user:
                logger.warning(f"User not found by tg_id: {tg_id}")
                return -1
            flag = True
            for event in user.events:
                if event.id == event_id:
                    flag = False
                    if data.name is None:
                        data.name = event.name
                    if data.desc is None:
                        data.desc = event.desc
                    break
            if flag:
                logger.warning(f"Event not owned by this user: {user.username}")
                return -1
            data.org_id = user.id
        id = await repo.update_event(data, event_id)
        return id
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        return -1

async def get_user_role(tg_id: int) -> RoleEnum | None:
    try:
        user = await repo.get_only_user_by_tg_id(tg_id)
        if not user:
            logger.warning(f"User not found by tg_id: {tg_id}")
            return None
        return user.role
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return None