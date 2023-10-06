from os import getenv

from dotenv import load_dotenv
from sqlmodel import create_engine

load_dotenv()

# Environment variables
DATABASE_NAME = getenv("DATABASE_NAME")
DATABASE_URL = f"sqlite:///{DATABASE_NAME}"

# SQLModel connection
engine = create_engine(
    url=DATABASE_URL,
    echo= True
)

