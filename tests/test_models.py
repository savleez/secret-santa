import unittest

from sqlmodel import SQLModel, Session

from secret_santa.models import Participant
from tests.database import engine


class TestParticipantCRUD(unittest.TestCase):
    def setUp(self):
        SQLModel.metadata.create_all(bind=engine)

    def tearDown(self):
        engine.dispose()

    def test_name_max_length(self):
        """Tries to create a Participant instance with a long name"""

        long_name = "A" * 256

        with self.assertRaises(Exception):
            new_participant = Participant(name=long_name)

    # def test_create_contact_method_type(self):
    #     new_contact_method_type = ContactMethodType(name="Email")

    #     self.assertIsNone(new_contact_method_type.id)

    #     with Session() as session:
    #         session.add(new_contact_method_type)
    #         session.commit()
    #         session.refresh(new_contact_method_type)

    #     self.assertIsNotNone(new_contact_method_type.id)

    # def test_create_contact_method_type_with_m


# class TestContactMethodCRUD(unittest.TestCase):
#     def setUp(self) -> None:
#         pass

#     def tearDown(self):
#         engine.dispose()


# class TestParticipantCRUD(unittest.TestCase):
#     def setUp(self) -> None:
#         pass

#     def tearDown(self):
#         engine.dispose()
