import argparse
import traceback
import asyncio
import re
import telebot
from telebot.async_telebot import AsyncTeleBot
import handlers
from config import conf, generation_config, safety_settings

# Init args
parser = argparse.ArgumentParser()
parser.add_argument("tg_token", help="токен Telegram")
parser.add_argument("GOOGLE_GEMINI_KEY", help="API‑ключ Google Gemini")
options = parser.parse_args()
print("Аргументы обработаны.")


async def main():
    # Init bot
    bot = AsyncTeleBot(options.tg_token)
    await bot.delete_my_commands(scope=None, language_code=None)
    await bot.set_my_commands(
    commands=[
        telebot.types.BotCommand("start", "Запуск"),
        telebot.types.BotCommand("gemini", f"использует {conf['model_1']}"),
        telebot.types.BotCommand("gemini_pro", f"использует {conf['model_2']}"),
        telebot.types.BotCommand("draw", "нарисовать изображение"),
        telebot.types.BotCommand("edit", "редактировать фото"),
        telebot.types.BotCommand("clear", "очистить историю"),
        telebot.types.BotCommand("switch","сменить модель по умолчанию")
    ],
)
    print("Бот инициализирован.")

    # Init commands
    bot.register_message_handler(handlers.start,                         commands=['start'],         pass_bot=True)
    bot.register_message_handler(handlers.gemini_stream_handler,         commands=['gemini'],        pass_bot=True)
    bot.register_message_handler(handlers.gemini_pro_stream_handler,     commands=['gemini_pro'],    pass_bot=True)
    bot.register_message_handler(handlers.draw_handler,                  commands=['draw'],          pass_bot=True)
    bot.register_message_handler(handlers.gemini_edit_handler,           commands=['edit'],          pass_bot=True)
    bot.register_message_handler(handlers.clear,                         commands=['clear'],         pass_bot=True)
    bot.register_message_handler(handlers.switch,                        commands=['switch'],        pass_bot=True)
    bot.register_message_handler(handlers.gemini_photo_handler,          content_types=["photo"],    pass_bot=True)
    bot.register_message_handler(
        handlers.gemini_private_handler,
        func=lambda message: message.chat.type == "private",
        content_types=['text'],
        pass_bot=True)

    # Start bot
    print("Запуск Gemini_Telegram_Bot.")
    await bot.polling(none_stop=True)

if __name__ == '__main__':
    asyncio.run(main())
