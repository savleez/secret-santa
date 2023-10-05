from sqlalchemy import Column, Integer, String, Boolean, Text

from secret_santa.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    recipient_name = Column(String(255), unique=False, nullable=True)
    preferences = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
