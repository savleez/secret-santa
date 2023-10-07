from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from secret_santa.database import Base

# TODO: Add validation to orm fields since SQLAlchemy does not do it.
# max_length, blank...


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    recipient_id = Column(
        Integer,
        ForeignKey("participants.id"),
        unique=True,
        nullable=True,
    )
    preferences = Column(Text, nullable=True)

    contact_methods = relationship("ContactMethod", back_populates="participant")
    recipient = relationship("Participant", remote_side=[id], uselist=False)

    def __eq__(self, other):
        return (
            self.id == other.id
            and self.name == other.name
            and self.recipient_id == other.recipient_id
            and self.preferences == other.preferences
        )


class ContactMethod(Base):
    __tablename__ = "contact_methods"

    id = Column(Integer, primary_key=True)
    participant_id = Column(
        Integer,
        ForeignKey("participants.id"),
        nullable=False,
    )
    method_type_id = Column(
        Integer,
        ForeignKey("contact_method_types.id"),
        nullable=False,
    )
    value = Column(String(255), nullable=False)

    participant = relationship(Participant, back_populates="contact_methods")
    method_type = relationship("ContactMethodType")

    def __eq__(self, other):
        return (
            self.id == other.id
            and self.participant_id == other.participant_id
            and self.method_type_id == other.method_type_id
            and self.value == other.value
        )


class ContactMethodType(Base):
    __tablename__ = "contact_method_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)

    def __eq__(self, other):
        return self.id == other.id and self.name == other.name
