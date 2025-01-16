import logging
import asyncio
from re import S
from types import new_class
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram import F
from aiogram.types import Message
from aiogram.types import FSInputFile
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand, BotCommandScopeDefault
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
from datetime import datetime
import qrcode
import cv2
from settings import settings
from models import *
import usecase


class Registration(StatesGroup):
  fio_wait=State()
  role_wait=State()

class Arbeit(StatesGroup):
  code_wait = State()
  code_event_name = State()
  code_event_part = State()
  redact_event_name = State()
  change_event_name = State()
  change_event_desc = State()


logging.basicConfig(force=True, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
bot = Bot(token=settings.TG_KEY, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

mero_list=['1','2','3']#имитация бд

@dp.message(CommandStart(), State(None))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer('Приветствую вас!\n Доступные команды:\n'+
                         '/start - старт\n'+
                         '/reg - регистрация\n'+
                         '/redact - редактировать мероприятие\n'+
                         '/generate - создать qr-код для этапа\n'+
                         '/cancel - Команда отмены действия\n'+
                         'Предлагаю вам начать с регистрации\n',
                          reply_markup=ReplyKeyboardRemove())




@dp.message(F.photo)  #Сканирование qr-кода
async def QrCodePhoto(message: types.Message):

    # инициализируем детектор QRCode cv2
    detector = cv2.QRCodeDetector()
    # обнаружить и декодировать
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_path = f"./{file_info.file_unique_id}.jpg"
    await bot.download_file(file_info.file_path, destination=file_path)
    img = cv2.imread(file_path)
    data, bbox, straight_qrcode = detector.detectAndDecode(img)

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        file_path = f"./{file_info.file_unique_id}.jpg"
        await bot.download_file(file_info.file_path, destination=file_path)
        img = Image.open(file_path)
        decoded_objects = decode(img)
        if decoded_objects:
            result_text = "\n".join([obj.data.decode("utf-8") for obj in decoded_objects])
            usecase.add_point_to_user(PointUserData(int(result_text), None), message.from_user.id)
            await message.answer(f"Найденный QR-код:\n{result_text}")
        else:
            await message.answer("QR-код не найден. Попробуй еще раз.")
    except Exception as e:
        logging.error(f"Ошибка при обработке QR-кода: {e}")
        await message.answer("Произошла ошибка при обработке фотографии. Попробуй еще раз.")


@dp.message(Command("cancel"), State(None))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup= ReplyKeyboardRemove())


sample_scanlist=['12345','qwerty']
@dp.message(Command("scan"), State(None))
async def cmd_scan_call(message: Message, state: FSMContext):
    await message.answer("Отсканируйте qr-код и отправьте результат сообщением")
    await state.set_state(Arbeit.code_wait.state)

@dp.message(F.text,Arbeit.code_wait)
async def cmd_scan_end(message: Message, state: FSMContext):
    if message.text not in sample_scanlist:
        await message.answer("QR-код не найден")
        return
    await message.answer("QR-код найден. Баллы начисленны")
    await state.clear()



userdata = {'Name1': "", 'Name2': "", 'Name3': "",'Role': ""} #тут уже ты из бд как-то сделаешь

roles = [
        [KeyboardButton(text='Участник')],
        [KeyboardButton(text='Организатор')]
        ]
roles_logic = ["участник", "организатор"]

@dp.message(Command("reg"), State(None))  #Регистрация пользователя
async def cmd_reg_start(message: Message,state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(keyboard=roles, resize_keyboard=True)
    await message.answer("Выберете роль:", reply_markup=keyboard)
    await state.set_state(Registration.role_wait.state)

@dp.message(F.text,Registration.role_wait)
async def cmd_reg_role(message: types.Message, state: FSMContext):
    if message.text.lower() not in roles_logic:
        await message.answer("Пожалуйста, выберите роль, используя клавиатуру ниже.")
        return
    await state.update_data(Role = message.text.lower())
#    await message.answer("Вы выбрали роль: " + message.text.lower())
    await state.set_state(Registration.fio_wait.state)
    await message.answer("Введите своё ФИО через клавиатуру:", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text, Registration.fio_wait)
async def cmd_reg_fio(message: types.Message, state: FSMContext):
    if len(message.text.split()) != 3:
      await message.answer(f'ФИО введено некорректно. Повторите ввод')
      return
    await message.answer(f'ФИО принято!')
    user_fio = await state.get_data()
    await state.clear()


@dp.callback_query(F.data == 'member')
async def send_content(call: CallbackQuery):
    userdata['Role'] = 'member'
    await call.message.answer("Вы выбрали вышу роль", reply_markup=types.ReplyKeyboardRemove())
    await call.answer('Выбрана роль участника', show_alert=True)


@dp.callback_query(F.data == 'organisator')
async def send_content(call: CallbackQuery):
    userdata['Role'] = 'organisator'
    await call.message.answer("Вы выбрали вышу роль", reply_markup=types.ReplyKeyboardRemove())
    await call.answer('Выбрана роль участника', show_alert=True)


class event_reg(StatesGroup):
  place_wait = State()
  description_wait = State()


event_data = {'date':'', 'name':'','description':''}


@dp.message( Command("event"), State(None))
async def cmd_event_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название вашего мероприятия")
    event_data['date'] =await state.get_data()
    await state.set_state(event_reg.place_wait.state)

@dp.message(F.text, event_reg.place_wait)
async def cmd_event_place(message: types.Message, state: FSMContext):
    event_data['name'] = await state.get_data()
    await message.answer("Введите описание вашего мероприятия:")
    await state.set_state(event_reg.description_wait.state)


@dp.message(F.text, event_reg.description_wait)
async def cmd_event_description(message: types.Message, state: FSMContext):
    event_data['description'] = await state.get_data()
    await state.clear()
    await message.answer("Ваше мероприятие зарегистрированно!")


@dp.message(Command("redact"), State(None))
async def cmd_redact_start(message: Message, state: FSMContext):
    await message.answer("Введите название мероприятия для редактирования:")
    await state.set_state(Arbeit.redact_event_name.state)

@dp.message(F.text, Arbeit.redact_event_name)
async def cmd_redact_name(message: Message, state: FSMContext):
    if message.text not in mero_list:
        await message.answer("Мероприятие с таким названием не найдено")
        return
    await message.answer("Выберете действие:")
    builder = InlineKeyboardBuilder()
    builder.button(text='Изменить название мероприятия', callback_data='name_change')
    builder.button(text='Изменить описание мероприятия', callback_data='desc_change')
    builder.adjust(1, 1, 2)
    await message.answer('Выберите действие:', reply_markup=builder.as_markup())
    await state.clear()


@dp.callback_query(F.data=='name_change',State(None))
async def name_change(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое название мероприятия:")
    await state.set_state(Arbeit.change_event_name.state)

@dp.message(F.text, Arbeit.change_event_name)
async def name_change_end(message: Message, state: FSMContext):
    new_name = message.text
    await message.answer("Название мероприятия изменено!")

    await state.clear()


@dp.callback_query(F.data=='desc_change', State(None))
async def desc_change(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введите новое описание мероприятия:")
    await state.set_state(Arbeit.change_event_desc.state)

@dp.message(F.text, Arbeit.change_event_desc)
async def desc_change_end(message: Message, state: FSMContext):
    await message.answer("Описание мероприятия изменено!")
    new_desc = message.text
    await state.clear()





@dp.message(Command("generate"), State(None))
async def cmd_generate_start(message: Message, state: FSMContext):
    await message.answer("Введите название мероприятия для создания QR-кода")
    await state.set_state(Arbeit.code_event_name.state)

@dp.message(F.text, Arbeit.code_event_name)
async def cmd_generate_name(message: Message, state: FSMContext):
    if message.text not in sample_scanlist:
        await message.answer("❌Мероприятие с таким названием не найдено")
        return
    code_name = message.text
    await message.answer("Введите этап мероприятия для создания QR-кода")
    await state.set_state(Arbeit.code_event_part.state)

@dp.message(F.text, Arbeit.code_event_part)
async def cmd_generate_part(message: Message, state: FSMContext):
    if message.text not in mero_list:
        await message.answer("❌Этапа с таким названием не найдено")
        return
    code_part = message.text
    photo = qrcode.make('тут что-то для qr-кода')
    temp_file_path = "qr_code.png"
    photo.save(temp_file_path)
    photo = FSInputFile(temp_file_path)
    await message.answer_photo(photo, caption="Вот ваш QR-код!")
    await state.clear()


@dp.message()
async def prtext(message: Message, state: FSMContext):
    await message.answer("Нельзя писать произвольный текст)")

def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands="start", state="*")
    dp.register_message_handler(cmd_cancel, commands="cancel", state="*")

async def start_bot():
    commands = [#BotCommand(command='scan', description='сканировать qr-код'),
                BotCommand(command='start', description='старт работы с ботом'),
                BotCommand(command='reg', description='регистрация пользователя'),
                BotCommand(command='event', description='зарегистрировать мероприятие'),
                BotCommand(command='redact', description='редактировать мероприятие'),
                BotCommand(command='generate', description='создать qr-код для этапа')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())



async def main():
    logging.basicConfig(level=logging.INFO)
    dp.startup.register(start_bot)
    try:
      print("Бот запущен...")
      await bot.delete_webhook(drop_pending_updates=True)
      await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
      await bot.session.close()
      print("Бот остановлен")



if __name__ == '__main__':
    asyncio.run(main())