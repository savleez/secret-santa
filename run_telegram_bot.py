import logging
from enum import Enum
from os import getenv
from re import sub as re_sub
from typing import List

# from secrets import choice
from random import choice, shuffle

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
    CallbackContext,
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import InstrumentedAttribute


from secret_santa.models import Participant
from secret_santa.database import Base, Session, engine

# from tests.database import Session, engine

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
(
    CHOOSING,
    TYPING_REPLY,
    TYPING_NAME,
    DELETE_PARTICIPANT,
    START_GAME,
    CONFIRM_YES_OR_NO,
) = range(6)

conv_enders = ["Adios", "adios", "Chao", "chao", "Cancelar", "cancelar"]

GAME_RULES = """
Este es un asistente para el juego de niño Jesús secreto.

Cada uno de los participantes le escribirá desde su celular al bot para que este los registre.
Cada participante deberá indicarle al bot su nombre, preferiblemente completo para evitar confusiones,
y tendrá la posibilidad de indicarle también sus preferencias.

Una vez todos los participantes estén listos, se dará inicio al juego y el bot le informará
a cada participante quién es su pareja.

Mientras dure el juego, cada participante podrá preguntarle al bot nuevamente por su pareja
y también por las preferencias que su pareja haya indicado.

Todo esto se maneja de forma secreta, puesto que una vez iniciado el juego, nadie tiene acceso a la información
que se le indique al bot. 
"""


class KeyboardOptions(Enum):
    GET_INFO = "Ver mi información"
    EDIT_NAME = "Editar mi nombre"
    EDIT_PREFS = "Editar mis preferencias"
    GET_RECIPIENT_NAME = "Consultar pareja"
    GET_RECIPIENT_PREFS = "Consultar preferencias de pareja"
    INSTRUCTIONS = "Reglas del juego"
    CONV_END = conv_enders[0]


def create_keyboard(options: List[str | KeyboardOptions] = list(KeyboardOptions)):
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


def get_participant(chat_id: str) -> Participant:
    with Session() as session:
        participant = (
            session.query(Participant).filter(Participant.chat_id == chat_id).first()
        )

    return participant


def get_participant_recipient(participant: Participant) -> Participant:
    with Session() as session:
        participant = (
            session.query(Participant)
            .filter(Participant.chat_id == participant.chat_id)
            .first()
        )

        recipient = participant.recipient

    return recipient


def get_all_participants() -> List[Participant]:
    with Session() as session:
        participants = session.query(Participant).all()

    return participants


