from telebot import TeleBot
from telebot.types import Message
from md2tgmd import escape
import traceback
from config import conf
from database import db
import gemini
from keyboards import get_start_keyboard, get_switch_keyboard
from telebot.types import CallbackQuery


def extract_command_argument(message: Message) -> str:
    """Return the text following the command in a message or caption."""
    text = (message.text or message.caption or "").strip()
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

error_info              =       conf["error_info"]
before_generate_info    =       conf["before_generate_info"]
download_pic_notify     =       conf["download_pic_notify"]
model_1                 =       conf["model_1"]
model_2                 =       conf["model_2"]

gemini_chat_dict        = gemini.gemini_chat_dict
gemini_pro_chat_dict    = gemini.gemini_pro_chat_dict
default_model_dict      = gemini.default_model_dict
gemini_draw_dict        = gemini.gemini_draw_dict

async def start(message: Message, bot: TeleBot) -> None:
    try:
        await bot.reply_to(
            message,
            escape("Добро пожаловать! Выберите действие или просто напишите ваш вопрос."),
            reply_markup=get_start_keyboard(),
            parse_mode="MarkdownV2",
        )
    except IndexError:
        await bot.reply_to(message, error_info)

async def gemini_stream_handler(message: Message, bot: TeleBot) -> None:
    m = extract_command_argument(message)
    if not m:
        await bot.reply_to(
            message,
            escape("Пожалуйста, добавьте текст после /gemini.\nНапример: `/gemini Кто такой Джон Леннон?`"),
            parse_mode="MarkdownV2",
        )
        return
    await gemini.gemini_stream(bot, message, m, model_1)

async def gemini_pro_stream_handler(message: Message, bot: TeleBot) -> None:
    m = extract_command_argument(message)
    if not m:
        await bot.reply_to(
            message,
            escape("Пожалуйста, добавьте текст после /gemini_pro.\nНапример: `/gemini_pro Кто такой Джон Леннон?`"),
            parse_mode="MarkdownV2",
        )
        return
    await gemini.gemini_stream(bot, message, m, model_2)

async def clear(message: Message, bot: TeleBot) -> None:
    await clear_history_logic(message.from_user.id, bot, message)

async def clear_history_logic(user_id, bot, message=None):
    uid = str(user_id)
    if uid in gemini_chat_dict:
        del gemini_chat_dict[uid]
    if uid in gemini_pro_chat_dict:
        del gemini_pro_chat_dict[uid]
    if uid in gemini_draw_dict:
        del gemini_draw_dict[uid]

    db.clear_history(user_id)
    if message:
        await bot.reply_to(message, "История очищена")

async def switch(message: Message, bot: TeleBot) -> None:
    if message.chat.type != "private":
        await bot.reply_to(message, "Эта команда доступна только в личном чате!")
        return

    user_id = str(message.from_user.id)
    current_model = db.get_user_model(user_id) or model_1

    await bot.reply_to(
        message,
        f"Текущая модель: {current_model}",
        reply_markup=get_switch_keyboard(current_model)
    )

async def callback_handler(call: CallbackQuery, bot: TeleBot) -> None:
    user_id = str(call.from_user.id)

    if call.data == "switch_menu":
        current_model = db.get_user_model(user_id) or model_1
        await bot.edit_message_text(
            f"Выберите модель (Текущая: {current_model})",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_switch_keyboard(current_model)
        )

    elif call.data.startswith("set_model_"):
        new_model = call.data.replace("set_model_", "")
        db.set_user_model(user_id, new_model)

        # Update keyboard to show checkmark
        await bot.edit_message_text(
            f"Модель изменена на {new_model}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_switch_keyboard(new_model)
        )
        await bot.answer_callback_query(call.id, f"Установлено: {new_model}")

    elif call.data == "clear_history":
        await clear_history_logic(user_id, bot)
        await bot.answer_callback_query(call.id, "История очищена")
        await bot.send_message(call.message.chat.id, "✅ История диалога была очищена.")

    elif call.data == "back_to_start":
        await bot.edit_message_text(
            escape("Добро пожаловать! Выберите действие."),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_start_keyboard(),
            parse_mode="MarkdownV2"
        )

    elif call.data == "help_info":
        help_text = escape(
            "📚 Справка:\n"
            "/gemini - вопрос Flash модели\n"
            "/gemini_pro - вопрос Pro модели\n"
            "/draw - генерация изображений\n"
            "/edit - редактирование (отправьте фото)\n"
            "/switch - смена модели по умолчанию\n"
            "/clear - сброс контекста"
        )
        await bot.edit_message_text(
            help_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=get_start_keyboard(),
            parse_mode="MarkdownV2"
        )

    elif call.data == "help_draw":
        await bot.answer_callback_query(call.id, "Используйте /draw <запрос>")

