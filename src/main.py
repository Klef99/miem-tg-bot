import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.filters.callback_data import CallbackData
from aiogram import F
from aiogram.types import Message
from aiogram.types import FSInputFile
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from html import escape
from pyzbar.pyzbar import decode
from PIL import Image
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging
import qrcode
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from aiosmtplib import SMTP


from settings import settings
from models import *
import usecase
import repo
from filters import RoleFilter

class Registration(StatesGroup):
  fio_wait=State()
  role_wait=State()


class Arbeit(StatesGroup,):
  code_wait = State()
  code_event_name = State()
  code_event_part = State()
  redact_event_name = State()
  change_event_name = State()
  change_event_desc = State()
  feedback_wait = State()


class infoFactory(CallbackData, prefix='mero'):
    id_mero: int


logging.basicConfig(force=True, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
bot = Bot(token=settings.TG_KEY, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
sheduler = AsyncIOScheduler()

@dp.message(CommandStart(), State(None))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    try:
        user = await repo.get_only_user_by_tg_id(message.from_user.id)
        if user:
            await message.answer(f'Приветствую, {user.username}! Вы уже зарегистрированы. Ваша роль: {str(user.role).capitalize()}',
                              reply_markup=ReplyKeyboardRemove())
            await start_bot(user.role, message.chat.id)
            return
        await message.answer('Приветствую вас! Так как вы не зарегистрированны, то функционал бота недоступен. Для регистрации введите команду /reg',
                          reply_markup=ReplyKeyboardRemove()) 
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        await message.answer('Приветствую вас! Так как вы не зарегистрированны, то функционал бота недоступен. Для регистрации введите команду /reg',
                          reply_markup=ReplyKeyboardRemove())
        return


@dp.message(Command('feedback'), RoleFilter([RoleEnum.ADMIN, RoleEnum.ORGANIZER, RoleEnum.PARTICIPANT]), State(None))
async def cmd_feedback(message: Message, state: FSMContext):
    await message.answer('Напишите текст отзыва и я отправлю его моим создателям')
    await state.set_state(Arbeit.feedback_wait.state)

@dp.message(F.text, Arbeit.feedback_wait)
async def send_feedback(message: Message, state: FSMContext):
    try:
        msg = message.text
        email_msg = MIMEMultipart()
        email_msg["From"] = settings.EMAIL_ADDRESS
        email_msg["To"] = settings.EMAIL_ADDRESS
        email_msg["Subject"] = 'feedback'
        email_msg.attach(MIMEText(f"<html><body>{msg}</body></html>", "html", "utf-8"))
        smtp_client = SMTP(hostname="smtp.mail.ru", port=465, use_tls=True)
        async with smtp_client:
            await smtp_client.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            await smtp_client.send_message(email_msg)
        # message.answer("Отзыв отправлен!")
        await state.clear()
    except Exception as e:
        logger.error(f"Error sending feedback: {e}")
        await message.answer('Произошла ошибка при отправке отзыва. Пожалуйста, попробуйте снова.')
        return

async def send_after(user_id: int):
  await bot.send_message(
                user_id,
                "Привет! Прошла неделя с момента вашей регистрации. Нам будет приятно, если вы оставите отзыв о нашем боте!\n вызовите команду \feedback, чтобы написать отзыв"
            )

@dp.message(F.photo, Arbeit.code_wait)  #Сканирование qr-кода
async def QrCodePhoto(message: types.Message, state: FSMContext):
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        with tempfile.NamedTemporaryFile() as tmp:
            file_path = tmp.name
            await bot.download_file(file_info.file_path, destination=file_path)
            img = Image.open(file_path)
            decoded_objects = decode(img)
            if decoded_objects:
                result_text = "\n".join([obj.data.decode("utf-8") for obj in decoded_objects])
                id = await usecase.add_point_to_user(PointUserData(int(result_text), None), message.from_user.id)
                if id == -1:
                    await message.answer("Данный код был уже использован вами или произошла ошибка при начислении баллов!")
                    await state.clear()
                    return
                await message.answer(f"Баллы начислены!")
                await state.clear()
            else:
                await message.answer("QR-код не найден. Попробуй еще раз.")
    except Exception as e:
        logging.error(f"Ошибка при обработке QR-кода: {e}")
        await message.answer("Произошла ошибка при обработке QR-кода. Попробуй еще раз.")
        await state.clear()


@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup= ReplyKeyboardRemove())


@dp.message(Command("info"), RoleFilter([RoleEnum.ADMIN, RoleEnum.ORGANIZER, RoleEnum.PARTICIPANT]), State(None))
async def cmd_info(message: Message, state: FSMContext):
    await state.clear()
    try:
        events = await usecase.get_all_events()
        if events == []:
            await message.answer("Нет ни одного мероприятия")
            await state.clear()
            return
        await state.update_data(events=events)
    except Exception as e:
        logging.error(f"Error getting all events: {e}")
        await message.answer("Ошибка при получении информации о мероприятиях")
        await state.clear()
        return
    buttons = InlineKeyboardBuilder()
    for event in events:  #билдим кнопки на основе списка меро: id_mero - id меро, id_point - id пункта
        buttons.button(text=str(event.id), callback_data=infoFactory(id_mero=event.id).pack())
    await message.answer("Информация о мероприятиях (id - название):\n"+ "\n".join([f"-- {i.id} - {i.name}" for i in events]),reply_markup=buttons.as_markup())
    await state.clear()


@dp.callback_query(infoFactory.filter())
async def points_but(callback: CallbackQuery, callback_data: infoFactory):
    await callback.message.delete()
    id = callback.data.split(":")[-1]
    try:
        event = await repo.get_event_by_id(int(id))
    except Exception as e:
        logging.error(f"Error getting event by id: {e}")
        await callback.message.answer("Ошибка при получении мероприятия")
        return
    s="Название:\n\n" + event.name + "\n\nОписание:\n\n" + event.desc + "\n\nАктивности мероприятия и награда за их выполнение:\n\n" + "\n\n".join([f"{point.name} - {point.reward} баллов" for point in event.points])
    await callback.message.answer(s)


@dp.message(Command("leaderboard"), RoleFilter([RoleEnum.ADMIN, RoleEnum.PARTICIPANT, RoleEnum.ORGANIZER]), State(None))
async def cmd_leaderboard(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Таблица лидеров:\n")
    data = await usecase.get_leaderboard()
    for thing in data:
      await message.answer(str(thing[0])+' - '+str(thing[1])+' баллов')
    await state.clear()


@dp.message(Command("scan"), RoleFilter([RoleEnum.ADMIN, RoleEnum.PARTICIPANT, RoleEnum.ORGANIZER]), State(None))
async def cmd_scan_call(message: Message, state: FSMContext):
    await message.answer("Отсканируйте qr-код и отправьте результат сообщением")
    await state.set_state(Arbeit.code_wait.state)


roles = [
        [KeyboardButton(text='Участник')],
        [KeyboardButton(text='Организатор')]
        ]
roles_logic = ["участник", "организатор"]

@dp.message(Command("reg"), State(None))  #Регистрация пользователя
async def cmd_reg_start(message: Message,state: FSMContext):
    try:
        user = await repo.get_only_user_by_tg_id(message.from_user.id)
        if user is not None:
            raise(Exception('User not found'))
    except Exception as e:
        await message.answer("Вы уже зарегистрированы!")
        return
    keyboard = types.ReplyKeyboardMarkup(keyboard=roles, resize_keyboard=True)
    await message.answer("Выберете роль:", reply_markup=keyboard)
    await state.set_state(Registration.role_wait.state)

@dp.message(F.text, Registration.role_wait)
async def cmd_reg_role(message: types.Message, state: FSMContext):
    if message.text.lower() not in roles_logic:
        await message.answer("Пожалуйста, выберите роль, используя клавиатуру ниже.")
        return
    await state.update_data(Role = message.text.lower())
    await state.set_state(Registration.fio_wait.state)
    await message.answer("Введите своё имя пользователя через клавиатуру:", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text,  Registration.fio_wait)
async def cmd_reg_fio(message: types.Message, state: FSMContext):
    if len(message.text) < 4:
      await message.answer(f'Имя введено некорректно (меньше 4-х символов). Повторите ввод')
      return
    user = await state.get_data()
    try:
        data = UserData(username=message.text, tg_id=message.from_user.id, role=RoleEnum(user["Role"]))
        st = await usecase.create_user(data)
        if st == -2:
            await message.answer('Вы уже зарегистрированы!')
            await state.clear()
            return
        if st == -1:
            await message.answer('Пользователь с такими данными уже существует!')
            await state.clear()
            return
    except Exception as e:
        logging.error(f'Ошибка при создании пользователя: {e}')
        await message.answer('Произошла ошибка при создании пользователя. Попробуйте позже.')
        await state.clear()
        return
    await message.answer(f'Успешная регистрация!')
    send_time = datetime.now() + timedelta(seconds=20)
    sheduler.add_job(send_after, "date", run_date=send_time, args=[message.from_user.id])
    await start_bot(RoleEnum(user["Role"]), message.chat.id)
    await state.clear()



class event_reg(StatesGroup):
  place_wait = State()
  description_wait = State()


@dp.message(Command("event"), RoleFilter([RoleEnum.ADMIN, RoleEnum.ORGANIZER]), State(None))
async def cmd_event_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название вашего мероприятия")
    await state.set_state(event_reg.place_wait.state)

@dp.message(F.text, event_reg.place_wait)
async def cmd_event_place(message: types.Message, state: FSMContext):
    await state.update_data(title = message.text)
    await message.answer("Введите описание вашего мероприятия:")
    await state.set_state(event_reg.description_wait.state)


@dp.message(F.text, event_reg.description_wait)
async def cmd_event_description(message: types.Message, state: FSMContext):
    await state.update_data(desc = message.text)
    try:
        data = await state.get_data()
        st = await usecase.create_event(EventData(data["title"], data["desc"], None), message.from_user.id)
        if st == -1:
            await message.answer('Произошла ошибка при регистрации мероприятия. Попробуйте позже.')
            await state.clear()
            return
    except Exception as e:
        logging.error(f'Ошибка при регистрации мероприятия: {e}')
        await message.answer('Произошла ошибка при регистрации мероприятия. Попробуйте позже.')
        await state.clear()
        return
    await state.clear()
    await message.answer("Ваше мероприятие зарегистрированно!")


@dp.message(Command("redact"), RoleFilter([RoleEnum.ADMIN, RoleEnum.ORGANIZER]), State(None))
async def cmd_redact_start(message: Message, state: FSMContext):
    try:
        events = await usecase.get_all_user_events(message.from_user.id)
        events = [f"{i.id} - {i.name}" for i in events]
        res = "Доступные мероприятия (id - название):\n" + "\n".join(events)
        await message.answer(res)
    except Exception as e:
        logger.error(f"Error getting user events: {e}")
        await message.answer("Произошла ошибка при получении мероприятий!")
        return
    await message.answer("Введите id мероприятия для редактирования:")
    await state.set_state(Arbeit.redact_event_name.state)

@dp.message(F.text, Arbeit.redact_event_name)
async def cmd_redact_name(message: Message, state: FSMContext):
    try:
        id = int(message.text)
        await state.update_data(id=id)
    except Exception as e:
        logger.error(f"Error getting event: {e}")
        await message.answer("Произошла ошибка при получении мероприятия!")
        await state.clear()
        return
    builder = InlineKeyboardBuilder()
    builder.button(text='Изменить название мероприятия', callback_data='name_change')
    builder.button(text='Изменить описание мероприятия', callback_data='desc_change')
    builder.adjust(1, 1, 2)
    await message.answer('Выберите действие:', reply_markup=builder.as_markup())


@dp.callback_query(F.data=='name_change', Arbeit.redact_event_name)
async def name_change(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое название мероприятия:")
    await state.set_state(Arbeit.change_event_name.state)

@dp.message(F.text, Arbeit.change_event_name)
async def name_change_end(message: Message, state: FSMContext):
    new_name = message.text
    try:
        data = await state.get_data()
        st = await usecase.update_event(EventData(new_name, None, None), data["id"], message.from_user.id)
        if st != data["id"]:
            raise(Exception("Error updating event data"))
        await message.answer("Название мероприятия изменено!")
        await state.clear()
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        await message.answer("Произошла ошибка при изменении названия мероприятия!")
        await state.clear()
        return

@dp.callback_query(F.data=='desc_change', Arbeit.redact_event_name)
async def desc_change(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое описание мероприятия:")
    await state.set_state(Arbeit.change_event_desc.state)

@dp.message(F.text, Arbeit.change_event_desc)
async def desc_change_end(message: Message, state: FSMContext):
    new_desc = message.text
    try:
        data = await state.get_data()
        st = await usecase.update_event(EventData(None, new_desc, None), data["id"], message.from_user.id)
        if st != data["id"]:
            raise(Exception("Error updating event data"))
        await message.answer("Описание мероприятия изменено!")
        await state.clear()
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        await message.answer("Произошла ошибка при изменении описания мероприятия!")
        await state.clear()
        return


@dp.message(Command("generate"), RoleFilter([RoleEnum.ADMIN, RoleEnum.ORGANIZER]), State(None))
async def cmd_generate_start(message: Message, state: FSMContext):
    await message.answer("Введите id мероприятия для создания QR-кода")
    try:
        events = await usecase.get_all_user_events(message.from_user.id)
        if events == []:
            await message.answer("У вас нет доступных мероприятий")
            await state.clear()
            return
        events = [f"{i.id} - {i.name}" for i in events]
        res = "Доступные мероприятия (id - название):\n" + "\n".join(events)
        await message.answer(res)
    except Exception as e:
        logger.error(f"Error getting user events: {e}")
        await message.answer("Произошла ошибка при получении мероприятий!")
        await state.clear()
        return
    await state.set_state(Arbeit.code_event_name.state)

@dp.message(F.text, Arbeit.code_event_name)
async def cmd_generate_name(message: Message, state: FSMContext):
    try:
        id = int(message.text)
        event = await repo.get_event_by_id(id)
        if event is None:
            raise(ValueError)
        await state.update_data(event_id=id)
    except ValueError:
        await message.answer("❌Мероприятие с таким id не найдено")
        # await state.clear()
        return
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        await message.answer("Произошла ошибка при получении мероприятий!")
        await state.clear()
        return
    await message.answer(f"Этапы мероприятия:\n"+'\n'.join([f'{i.id} - {i.name}' for i in event.points]))
    await message.answer("Введите id этапа мероприятия для создания QR-кода")
    await state.set_state(Arbeit.code_event_part.state)

@dp.message(F.text, Arbeit.code_event_part)
async def cmd_generate_part(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        event_id = data["event_id"]
        event = await repo.get_event_by_id(event_id)
        id = int(message.text)
    except ValueError:
        await message.answer("Введен неверный id.")
        return
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        await message.answer("Произошла ошибка при получении мероприятий!")
        await state.clear()
        return
    if id not in [point.id for point in event.points]:
        await message.answer("❌Этап мероприятия с таким id не найден!")
        # await state.clear()
        return
    photo = qrcode.make(id)
    with tempfile.NamedTemporaryFile() as tmp:
        photo.save(tmp)
        photo = FSInputFile(tmp.name)
        await message.answer_photo(photo, caption="Вот ваш QR-код!")
    await state.clear()


@dp.message()
async def prtext(message: Message):
    await message.answer("Бот не поддерживает произвольный ввод текста")

def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands="start", state="*")
    dp.register_message_handler(cmd_cancel, commands="cancel", state="*")

async def start_bot(user_role: RoleEnum=RoleEnum.UNREGISTER, chat_id: int=None):
    match user_role:
      case RoleEnum.ORGANIZER:
        commands =[BotCommand(command='start', description='старт работы с ботом'),
                BotCommand(command='reg', description='регистрация пользователя'),
                BotCommand(command='event', description='зарегистрировать мероприятие'),
                BotCommand(command='redact', description='редактировать мероприятие'),
                BotCommand(command='generate', description='создать qr-код для этапа'),
                BotCommand(command='info',description = 'вывести информацию о мероприятиях'),
                BotCommand(command='leaderboard', description='вывести таблицу лидеров'),
                BotCommand(command='feedback', description='отправить обратную связь'),
                BotCommand(command='cancel', description='отменить текущее действие')]
      case RoleEnum.PARTICIPANT:
        commands =[BotCommand(command='start', description='старт работы с ботом'),
                  BotCommand(command='info',description = 'вывести информацию о мероприятиях'),
                  BotCommand(command='scan', description='сканировать qr-код'),
                  BotCommand(command='leaderboard', description='вывести таблицу лидеров'),
                  BotCommand(command='feedback', description='отправить обратную связь'),
                  BotCommand(command='cancel', description='отменить текущее действие')]
      case RoleEnum.UNREGISTER:
        commands =[BotCommand(command='start', description='старт работы с ботом'),
                  BotCommand(command='reg', description='регистрация пользователя'),
                  BotCommand(command='cancel', description='отменить текущее действие')]
      case RoleEnum.ADMIN:
        commands = [BotCommand(command='start', description='старт работы с ботом'),
                BotCommand(command='scan', description='сканировать qr-код'),
                BotCommand(command='reg', description='регистрация пользователя'),
                BotCommand(command='event', description='зарегистрировать мероприятие'),
                BotCommand(command='redact', description='редактировать мероприятие'),
                BotCommand(command='generate', description='создать qr-код для этапа'),
                BotCommand(command='info',description = 'вывести информацию о мероприятиях'),
                BotCommand(command='leaderboard', description='вывести таблицу лидеров'),
                BotCommand(command='feedback', description='отправить обратную связь'),
                BotCommand(command='cancel', description='отменить текущее действие')]
    if chat_id is None:
        await bot.set_my_commands(commands, BotCommandScopeDefault())
    else:
        await bot.set_my_commands(commands, BotCommandScopeChat(chat_id=chat_id))
async def main():
    #тут из бд брать роль пользовател
    dp.startup.register(start_bot)
    sheduler.start()
    try:
      print("Бот запущен...")
      await bot.delete_webhook(drop_pending_updates=True)
      await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
      await bot.session.close()
      print("Бот остановлен")


if __name__=="__main__":
    asyncio.run(main())