def delete_participant(chat_id: str = None, participant_name: str = None):
    deleted = False

    with Session() as session:
        try:
            if chat_id:
                participant = (
                    session.query(Participant)
                    .filter(Participant.chat_id == chat_id)
                    .first()
                )
            else:
                participant = (
                    session.query(Participant)
                    .filter(Participant.name == participant_name)
                    .first()
                )

            session.delete(participant)
            session.commit()
            deleted = True

        except:
            try:
                session.rollback()
            except:
                pass

    return deleted


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /hola is issued."""

    chat_id = update.effective_chat.id

    with Session() as session:
        participant = (
            session.query(Participant).filter(Participant.chat_id == chat_id).first()
        )

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
            "Parece ser que ya alguien se registró con ese nombre",
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
            reply_markup=ReplyKeyboardRemove(),
        )

        await update.message.reply_text(
            "¿Qué quieres hacer?",
            reply_markup=create_keyboard(),
        )

        return CHOOSING


async def choice_reply_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ask the user for info about the selected predefined choice."""

    global conv_enders, GAME_RULES

    usr_response = update.message.text
    context.bot_data["choice"] = usr_response

    if usr_response in conv_enders:
        return await done(update, context)

    participant = get_participant(chat_id=update.effective_chat.id)

    if usr_response == KeyboardOptions.GET_INFO.value:
        await update.message.reply_text(
            f"Actualmente tengo guardado que te llamas {participant.name}",
            reply_markup=ReplyKeyboardRemove(),
        )

        if participant.preferences is None or len(participant.preferences) == 0:
            await update.message.reply_text(
                "Y actualmente no tienes preferencias guardadas.",
                reply_markup=ReplyKeyboardRemove(),
            )

        else:
            await update.message.reply_text(
                "También tengo guardado que tus preferencias son:"
                f'\n"{participant.preferences}"',
                reply_markup=ReplyKeyboardRemove(),
            )

    elif usr_response == KeyboardOptions.EDIT_NAME.value:
        await update.message.reply_text(
            "Entiendo que quieres actualizar tu nombre actual en el juego",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            f"Actualmente tengo registrado que tu nombre es: {participant.name}",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            "¿Me puedes decir cuál es tu nombre?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return TYPING_REPLY

    elif usr_response == KeyboardOptions.EDIT_PREFS.value:
        await update.message.reply_text(
            "Entiendo que quieres actualizar tus preferencias de regalo en el juego",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            "En tus preferencias puedes indicar cosas como tu talla de ropa o de zapatos,"
            "o si tienes alguna preferencia en particular que pueda interesar a la persona que te tiene",
            reply_markup=ReplyKeyboardRemove(),
        )

        if participant.preferences is None or len(participant.preferences) == 0:
            await update.message.reply_text(
                "Actualmente no tienes preferencias guardadas",
                reply_markup=ReplyKeyboardRemove(),
            )

        else:
            await update.message.reply_text(
                "Actualmente tus preferencias guardadas son:"
                f"\n{participant.preferences}",
                reply_markup=ReplyKeyboardRemove(),
            )

        await update.message.reply_text(
            "¿Me puedes decir cuáles son tus preferencias?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return TYPING_REPLY

    elif usr_response == KeyboardOptions.GET_RECIPIENT_NAME.value:
        await update.message.reply_text(
            "Entiendo que quieres consultar quién es tu pareja en el juego",
            reply_markup=ReplyKeyboardRemove(),
        )

        recipient = get_participant_recipient(participant=participant)

        if recipient is None:
            await update.message.reply_text(
                "Pero todavía no se han asignado las parejas",
                reply_markup=ReplyKeyboardRemove(),
            )

        else:
            await update.message.reply_text(
                f"Recuerda no decirle a nadie, tu pareja es: {recipient.name}",
                reply_markup=ReplyKeyboardRemove(),
            )

    elif usr_response == KeyboardOptions.GET_RECIPIENT_PREFS.value:
        recipient = get_participant_recipient(participant=participant)

        if recipient is None:
            await update.message.reply_text(
                "Pero todavía no se han asignado las parejas",
                reply_markup=ReplyKeyboardRemove(),
            )

        else:
            await update.message.reply_text(
                f"Las preferencias de tu pareja son:\n{recipient.preferences}",
                reply_markup=ReplyKeyboardRemove(),
            )

    elif usr_response == KeyboardOptions.INSTRUCTIONS.value:
        await update.message.reply_text(
            GAME_RULES,
            reply_markup=ReplyKeyboardRemove(),
        )

    elif usr_response == KeyboardOptions.CONV_END.value:
        return await done(update, context)

    else:
        await update.message.reply_text(
            "Lo siento, no entiendo lo que dijiste"
            "\n¿Puedes seleccionar una de las opciones disponibles?",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            "También puedes decir /ayuda para ver las opciones disponibles",
            reply_markup=create_keyboard(),
        )

    await update.message.reply_text(
        "¿Quieres hacer algo más?",
        reply_markup=create_keyboard(),
    )

    return CHOOSING


async def yes_or_no_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /ayuda is issued."""

    global conv_enders

    usr_response = update.message.text
    action = context.bot_data.get("action")

    if usr_response in conv_enders or usr_response.lower() == "no":
        return await done(update, context)

    if action == "delete_participant":
        return await delete_participant_handler(update, context)

    elif action == "start_game":
        return START_GAME

    else:
        await update.message.reply_text(
            "Parece que hubo un error"
            "\nSi quieres intentarlo de nuevo envía el comando nuevamente",
            reply_markup=ReplyKeyboardRemove(),
        )

        return done(update, context)


async def delete_participant_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    global conv_enders

    usr_response = update.message.text
    participant_to_delete = context.bot_data.get("participant_to_delete")

    if usr_response in conv_enders:
        return await done(update, context)

    if not participant_to_delete:
        context.bot_data["participant_to_delete"] = usr_response
        context.bot_data["action"] = "delete_participant"

        await update.message.reply_text(
            f"¿Seguro que quieres eliminar al participante {usr_response}?",
            reply_markup=create_keyboard(["Si", "No"]),
        )

        return CONFIRM_YES_OR_NO

    deleted = delete_participant(participant_name=participant_to_delete)

    if deleted:
        await update.message.reply_text(
            f"El participante {participant_to_delete} fue eliminado"
            "\nSi se quiere registrar nuevamente deberá mandar /hola al bot",
            reply_markup=ReplyKeyboardRemove(),
        )

    else:
        await update.message.reply_text(
            "Hubo un error desconocido y el participante no se eliminó.",
            reply_markup=ReplyKeyboardRemove(),
        )


async def process_typing_response(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

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
                reply_markup=ReplyKeyboardRemove(),
            )

            await update.message.reply_text(
                "¿Qué quieres hacer?",
                reply_markup=create_keyboard(),
            )

            return CHOOSING

        if choice == KeyboardOptions.EDIT_PREFS.value:
            participant.preferences = usr_response
            session.add(participant)
            session.commit()

            await update.message.reply_text(
                f"Muchas gracias, acabo de actualizar tus preferencias.",
                reply_markup=ReplyKeyboardRemove(),
            )

            await update.message.reply_text(
                "¿Quieres hacer algo más?",
                reply_markup=create_keyboard(),
            )

            # if participant.recipient is not None:

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

    global GAME_RULES

    await update.message.reply_text(
        GAME_RULES,
        reply_markup=ReplyKeyboardRemove(),
    )

    await update.message.reply_text(
        "Recuerda que puedes iniciar una nueva conversación enviando un mensaje diciendo: /hola",
        reply_markup=ReplyKeyboardRemove(),
    )


async def start_game_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text(
        "Inicio de juego!",
        reply_markup=ReplyKeyboardRemove(),
    )

    participants = get_all_participants()

    if len(participants) < 2:
        await update.message.reply_text(
            "¡El juego no puede iniciar con menos de 3 personas!"
            "Para consultar la lista de participantes envíe como mensaje /participantes",
            reply_markup=ReplyKeyboardRemove(),
        )

        return await done(update, context)

    if not all([isinstance(participant, Participant) for participant in participants]):
        raise ValueError("The participants must be Person instances.")

    participants_copy = participants.copy()
    shuffle(participants_copy)

    for participant in participants:
        possible_recipient = participant

        while possible_recipient == participant:
            possible_recipient = choice(participants_copy)

        update_participant_recipient(
            participant=participant,
            recipient=possible_recipient,
        )

        participants_copy.remove(possible_recipient)

    # participants = get_all_participants()
    # assert (
    #     all([participant.recipient is not None for participant in participants]) == True
    # )

    await update.message.reply_text(
        "¡Se asignaron las parejas!",
        reply_markup=ReplyKeyboardRemove(),
    )


def update_participant_recipient(participant: Participant, recipient: Participant):
    with Session() as session:
        participant = (
            session.query(Participant).filter(Participant.id == participant.id).first()
        )

        participant.recipient_id = recipient.id
        session.commit()
        session.refresh(participant)


async def get_all_participants_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    participants = get_all_participants()
    names = [
        participant.name for participant in participants if participant.name is not None
    ]

    if len(names) == 0:
        await update.message.reply_text(
            "Todavía no se han registrado participantes",
            reply_markup=ReplyKeyboardRemove(),
        )

    else:
        await update.message.reply_text(
            f"De momento hay {len(names)} participantes: {', '.join(names)}",
            reply_markup=ReplyKeyboardRemove(),
        )

    await update.message.reply_text(
        "Recuerda que puedes registrarte e iniciar una nueva conversación enviando un mensaje diciendo: /hola",
        reply_markup=ReplyKeyboardRemove(),
    )


async def delete_participant_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    participants = get_all_participants()

    names = [
        participant.name for participant in participants if participant.name is not None
    ]

    await update.message.reply_text(
        "Entiendo que quieres eliminar a uno de los participantes"
        "\nPor favor selecciona el participante a eliminar",
        reply_markup=create_keyboard(options=names),
    )

    return DELETE_PARTICIPANT


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""

    new_message = re_sub("[aeiouAEIOU]", "i", update.message.text)

    await update.message.reply_text(
        new_message,
        reply_markup=ReplyKeyboardRemove(),
    )
    await update.message.reply_text(
        "Para iniciar una nueva conversación envía un mensaje diciendo: /hola",
        reply_markup=ReplyKeyboardRemove(),
    )


def main() -> None:
    """Start the bot."""
    global TOKEN, engine, Base, reply_keyboard

    Base.metadata.create_all(engine)

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    context = CallbackContext(application, chat_id=None, user_id=None)

    keyboard_options_reg = "|".join([option.value for option in list(KeyboardOptions)])
    conv_enders_reg = "|".join(["Adios", "adios", "Chao", "chao"])

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("hola", start),
            CommandHandler("start", start),
        ],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$"))
                    & (filters.Regex(f"^({keyboard_options_reg})$")),
                    choice_reply_handler,
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
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{conv_enders_reg}$"), done)],
        allow_reentry=True,
    )

    conv_handler_delete_participant = ConversationHandler(
        entry_points=[
            CommandHandler("eliminar_participante", delete_participant_command)
        ],
        states={
            CONFIRM_YES_OR_NO: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    yes_or_no_handler,
                ),
            ],
            DELETE_PARTICIPANT: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    delete_participant_handler,
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{conv_enders_reg}$"), done)],
        allow_reentry=True,
    )

    conv_handler_start_game = ConversationHandler(
        entry_points=[CommandHandler("iniciar_juego", start_game_command)],
        states={
            CONFIRM_YES_OR_NO: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    delete_participant_handler,
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{conv_enders_reg}$"), done)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.add_handler(conv_handler_delete_participant)
    application.add_handler(conv_handler_start_game)

    application.add_handler(CommandHandler("instrucciones", instructions_command))
    application.add_handler(
        CommandHandler("participantes", get_all_participants_command)
    )
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
