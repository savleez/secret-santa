from sqlmodel import create_engine

DATABASE_URL = "sqlite:///:memory:"

# SQLModel connection
engine = create_engine(url=DATABASE_URL, echo=True)
