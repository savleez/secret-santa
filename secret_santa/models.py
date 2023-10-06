from typing import Optional

from sqlmodel import Field, SQLModel, create_engine


class Participant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=255, unique=True, nullable=False)
    recipient_name: Optional[str] = Field(max_length=255, unique=True)
    preferences: Optional[str] = None


# class Participant(Base):
#     __tablename__ = "participants"

#     id = Column(Integer, primary_key=True)
#     name = Column(String(255), unique=True, nullable=False)
#     recipient_name = Column(String(255), unique=False, nullable=True)
#     preferences = Column(Text, nullable=True)
#     is_admin = Column(Boolean, default=False, nullable=False)

#     contact_methods = relationship("ContactMethod", back_populates="participant")


# class ContactMethod(Base):
#     __tablename__ = "contact_methods"

#     id = Column(Integer, primary_key=True)
#     participant_id = Column(Integer, ForeignKey("participants.id"))
#     method_type_id = Column(Integer, ForeignKey("contact_method_types.id"))
#     value = Column(String(255), nullable=False)

#     participant = relationship(Participant, back_populates="contact_methods")
#     method_type = relationship("ContactMethodType")


# class ContactMethodType(Base):
#     __tablename__ = "contact_method_types"

#     id = Column(Integer, primary_key=True)
#     name = Column(String(255), unique=True, nullable=False)
