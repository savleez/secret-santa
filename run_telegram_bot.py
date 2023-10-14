from enum import Enum
from random import choice, shuffle
from re import sub as re_sub
from os import getenv
from typing import List

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
)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from secret_santa.models import Participant
from secret_santa.database import Base

TEST = True

if TEST:
    from tests.database import Session, engine
else:
    from secret_santa.database import Session, engine


load_dotenv()
TOKEN = getenv("TELEGRAM_TOKEN")

(
    CHOOSING,
    TYPING_REPLY,
    TYPING_NAME,
    DELETE_PARTICIPANT,
    CONFIRM_DELETE_PARTICIPANT,
) = range(5)

conv_enders = [
    "Adios",
    "adios",
    "Adiós",
    "adiós",
    "Chao",
    "chao",
    "Cancelar",
    "cancelar",
]

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
    GET_PARTICIPANT = "Ver mi información"
    GET_RECIPIENT = "Ver mi pareja"
    EDIT_NAME = "Cambiar mi nombre"
    EDIT_PREFS = "Cambiar mis preferencias"
    INSTRUCTIONS = "Ver reglas del juego"
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


def update_participant(new_participant: Participant) -> bool:
    updated = False

    with Session() as session:
        try:
            session.add(new_participant)
            session.commit()

            updated = True
        except:
            try:
                session.rollback()
            except:
                pass

    return updated


def get_participant(chat_id: str = None, participant_name: str = None) -> Participant:
    with Session() as session:
        if chat_id:
            participant = (
                session.query(Participant)
                .filter(Participant.chat_id == chat_id)
                .first()
            )
        elif participant_name:
            participant = (
                session.query(Participant)
                .filter(Participant.name == participant_name)
                .first()
            )
        else:
            return None

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


def get_participant_whose_recipient_is_participant(
    participant: Participant,
) -> Participant:
    with Session() as session:
        participant = (
            session.query(Participant)
            .filter(Participant.chat_id == participant.chat_id)
            .first()
        )

        participant_whose_recipient_is_participant = (
            session.query(Participant)
            .filter(Participant.recipient_id == participant.id)
            .first()
        )

        return participant_whose_recipient_is_participant


def get_all_participants() -> List[Participant]:
    with Session() as session:
        participants = session.query(Participant).all()

    return participants


