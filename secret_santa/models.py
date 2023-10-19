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
    chat_id = Column(String, nullable=False, unique=True)

    recipient = relationship("Participant", remote_side=[id], uselist=False)

    def __eq__(self, other):
        return (
            self.id == other.id
            and self.name == other.name
            and self.recipient_id == other.recipient_id
            and self.preferences == other.preferences
        )

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
