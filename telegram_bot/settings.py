from enum import Enum


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
