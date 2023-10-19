from typing import List

from secret_santa.models import Participant
from secret_santa.database import Session


def update_participant(new_participant: Participant) -> bool:
    updated = False

    with Session() as session:
        try:
            participant = (
                session.query(Participant)
                .filter(Participant.id == new_participant.id)
                .first()
            )

            participant.name = new_participant.name
            participant.preferences = new_participant.preferences
            participant.recipient_id = new_participant.recipient_id

            session.add(participant)
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