def delete_participant(chat_id: str = None, participant_name: str = None):
    deleted = False

    with Session() as session:
        try:
            if chat_id:
                participant = get_participant(chat_id=chat_id)
            else:
                participant = get_participant(participant_name=participant_name)

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

    participant = get_participant(update.effective_chat.id)

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
                session.query(Participant)
                .filter(func.lower(Participant.name) == name.lower())
                .all()
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
            f"Muchas gracias {name}, te acabo de registrar en el juego",
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

    user_choice = update.message.text
    context.bot_data["choice"] = user_choice

    if user_choice in conv_enders:
        return await done(update, context)

    participant = get_participant(chat_id=update.effective_chat.id)

    preferences = (
        f'tus preferencias son:\n"{participant.preferences}"'
        if participant.preferences is not None and len(participant.preferences) > 0
        else "todavía no tienes preferencias"
    )

    if user_choice == KeyboardOptions.GET_PARTICIPANT.value:
        await update.message.reply_text(
            f"Te llamas {participant.name} y {preferences}",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif user_choice == KeyboardOptions.EDIT_NAME.value:
        await update.message.reply_text(
            "¿Me puedes decir cuál es tu nuevo nombre?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return TYPING_REPLY

    elif user_choice == KeyboardOptions.EDIT_PREFS.value:
        await update.message.reply_text(
            "En tus preferencias puedes indicar cosas como tu talla de ropa o de zapatos,"
            "o si tienes alguna preferencia en particular que pueda interesar "
            "a la persona que te tiene",
            reply_markup=ReplyKeyboardRemove(),
        )

        await update.message.reply_text(
            preferences.capitalize(),
            reply_markup=ReplyKeyboardRemove(),
        )

        await update.message.reply_text(
            "¿Me puedes decir cuáles son tus nuevas preferencias?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return TYPING_REPLY

    elif user_choice == KeyboardOptions.GET_RECIPIENT.value:
        recipient = get_participant_recipient(participant=participant)

        if recipient is None:
            await update.message.reply_text(
                "Todavía no se han asignado las parejas",
                reply_markup=ReplyKeyboardRemove(),
            )

        else:
            preferences = (
                f'sus preferencias son:\n"{recipient.preferences}"'
                if recipient.preferences is not None and len(recipient.preferences) > 0
                else "todavía no tiene preferencias"
            )

            await update.message.reply_text(
                "Recuerda no decirle a nadie 🤫",
                reply_markup=ReplyKeyboardRemove(),
            )
            await update.message.reply_text(
                f"Tu pareja es {recipient.name} y {preferences}",
                reply_markup=ReplyKeyboardRemove(),
            )

    elif user_choice == KeyboardOptions.INSTRUCTIONS.value:
        await update.message.reply_text(
            GAME_RULES,
            reply_markup=ReplyKeyboardRemove(),
        )

    else:
        await update.message.reply_text(
            "Lo siento, no entiendo lo que dijiste"
            "¿Puedes seleccionar una de las opciones disponibles?",
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


async def confirm_delete_participant(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    global conv_enders

    usr_response = update.message.text

    if usr_response in conv_enders or usr_response.lower() != "si":
        return await done(update, context)

    return await delete_participant_handler(update, context)


async def delete_participant_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    global conv_enders

    usr_response = update.message.text
    participant_to_delete = context.bot_data.get("participant_to_delete")

    participants = get_all_participants()
    names = [
        participant.name for participant in participants if participant.name is not None
    ]

    if usr_response in conv_enders or (
        usr_response not in names and usr_response.lower() not in ["si", "no"]
    ):
        return await done(update, context)

    if not participant_to_delete:
        context.bot_data["participant_to_delete"] = usr_response

        await update.message.reply_text(
            f"¿Seguro que quieres eliminar al participante {usr_response}?",
            reply_markup=create_keyboard(["Si", "No"]),
        )

        return CONFIRM_DELETE_PARTICIPANT

    chat_id = get_participant(participant_name=participant_to_delete).chat_id
    deleted = delete_participant(participant_name=participant_to_delete)

    if deleted:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Fuiste eliminado del juego, si tienes dudas por favor contacta a Maria Fernanda",
        )

        await update.message.reply_text(
            f"El participante {participant_to_delete} fue eliminado. "
            "Si se quiere registrar nuevamente deberá mandar /hola al bot",
            reply_markup=ReplyKeyboardRemove(),
        )

    else:
        await update.message.reply_text(
            "Hubo un error desconocido y el participante no se eliminó.",
            reply_markup=ReplyKeyboardRemove(),
        )


async def typing_response_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    chat_id = update.effective_chat.id
    choice = context.bot_data["choice"]
    usr_response = update.message.text

    participant = get_participant(chat_id=chat_id)

    updated_reply = "Muchas gracias {}, acabo de actualizar {} en el juego"

    if choice == KeyboardOptions.EDIT_NAME.value:
        participant.name = usr_response
        update_participant(participant)

        updated_reply = updated_reply.format(participant.name, "tu nombre")

    elif choice == KeyboardOptions.EDIT_PREFS.value:
        participant.preferences = usr_response
        update_participant(participant)

        updated_reply = updated_reply.format(participant.name, "tus preferencias")

        participant_whose_recipient_is_participant = (
            get_participant_whose_recipient_is_participant(participant)
        )

        if participant_whose_recipient_is_participant is not None:
            await context.bot.send_message(
                chat_id=participant_whose_recipient_is_participant.chat_id,
                text=(
                    "Tu pareja acaba de actualizar sus preferencias, "
                    "puedes consultarlas diciendo /hola y luego en la opción de "
                    "Ver mi pareja"
                ),
            )
    else:
        updated_reply = (
            "Disculpa, parece que hubo un pequeño error, "
            "¿Puedes intentar otra vez por favor?"
        )

    await update.message.reply_text(
        updated_reply,
        reply_markup=ReplyKeyboardRemove(),
    )

    await update.message.reply_text(
        "¿Quieres hacer algo más?",
        reply_markup=create_keyboard(),
    )

    return CHOOSING


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text(
        "Si tienes dudas de cómo funciona este chat, "
        "por favor contacta a Maria Fernanda 😄",
        reply_markup=ReplyKeyboardRemove(),
    )


async def start_game_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    clean_recipients()
    participants = get_all_participants()

    if len(participants) < 3:
        await update.message.reply_text(
            "¡El juego no puede iniciar con menos de 3 personas! "
            "Para consultar la lista de participantes envíe /participantes",
            reply_markup=ReplyKeyboardRemove(),
        )

        return await done(update, context)

    await update.message.reply_text(
        "Repartiendo las parejas...",
        reply_markup=ReplyKeyboardRemove(),
    )

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

    if any(
        [participant.recipient_id is None for participant in get_all_participants()]
    ):
        await update.message.reply_text(
            "Hubo un error asignando las parejas, por favor intente eliminar "
            "las parejas con /eliminar_parejas y repartirlas de nuevo con "
            "/iniciar_juego",
            reply_markup=ReplyKeyboardRemove(),
        )

    await update.message.reply_text(
        "¡Se asignaron las parejas!",
        reply_markup=ReplyKeyboardRemove(),
    )

    for participant in get_all_participants():
        await context.bot.send_message(
            chat_id=participant.chat_id,
            text=(
                "Ya se te asignó una pareja, para consultar quién te tocó "
                "inicia una conversación con /hola y pregúntame por tu pareja"
            ),
        )


async def get_commands_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    available_commands = (
        "/hola o /start -> Iniciar conversación"
        "\n/participantes -> Obtener lista de participantes"
        "\n/eliminar_participante -> Eliminar un participante"
        "\n/iniciar_juego -> Repartir las parejas"
        "\n/eliminar_parejas -> Eliminar las parejas"
        "\n/ayuda -> Mensaje de ayuda"
        "\n/comandos -> Este menú con los comandos"
    )

    await update.message.reply_text(
        available_commands,
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


def clean_recipients():
    for participant in get_all_participants():
        participant.recipient_id = None
        update_participant(participant)

    if any(
        [participant.recipient_id is not None for participant in get_all_participants()]
    ):
        raise ValueError("No se limpiaron todos las parejas")


async def clean_recipients_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    if len(get_all_participants()) == 1:
        await update.message.reply_text(
            f"Todavía no hay participantes",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    try:
        clean_recipients()

        await update.message.reply_text(
            f"Se limpiaron todas las parejas",
            reply_markup=ReplyKeyboardRemove(),
        )

    except:
        await update.message.reply_text(
            "Parece que ocurrió un error y no se limpiaron todos los participantes. "
            "Por favor revisar manualmente",
            reply_markup=ReplyKeyboardRemove(),
        )


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
            f"Por ahora hay {len(names)} participantes: {', '.join(names)}",
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

    if len(names) == 0:
        await update.message.reply_text(
            "Todavía no se han registrado participantes",
            reply_markup=ReplyKeyboardRemove(),
        )

        return

    await update.message.reply_text(
        "Por favor selecciona el participante a eliminar",
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
    global TOKEN, engine, Base, conv_enders

    Base.metadata.create_all(engine)

    # Create the Application and pass it your bot's token.
    app = Application.builder().token(TOKEN).build()

    keyboard_options_reg = "|".join([option.value for option in list(KeyboardOptions)])
    conv_enders_reg = "|".join(conv_enders)

    # Add main conversation handler with the states CHOOSING and TYPING_CHOICE
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("hola", start),
            CommandHandler("start", start),
            MessageHandler(
                filters.TEXT
                & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$"))
                & (filters.Regex("^(?i)hola$")),
                start,
            ),
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
                    typing_response_handler,
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

    # Add delete participant conversation handler
    conv_handler_delete_participant = ConversationHandler(
        entry_points=[
            CommandHandler("eliminar_participante", delete_participant_command)
        ],
        states={
            DELETE_PARTICIPANT: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    delete_participant_handler,
                ),
            ],
            CONFIRM_DELETE_PARTICIPANT: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    confirm_delete_participant,
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{conv_enders_reg}$"), done)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(conv_handler_delete_participant)

    app.add_handler(CommandHandler("participantes", get_all_participants_command))
    app.add_handler(CommandHandler("iniciar_juego", start_game_command))
    app.add_handler(CommandHandler("eliminar_parejas", clean_recipients_command))
    app.add_handler(CommandHandler("ayuda", help_command))
    app.add_handler(CommandHandler("comandos", get_commands_command))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
            echo,
        )
    )

    # Run the bot until the user presses Ctrl-C
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
