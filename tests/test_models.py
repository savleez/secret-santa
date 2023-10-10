import unittest

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError

from secret_santa.models import Participant
from secret_santa.database import Base
from tests.database import Session, engine


class TestParticipantCRUD(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)

        self.chat_id = "some_chat_id"
        self.name = "John Doe"

        self.participant = Participant(name=self.name, chat_id=self.chat_id)

    def tearDown(self):
        engine.dispose()

    def register_participant_on_db(self, participant: Participant):
        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

        return participant

    def test_create_participant_with_only_name(self):
        # Check that participant does not exist yet
        self.assertIsNotNone(self.participant.name)
        self.assertIsNone(self.participant.id)

        # Create participant
        participant = self.register_participant_on_db(self.participant)

        # Verify that the Participant has been created and assigned an ID
        self.assertIsNotNone(participant.id)
        self.assertEqual(participant.name, self.name)

    def test_read_participant(self):
        name = "John Doe"

        # Create participant
        participant = self.register_participant_on_db(self.participant)

        # Retrieve the Participant from the database
        with Session() as session:
            retrieved_participant = session.query(Participant).get(participant.id)

        # Verify that the retrieved Participant matches the original one
        self.assertIsNotNone(retrieved_participant)
        self.assertEqual(retrieved_participant.name, name)

    def test_update_participant_name(self):
        updated_name = "John Smith"

        # Create a new Participant with the initial name
        participant = self.register_participant_on_db(
            Participant(name=self.name, chat_id=self.chat_id)
        )

        # Update the name of the Participant
        participant.name = updated_name

        with Session() as session:
            session.add(participant)
            session.commit()

        # Verify that the name has been updated correctly
        self.assertEqual(participant.name, updated_name)

    def test_update_participant_recipient(self):
        participant_2_name = "John Smith"
        participant_2_chat_id = "some other chat id"

        # Create a new Participant with the initial name
        participant_1 = self.register_participant_on_db(self.participant)

        participant_2 = self.register_participant_on_db(
            Participant(name=participant_2_name, chat_id=participant_2_chat_id)
        )

        # Update the name of the Participant
        participant_1.recipient_id = participant_2.id

        with Session() as session:
            session.add(participant_1)
            session.commit()
            session.refresh(participant_1)

        # Verify that the name has been updated correctly
        self.assertEqual(participant_1.recipient_id, participant_2.id)

    def test_update_participant_preferences(self):
        preferences = "I like chocolate"

        # Create a new Participant with the initial name
        participant = self.register_participant_on_db(self.participant)

        # Update the name of the Participant
        participant.preferences = preferences

        with Session() as session:
            session.add(participant)
            session.commit()

        # Verify that the name has been updated correctly
        self.assertEqual(participant.preferences, preferences)

    def test_delete_participant(self):
        participant = self.register_participant_on_db(self.participant)

        # Verify that the Participant has been registered
        self.assertIsNotNone(participant.id)

        with Session() as session:
            # Delete the Participant from the database
            session.delete(participant)
            session.commit()

        # Verify that the Participant has been deleted
        with Session() as session:
            deleted_participant = session.query(Participant).get(participant.id)
            self.assertIsNone(deleted_participant)

    def test_get_participant_recipient(self):
        participant_2_name = "John Smith"
        participant_2_chat_id = "some other chat id"

        # Create a new Participant with the initial name
        participant_1 = self.register_participant_on_db(self.participant)
        participant_2 = self.register_participant_on_db(
            Participant(name=participant_2_name, chat_id=participant_2_chat_id)
        )

        self.assertIsNotNone(participant_1.id)
        self.assertIsNotNone(participant_2.id)

        # Update the name of the Participant
        participant_1.recipient_id = participant_2.id

        with Session() as session:
            session.add(participant_1)
            session.commit()
            session.refresh(participant_1)

        with Session() as session:
            participant_1 = session.query(Participant).get(participant_1.id)
            self.assertEqual(participant_1.recipient, participant_2)
