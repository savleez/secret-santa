from random import choice, shuffle
from re import sub as re_sub
from os import getenv
from multiprocessing import Process

from dotenv import load_dotenv
from telegram import (
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

from telegram_bot import settings
from telegram_bot import models
from telegram_bot.utils import create_keyboard
from secret_santa.models import Participant
from secret_santa.database import Session, engine, Base, DATABASE_URL


load_dotenv()
TOKEN = getenv("TELEGRAM_TOKEN")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /hola is issued."""

    participant = models.get_participant(update.effective_chat.id)

    if participant is None:
        await update.message.reply_text(
            "¡Hola! Bienvenido al juego de Niño Jesús Secreto",
            reply_markup=ReplyKeyboardRemove(),
        )
        await update.message.reply_text(
            "¿Cómo te llamas?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return settings.TYPING_NAME

    await update.message.reply_text(
        f"¡Hola {participant.name}! ¿Qué quieres hacer?",
        reply_markup=create_keyboard(),
    )

    return settings.CHOOSING


async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Say goodbye"""

    await update.message.reply_text(
        f"¡Hasta la próxima!",
        reply_markup=ReplyKeyboardRemove(),
    )

    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /ayuda is issued."""

    await update.message.reply_text(
        "Si tienes dudas de cómo funciona este chat, "
        "por favor contacta a Maria Fernanda 😄",
        reply_markup=ReplyKeyboardRemove(),
    )


def assign_recipients(participants) -> None:
    participants_copy = participants.copy()
    shuffle(participants)

    for participant in participants:
        possible_recipient = participant

        while possible_recipient == participant:
            possible_recipient = choice(participants_copy)

            # Add restriction to avoid Valen to be paired with Sergio Vargas
            # Valen -> 1749651542
            # Sergio Velez -> 5556702448
            # Sergio Vargas ->
            # Mafe -> 1310291616
            participant_is_valen = int(participant.chat_id) == 1749651542
            recipient_is_valen = int(possible_recipient.chat_id) == 1749651542
            participant_is_sergio = (
                "sergio" in participant.name.lower()
                and int(participant.chat_id) != 5556702448
            )
            recipient_is_sergio = (
                "sergio" in possible_recipient.name.lower()
                and int(possible_recipient.chat_id) != 5556702448
            )

            if (participant_is_valen and recipient_is_sergio) or (
                participant_is_sergio and recipient_is_valen
            ):
                possible_recipient = participant

        models.update_participant_recipient(
            participant=participant,
            recipient=possible_recipient,
        )

        participants_copy.remove(possible_recipient)


async def start_game_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    models.clean_recipients()
    participants = models.get_all_participants()

    if len(participants) < 4:
        await update.message.reply_text(
            "¡El juego no puede iniciar con menos de 4 personas! "
            "Para consultar la lista de participantes envíe /participantes",
            reply_markup=ReplyKeyboardRemove(),
        )

        return await done_command(update, context)

    await update.message.reply_text(
        "Repartiendo las parejas...",
        reply_markup=ReplyKeyboardRemove(),
    )

    try:
        process = Process(target=assign_recipients, args=(participants,))
        process.start()
        process.join(60)  # -> Esperar máximo 60 segundos

        if process.is_alive():
            process.terminate()
            models.clean_recipients()

            raise ValueError("Timeout asignando las parejas.")

        if any(
            [
                participant.recipient_id is None
                for participant in models.get_all_participants()
            ]
        ):
            raise ValueError("No se asignaron todas las parejas")

    except:
        await update.message.reply_text(
            "Hubo un error asignando las parejas, por favor intente eliminar "
            "las parejas con /eliminar_parejas y repartirlas de nuevo con "
            "/iniciar_juego",
            reply_markup=ReplyKeyboardRemove(),
        )
        ConversationHandler.END

    else:
        await update.message.reply_text(
            "¡Se asignaron las parejas!",
            reply_markup=ReplyKeyboardRemove(),
        )

        for participant in models.get_all_participants():
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


async def clean_recipients_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    if len(models.get_all_participants()) == 1:
        await update.message.reply_text(
            f"Todavía no hay participantes",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    try:
        models.clean_recipients()

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

    participants = models.get_all_participants()
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

    participants = models.get_all_participants()

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

    return settings.DELETE_PARTICIPANT


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

        return settings.TYPING_NAME

    else:
        await update.message.reply_text(
            f"Muchas gracias {name}, te acabo de registrar en el juego",
            reply_markup=ReplyKeyboardRemove(),
        )

        await update.message.reply_text(
            "¿Qué quieres hacer?",
            reply_markup=create_keyboard(),
        )

        return settings.CHOOSING


async def choice_reply_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ask the user for info about the selected predefined choice."""

    user_choice = update.message.text
    context.bot_data["choice"] = user_choice

    participant = models.get_participant(chat_id=update.effective_chat.id)

    if user_choice in settings.conv_enders or participant is None:
        return await done_command(update, context)

    participant = models.get_participant(chat_id=update.effective_chat.id)

    preferences = (
        f'tus preferencias son:\n"{participant.preferences}"'
        if participant.preferences is not None and len(participant.preferences) > 0
        else "todavía no tienes preferencias"
    )

    if user_choice == settings.KeyboardOptions.GET_PARTICIPANT.value:
        await update.message.reply_text(
            f"Te llamas {participant.name} y {preferences}",
            reply_markup=ReplyKeyboardRemove(),
        )

    elif user_choice == settings.KeyboardOptions.EDIT_NAME.value:
        await update.message.reply_text(
            "¿Me puedes decir cuál es tu nuevo nombre?",
            reply_markup=ReplyKeyboardRemove(),
        )

        return settings.TYPING_REPLY

    elif user_choice == settings.KeyboardOptions.EDIT_PREFS.value:
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

        return settings.TYPING_REPLY

    elif user_choice == settings.KeyboardOptions.GET_RECIPIENT.value:
        recipient = models.get_participant_recipient(participant=participant)

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

    elif user_choice == settings.KeyboardOptions.INSTRUCTIONS.value:
        await update.message.reply_text(
            settings.GAME_RULES,
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

    return settings.CHOOSING


async def confirm_delete_participant(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    usr_response = update.message.text

    if usr_response in settings.conv_enders or usr_response.lower() != "si":
        return await done_command(update, context)

    return await delete_participant_handler(update, context)


async def delete_participant_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""

    usr_response = update.message.text
    participant_to_delete = context.bot_data.get("participant_to_delete")

    participants = models.get_all_participants()
    names = [
        participant.name for participant in participants if participant.name is not None
    ]

    if usr_response in settings.conv_enders or (
        usr_response not in names and usr_response.lower() not in ["si", "no"]
    ):
        return await done_command(update, context)

    if not participant_to_delete:
        context.bot_data["participant_to_delete"] = usr_response

        await update.message.reply_text(
            f"¿Seguro que quieres eliminar al participante {usr_response}?",
            reply_markup=create_keyboard(["Si", "No"]),
        )

        return settings.CONFIRM_DELETE_PARTICIPANT

    try:
        chat_id = models.get_participant(participant_name=participant_to_delete).chat_id
        deleted = models.delete_participant(participant_name=participant_to_delete)
        models.clean_recipients()
    except:
        deleted = False
    finally:
        context.bot_data["participant_to_delete"] = None

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

    participant = models.get_participant(chat_id=chat_id)

    updated_reply = "Muchas gracias {}, acabo de actualizar {} en el juego"

    if choice == settings.KeyboardOptions.EDIT_NAME.value:
        participant.name = usr_response
        models.update_participant(participant)

        updated_reply = updated_reply.format(participant.name, "tu nombre")

    elif choice == settings.KeyboardOptions.EDIT_PREFS.value:
        participant.preferences = usr_response
        models.update_participant(participant)

        updated_reply = updated_reply.format(participant.name, "tus preferencias")

        participant_whose_recipient_is_participant = (
            models.get_participant_whose_recipient_is_participant(participant)
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

    return settings.CHOOSING


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


async def get_database_path(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /ayuda is issued."""


    await update.message.reply_text(
        f"La base de datos está ubicada en: {DATABASE_URL}",
        reply_markup=ReplyKeyboardRemove(),
    )


def main() -> None:
    """Start the bot."""
    global TOKEN

    Base.metadata.create_all(engine)

    # Create the Application and pass it your bot's token.
    app = Application.builder().token(TOKEN).build()

    keyboard_options_reg = "|".join(
        [option.value for option in list(settings.KeyboardOptions)]
    )
    conv_enders_reg = "|".join(settings.conv_enders)

    # Add main conversation handler with the states settings.CHOOSING and TYPING_CHOICE
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("hola", start_command),
            CommandHandler("start", start_command),
            MessageHandler(
                filters.TEXT
                & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$"))
                & (filters.Regex(r"(?i)^hola$")),
                start_command,
            ),
        ],
        states={
            settings.CHOOSING: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$"))
                    & (filters.Regex(f"^({keyboard_options_reg})$")),
                    choice_reply_handler,
                ),
            ],
            settings.TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    typing_response_handler,
                )
            ],
            settings.TYPING_NAME: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    register_participant,
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{conv_enders_reg}$"), done_command)],
        allow_reentry=True,
    )

    # Add delete participant conversation handler
    conv_handler_delete_participant = ConversationHandler(
        entry_points=[
            CommandHandler("eliminar_participante", delete_participant_command)
        ],
        states={
            settings.DELETE_PARTICIPANT: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    delete_participant_handler,
                ),
            ],
            settings.CONFIRM_DELETE_PARTICIPANT: [
                MessageHandler(
                    filters.TEXT
                    & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
                    confirm_delete_participant,
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex(f"^{conv_enders_reg}$"), done_command)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(conv_handler_delete_participant)

    app.add_handler(CommandHandler("participantes", get_all_participants_command))
    app.add_handler(CommandHandler("iniciar_juego", start_game_command))
    app.add_handler(CommandHandler("eliminar_parejas", clean_recipients_command))
    app.add_handler(CommandHandler("ayuda", help_command))
    app.add_handler(CommandHandler("comandos", get_commands_command))
    app.add_handler(CommandHandler("get_database", get_database_path))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~(filters.COMMAND | filters.Regex(f"^{conv_enders_reg}$")),
            echo,
        )
    )

    # Run the bot until the user presses Ctrl-C
    print("App started")
    app.run_polling(allowed_updates=Update.ALL_TYPES, timeout=120)


if __name__ == "__main__":
    main()
