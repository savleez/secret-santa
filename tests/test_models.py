import unittest

from sqlalchemy.ext.declarative import declarative_base

from secret_santa.models import Participant, ContactMethod, ContactMethodType
from secret_santa.database import Base
from tests.database import Session, engine


class TestContactMethodTypeCRUD(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)

    def tearDown(self):
        engine.dispose()

    def test_name_max_length(self):
        """Intenta crear un ContactMethodType con un nombre que excede 255 caracteres"""

        long_name = "A" * 256
        contact_method_type = ContactMethodType(name=long_name)

        with self.assertRaises(Exception):
            with Session() as session:
                session.add(contact_method_type)
                session.commit()
                session.refresh(contact_method_type)

    def test_create_contact_method_type(self):
        new_contact_method_type = ContactMethodType(name="Email")

        self.assertIsNone(new_contact_method_type.id)

        with Session() as session:
            session.add(new_contact_method_type)
            session.commit()
            session.refresh(new_contact_method_type)

        self.assertIsNotNone(new_contact_method_type.id)

        # def test_create_contact_method_type_with_m


class TestContactMethodCRUD(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self):
        engine.dispose()


class TestParticipantCRUD(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self):
        engine.dispose()
