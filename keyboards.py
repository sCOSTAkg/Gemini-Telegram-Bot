from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import conf

model_1 = conf["model_1"]
model_2 = conf["model_2"]

def get_start_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🔄 Switch Model", callback_data="switch_menu"),
        InlineKeyboardButton("🗑️ Clear History", callback_data="clear_history")
    )
    keyboard.row(
        InlineKeyboardButton("🎨 Draw", callback_data="help_draw"), # Just a placeholder or help
        InlineKeyboardButton("❓ Help", callback_data="help_info")
    )
    return keyboard

def get_switch_keyboard(current_model):
    keyboard = InlineKeyboardMarkup()

    # Checkmark logic
    text_1 = f"✅ {model_1}" if current_model == model_1 else model_1
    text_2 = f"✅ {model_2}" if current_model == model_2 else model_2

    keyboard.row(InlineKeyboardButton(text_1, callback_data=f"set_model_{model_1}"))
    keyboard.row(InlineKeyboardButton(text_2, callback_data=f"set_model_{model_2}"))
    keyboard.row(InlineKeyboardButton("🔙 Back", callback_data="back_to_start"))
    return keyboard
