import repo
from models import *
from ai_connector import gigaChatConnector as gcc
from asyncio import run

async def create_user(data: UserData) -> int:
    try:
        id = await repo.create_user(data)
        return id
    except Exception as e:
        print(f"Error creating user: {e}")
        return -1

async def create_event(data: EventData, tg_id: int) -> int:
    try:
        pts = gcc.get_event_points(data.name, data.desc)
        if data.org_id is not None:
            user = await repo.get_only_user_by_tg_id(tg_id)
            if not user:
                print(f"User not found by tg_id: {tg_id}")
                return -1
            data.org_id = user.id
        id = await repo.create_event(data)
        pts = [PointData(name=pt["title"], reward=pt["reward_points"], event_id=id) for pt in pts]
        st = await repo.add_many_points(pts)
        return id if st == len(pts) else -1
    except Exception as e:
        print(f"Error creating event: {e}")
        return -1

async def add_point_to_user(data: PointUserData, tg_id: int) -> None:
    try:
        if data.user_id is not None:
            user = await repo.get_only_user_by_tg_id(tg_id)
            if not user:
                print(f"User not found by tg_id: {tg_id}")
                return -1
            data.user_id = user.id
        id = await repo.add_point_to_user(data)
        return id
    except Exception as e:
        print(f"Error creating event: {e}")
        return -1

async def get_all_user_events(tg_id: int):
    try:
        user = await repo.get_user_by_tg_id(tg_id)
        if not user:
            print(f"User not found by tg_id: {tg_id}")
            return []
        events = user.events
        return events
    except Exception as e:
        print(f"Error getting user events: {e}")
        return []

async def get_all_events():
    try:
        events = await repo.get_all_events()
        return events
    except Exception as e:
        print(f"Error getting all events: {e}")
        return []
    
async def get_leaderboard():
    try:
        users = await repo.get_all_users()
        res = []
        for user in users:
            points = sum([pt.reward for pt in user.points])
            user.points_total = points
            res.append(user.username)
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return []