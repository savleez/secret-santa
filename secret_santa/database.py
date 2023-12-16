from os import getenv
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()

# Environment variables
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATABASE_NAME = getenv("DATABASE_NAME")

DATABASE_URL = f"sqlite:///{PROJECT_DIR / DATABASE_NAME}"

# SQLAlchemy
engine = create_engine(
    url=DATABASE_URL,
    connect_args={"check_same_thread": False},
)

Session = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()
