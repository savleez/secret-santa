from typing import List

from telegram import ReplyKeyboardMarkup, KeyboardButton

from telegram_bot.settings import KeyboardOptions


def create_keyboard(
    options: List[str | KeyboardOptions] = list(KeyboardOptions),
):
    keyboard = []
    row = []

    options = (
        [option.value for option in options]
        if isinstance(options[0], KeyboardOptions)
        else options
    )

    for i, item in enumerate(options):
        row.append(KeyboardButton(item))

        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
