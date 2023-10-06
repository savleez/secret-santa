import unittest

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError

from secret_santa.models import Participant, ContactMethod, ContactMethodType
from secret_santa.database import Base
from tests.database import Session, engine


class TestContactMethodTypeCRUD(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        engine.dispose()

    def test_add_unique_names(self):
        name1 = "Email"
        name2 = "Telegram"

        contact_method_type_1 = ContactMethodType(name=name1)
        contact_method_type_2 = ContactMethodType(name=name2)

        self.assertIsNone(contact_method_type_1.id)
        self.assertIsNone(contact_method_type_2.id)

        with Session() as session:
            session.add(contact_method_type_1)
            session.add(contact_method_type_2)
            session.commit()
            session.refresh(contact_method_type_1)
            session.refresh(contact_method_type_2)

        self.assertIsNotNone(contact_method_type_1.id)
        self.assertIsNotNone(contact_method_type_2.id)

    def test_add_existing_name(self):
        name1 = "Email"
        name2 = "Email"

        contact_method_type_1 = ContactMethodType(name=name1)
        contact_method_type_2 = ContactMethodType(name=name2)

        self.assertIsNone(contact_method_type_1.id)
        self.assertIsNone(contact_method_type_2.id)

        with self.assertRaises(IntegrityError):
            with Session() as session:
                session.add(contact_method_type_1)
                session.add(contact_method_type_2)
                session.commit()
                session.refresh(contact_method_type_1)
                session.refresh(contact_method_type_2)

    def test_add_null_name(self):
        name = None

        contact_method_type = ContactMethodType(name=name)

        self.assertIsNone(contact_method_type.id)

        with self.assertRaises(IntegrityError):
            with Session() as session:
                session.add(contact_method_type)
                session.commit()
                session.refresh(contact_method_type)

    def test_add_not_null_name(self):
        name = "Email"

        contact_method_type = ContactMethodType(name=name)

        self.assertIsNone(contact_method_type.id)

        with Session() as session:
            session.add(contact_method_type)
            session.commit()
            session.refresh(contact_method_type)

        self.assertIsNotNone(contact_method_type.id)

    def test_retrieve_contact_method_type_by_name(self):
        name = "Email"

        new_contact_method_type = ContactMethodType(name=name)

        self.assertIsNone(new_contact_method_type.id)

        with Session() as session:
            session.add(new_contact_method_type)
            session.commit()
            session.refresh(new_contact_method_type)

        self.assertIsNotNone(new_contact_method_type.id)

        with Session() as session:
            retrieved_contact_method_type = (
                session.query(ContactMethodType)
                .filter(ContactMethodType.name == name)
                .first()
            )

        self.assertIsNotNone(retrieved_contact_method_type)
        self.assertEqual(new_contact_method_type.id, retrieved_contact_method_type.id)
        self.assertEqual(
            new_contact_method_type.name, retrieved_contact_method_type.name
        )

    def test_update_name(self):
        initial_name = "Email"
        updated_name = "New Email"

        # Create a new ContactMethodType with the initial name
        contact_method_type = ContactMethodType(name=initial_name)
        self.assertIsNone(contact_method_type.id)

        with Session() as session:
            session.add(contact_method_type)
            session.commit()
            session.refresh(contact_method_type)

        # Update the name of the ContactMethodType
        contact_method_type.name = updated_name
        self.assertIsNotNone(contact_method_type.id)

        with Session() as session:
            session.add(contact_method_type)
            session.commit()
            session.refresh(contact_method_type)

        # Verify that the name has been updated correctly
        self.assertEqual(contact_method_type.name, updated_name)

    def test_delete_contact_method_type(self):
        name = "Email"

        # Create a new ContactMethodType
        contact_method_type = ContactMethodType(name=name)
        self.assertIsNone(contact_method_type.id)

        with Session() as session:
            session.add(contact_method_type)
            session.commit()
            session.refresh(contact_method_type)

        # Delete the ContactMethodType from the database
        with Session() as session:
            session.delete(contact_method_type)
            session.commit()

        # Verify that the ContactMethodType has been deleted
        with Session() as session:
            deleted_contact_method_type = session.query(ContactMethodType).get(
                contact_method_type.id
            )
            self.assertIsNone(deleted_contact_method_type)


class TestParticipantCRUD(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        engine.dispose()

    def test_create_participant_with_only_name(self):
        name = "John Doe"

        # Create a new Participant
        participant = Participant(name=name)
        self.assertIsNone(participant.id)

        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

        # Verify that the Participant has been created and assigned an ID
        self.assertIsNotNone(participant.id)
        self.assertEqual(participant.name, name)

    def test_read_participant(self):
        name = "John Doe"
        recipient_name = "Jane Smith"
        preferences = "No preferences"

        # Create a new Participant
        participant = Participant(
            name=name, recipient_name=recipient_name, preferences=preferences
        )

        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

        with Session() as session:
            # Retrieve the Participant from the database
            retrieved_participant = session.query(Participant).get(participant.id)

        # Verify that the retrieved Participant matches the original one
        self.assertIsNotNone(retrieved_participant)
        self.assertEqual(retrieved_participant.name, name)
        self.assertEqual(retrieved_participant.recipient_name, recipient_name)
        self.assertEqual(retrieved_participant.preferences, preferences)

    def test_update_participant_name(self):
        initial_name = "John Doe"
        updated_name = "John Smith"

        # Create a new Participant with the initial name
        participant = Participant(name=initial_name)

        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

        # Update the name of the Participant
        participant.name = updated_name

        with Session() as session:
            session.add(participant)
            session.commit()

        # Verify that the name has been updated correctly
        self.assertEqual(participant.name, updated_name)

    def test_update_participant_recipient_name(self):
        name = "John Doe"
        recipient_name = "John Smith"

        # Create a new Participant with the initial name
        participant = Participant(name=name)

        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

        # Update the name of the Participant
        participant.recipient_name = recipient_name

        with Session() as session:
            session.add(participant)
            session.commit()

        # Verify that the name has been updated correctly
        self.assertEqual(participant.recipient_name, recipient_name)

    def test_update_participant_preferences(self):
        name = "John Doe"
        preferences = "I like chocolate"

        # Create a new Participant with the initial name
        participant = Participant(name=name)

        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

        # Update the name of the Participant
        participant.preferences = preferences

        with Session() as session:
            session.add(participant)
            session.commit()

        # Verify that the name has been updated correctly
        self.assertEqual(participant.preferences, preferences)

    def test_delete_participant(self):
        name = "John Doe"

        # Create a new Participant
        participant = Participant(name=name)

        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

            # Delete the Participant from the database
            session.delete(participant)
            session.commit()

        # Verify that the Participant has been deleted
        with Session() as session:
            deleted_participant = session.query(Participant).get(participant.id)
            self.assertIsNone(deleted_participant)


class TestContactMethodCRUD(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        engine.dispose()

    def test_create_contact_method(self):
        """Test case for creating a new contact method.
        This function creates a new ContactMethodType, Participant, and ContactMethod.
        It verifies that the ContactMethod is successfully created with the correct values.
        """

        # Create a new ContactMethodType
        contact_method_type = ContactMethodType(name="Email")
        with Session() as session:
            session.add(contact_method_type)
            session.commit()
            session.refresh(contact_method_type)

        # Create a new Participant
        participant = Participant(name="John Doe")
        with Session() as session:
            session.add(participant)
            session.commit()
            session.refresh(participant)

        # Create a new ContactMethod
        contact_method = ContactMethod(
            participant_id=participant.id,
            value="test@example.com",
            method_type_id=contact_method_type.id,
        )
        self.assertIsNone(contact_method.id)

        with Session() as session:
            session.add(contact_method)
            session.commit()
            session.refresh(contact_method)

        self.assertIsNotNone(contact_method.id)
        self.assertEqual(contact_method.participant_id, participant.id)
        self.assertEqual(contact_method.method_type_id, contact_method_type.id)
