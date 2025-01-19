from typing import Union, Dict, Any

from aiogram.filters import BaseFilter
from aiogram.types import Message
from repo import get_only_user_by_tg_id
from models import RoleEnum
import logging

class RoleFilter(BaseFilter):
    def __init__(self, roles: list[RoleEnum]):
        super().__init__()
        self.roles = roles
        
    async def __call__(self, message: Message) -> bool:
        try:
            user = await get_only_user_by_tg_id(message.from_user.id)
            if not user:
                logging.warning(f"User not found by tg_id: {message.from_user.id}")
                await message.answer("Вы не зарегистрированы в системе!")
                return False
            if not user.role in self.roles:
                await message.answer(f"Вам не разрешено выполнять эту операцию! Ваша роль: {str(user.role).capitalize()}")
                return False
            return True
        except Exception as e:
            logging.error(f"Error getting user role: {e}")
            return False