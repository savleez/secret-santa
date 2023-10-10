import logging
from enum import Enum
from os import getenv
from re import sub as re_sub

from dotenv import load_dotenv
from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    Update,
)
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
CHOOSING, TYPING_REPLY, TYPING_NAME = range(3)
conv_enders = ["Adios", "adios", "Chao", "chao"]


class KeyboardOptions(Enum):
    EDIT_NAME = "Editar mi nombre"
    EDIT_PREFS = "Editar mis preferencias"
    GET_RECIPIENT_NAME = "Consultar pareja"
    GET_RECIPIENT_PREFS = "Consultar preferencias de pareja"
    INSTRUCTIONS = "Reglas del juego"
    CONV_END = conv_enders[0]


def create_keyboard():
    keyboard = []
    row = []

    for i, item in enumerate(list(KeyboardOptions)):
        row.append(KeyboardButton(item.value))

        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /hola is issued."""

    chat_id = update.effective_chat.id
    Session = context.bot_data["session"]

    with Session() as session:
        participant = session.query(Participant).filter_by(chat_id=chat_id).first()

    if participant is None:
        await update.message.reply_text(
            "¡Hola! Bienvenido al juego de Niño Jesús Secreto",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            "¿Cómo te llamas?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return TYPING_NAME

    await update.message.reply_text(
        f"¡Hola {participant.name}! ¿Qué quieres hacer?",
        reply_markup=create_keyboard(),
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
        try:
            session.rollback()
        except Exception:
            pass

        await update.message.reply_text(
            "Parece ser que ya alguien se registró con ese nombre"
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            f"¿Me podrías indicar tu nombre completo?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return TYPING_NAME

    else:
        await update.message.reply_text(
            f"Muchas gracias, te acabo de registrar en el juego como {name}.",
        )

        await update.message.reply_text(
            "¿Qué quieres hacer?",
            reply_markup=create_keyboard(),
        )

        return CHOOSING


async def invalid_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for the valid choices."""

    global conv_enders

    usr_response = update.message.text.lower()
    if usr_response == "no" or usr_response in conv_enders:
        return await done(update, context)

    await update.message.reply_text(
        "Lo siento, no te entiendo, ¿puedes seleccionar una de las opciones?",
        reply_markup=create_keyboard(),
    )

    return CHOOSING


async def choice_reply_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ask the user for info about the selected predefined choice."""

    global conv_enders

    usr_response = update.message.text

    # TODO: Crear las funciones de cada opcion

    if usr_response.lower() == "no" or usr_response in conv_enders:
        return await done(update, context)

    elif usr_response == KeyboardOptions.EDIT_NAME.value:
        context.bot_data["choice"] = KeyboardOptions.EDIT_NAME.value
        await update.message.reply_text(
            "Entiendo que quieres actualizar tu nombre actual en el juego"
        )
        await update.message.reply_text("¿Me puedes decir cuál es tu nombre?")

        return TYPING_REPLY

    elif usr_response == KeyboardOptions.EDIT_PREFS.value:
        await update.message.reply_text("editar preferencias")

    elif usr_response == KeyboardOptions.GET_RECIPIENT_NAME.value:
        await update.message.reply_text("consultar nombre de pareja")

    elif usr_response == KeyboardOptions.GET_RECIPIENT_PREFS.value:
        await update.message.reply_text("consultar preferencias de pareja")

    elif usr_response == KeyboardOptions.INSTRUCTIONS.value:
        await update.message.reply_text("reglas del juego")

    elif usr_response == KeyboardOptions.CONV_END.value:
        await update.message.reply_text("terminar conversacion")

        return await done(update, context)

    return CHOOSING


async def process_typing_response(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    Session = context.bot_data["session"]
    chat_id = update.effective_chat.id
    choice = context.bot_data["choice"]
    usr_response = update.message.text

    with Session() as session:
        participant = (
            session.query(Participant).filter(Participant.chat_id == chat_id).first()
        )

        if not participant:
            raise ValueError("No se encontró el participante a modificar")

        if choice == KeyboardOptions.EDIT_NAME.value:
            participant.name = usr_response
            session.add(participant)
            session.commit()

            await update.message.reply_text(
                f"Muchas gracias, acabo de actualizar tu nombre en el juego por {participant.name}.",
            )

            await update.message.reply_text(
                "¿Qué quieres hacer?",
                reply_markup=create_keyboard(),
            )

            return CHOOSING


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text(
        "Help!",
        reply_markup=ReplyKeyboardRemove(),
    )


async def instructions_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /instrucciones is issued."""

    await update.message.reply_text("Instructiones!")


async def start_game_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text("Inicio de juego!")
    await update.message.reply_text("Repartiendo...")
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
    await update.message.reply_text(
        "Para iniciar una nueva conversación envía un mensaje diciendo: /hola"
    )


def main() -> None:
    """Start the bot."""
    global TOKEN, Session, engine, Base, reply_keyboard

    Base.metadata.create_all(engine)

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    context = CallbackContext(application, chat_id=None, user_id=None)

    context.bot_data["session"] = Session

    keyboard_options_reg = "|".join([option.value for option in list(KeyboardOptions)])
    conv_enders_reg = "|".join(["Adios", "adios", "Chao", "chao"])

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("hola", start)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex(f"^({keyboard_options_reg})$"),
                    choice_reply_handler,
                ),
                MessageHandler(
                    ~(filters.Regex(f"^({keyboard_options_reg})$")),
                    invalid_choice,
                ),
            ],
            TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    process_typing_response,
                )
            ],
            TYPING_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    register_participant,
                ),
                MessageHandler(
                    filters.TEXT
                    & (filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    done,
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{conv_enders_reg}$"), done)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("instrucciones", instructions_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
            echo,
        )
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