async def gemini_private_handler(message: Message, bot: TeleBot) -> None:
    m = message.text.strip()
    user_id = str(message.from_user.id)

    current_model = db.get_user_model(user_id)

    # If not set, default to model_1 (Flash) as per typical expectation,
    # OR follow original logic: "If not in default_model_dict -> set True -> use model_1"
    # Wait, `switch` original: "if not in dict: dict=False (Pro)".
    # `gemini_private_handler` original: "if not in dict: dict=True (Flash)".
    # So by default private chat uses Flash. Switch toggles it.

    if current_model is None:
        current_model = model_1
        db.set_user_model(user_id, model_1)

    await gemini.gemini_stream(bot, message, m, current_model)

async def gemini_voice_handler(message: Message, bot: TeleBot) -> None:
    if message.chat.type != "private":
        return

    try:
        file_info = await bot.get_file(message.voice.file_id)
        file_data = await bot.download_file(file_info.file_path)

        # User model preference
        user_id = str(message.from_user.id)
        current_model = db.get_user_model(user_id) or model_1

        await gemini.gemini_voice(bot, message, file_data, current_model)

    except Exception as e:
        traceback.print_exc()
        await bot.reply_to(message, error_info)

async def gemini_photo_handler(message: Message, bot: TeleBot) -> None:
    if message.chat.type != "private":
        s = message.caption or ""
        if not s or not (s.startswith("/gemini")):
            return
        m = extract_command_argument(message)
        try:
            file_path = await bot.get_file(message.photo[-1].file_id)
            photo_file = await bot.download_file(file_path.file_path)
        except Exception:
            traceback.print_exc()
            await bot.reply_to(message, error_info)
            return
        await gemini.gemini_edit(bot, message, m, photo_file)
    else:
        m = extract_command_argument(message)
        try:
            file_path = await bot.get_file(message.photo[-1].file_id)
            photo_file = await bot.download_file(file_path.file_path)
        except Exception:
            traceback.print_exc()
            await bot.reply_to(message, error_info)
            return
        await gemini.gemini_edit(bot, message, m, photo_file)

async def gemini_edit_handler(message: Message, bot: TeleBot) -> None:
    if not message.photo:
        await bot.reply_to(message, "Пожалуйста, отправьте фотографию")
        return
    m = extract_command_argument(message)
    try:
        file_path = await bot.get_file(message.photo[-1].file_id)
        photo_file = await bot.download_file(file_path.file_path)
    except Exception as e:
        traceback.print_exc()
        await bot.reply_to(message, str(e))
        return
    await gemini.gemini_edit(bot, message, m, photo_file)

async def draw_handler(message: Message, bot: TeleBot) -> None:
    m = extract_command_argument(message)
    if not m:
        await bot.reply_to(
            message,
            escape("Пожалуйста, добавьте, что нарисовать после /draw.\nНапример: `/draw нарисуй мне кота.`"),
            parse_mode="MarkdownV2",
        )
        return

    # reply to the message first, then delete the "drawing..." message
    drawing_msg = await bot.reply_to(message, "Рисую...")
    try:
        await gemini.gemini_draw(bot, message, m)
    finally:
        await bot.delete_message(chat_id=message.chat.id, message_id=drawing_msg.message_id)
