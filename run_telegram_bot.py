import logging
from os import getenv
from re import sub as re_sub

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    Updater,
    CallbackContext,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError


from secret_santa.models import Participant
from secret_santa.database import Base
from tests.database import Session, engine

load_dotenv()
TOKEN = getenv("TELEGRAM_TOKEN")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Bot
TYPE_NAME_REPLY, CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(4)

# reply_keyboard = [
#     ["Age", "Favourite colour"],
#     ["Number of siblings", "Something else..."],
#     ["Done"],
# ]
# markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /hola is issued."""

    chat_id = update.effective_chat.id
    Session = context.bot_data["session"]

    with Session() as session:
        participant = session.query(Participant).filter_by(chat_id=chat_id).first()

    if participant is None:
        await update.message.reply_text(
            "¡Hola! Bienvenido al juego de Niño Jesús Secreto\n¿Cómo te llamas?",
        )

        return TYPING_REPLY

    await update.message.reply_text(
        f"¡Hola {participant.name}! ¿Quieres preguntarme algo?",
    )

    return CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Say goodbye"""

    await update.message.reply_text(
        f"¡Hasta la próxima!",
        reply_markup=ReplyKeyboardRemove(),
    )

    return ConversationHandler.END


async def register_participant(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Save the participant name and chat_id on database."""

    name = update.message.text
    chat_id = update.effective_chat.id
    Session = context.bot_data["session"]
    new_participant = Participant(chat_id=chat_id, name=name)

    try:
        with Session() as session:
            exists = (
                session.query(Participant.name)
                .filter(func.lower(Participant.name) == name.lower())
                .first()
            )

        if exists:
            raise ValueError("Name is already taken.")

        session.add(new_participant)
        session.commit()

    except (IntegrityError, ValueError):
        # session.rollback()
        await update.message.reply_text(
            "Parece ser que ya alguien se registró con ese nombre"
            f"\n¿Me podrías indicar tu nombre completo?",
        )

        return TYPING_REPLY

    else:
        await update.message.reply_text(
            f"Muchas gracias {name}, te acabo de registrar en el juego.",
        )

        return CHOOSING


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text("Help!")


async def instructions_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /instrucciones is issued."""

    await update.message.reply_text("Instructiones!")


async def start_game_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text("Inicio de juego!\nRepartiendo...")
    await update.message.reply_text("Kidding!")


async def get_all_participants_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text("Lista de participantes:{lista}")


async def delete_participant_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    # TODO: Mostrar lista de participantes como opciones y preguntar si está seguro
    await update.message.reply_text("Eliminado!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""

    new_message = re_sub("[aeiouAEIOU]", "i", update.message.text)

    await update.message.reply_text(new_message)


def main() -> None:
    """Start the bot."""
    global TOKEN, Session, engine, Base

    Base.metadata.create_all(engine)

    # session = Session()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    context = CallbackContext(application, chat_id=None, user_id=None)

    context.bot_data["session"] = Session
    # dispatcher.bot_data["session"] = session

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("hola", start)],
        states={
            CHOOSING: [
                # MessageHandler(
                #     filters.Regex("^(Age|Favourite colour|Number of siblings)$"),
                #     regular_choice,
                # ),
                # MessageHandler(filters.Regex("^Something else...$"), custom_choice),
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")),
                    echo,
                )
            ],
            # TYPING_CHOICE: [
            #     MessageHandler(
            #         filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")),
            #         regular_choice,
            #     )
            # ],
            TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Adios$")),
                    register_participant,
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("instrucciones", instructions_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")),
            echo,
        )
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
