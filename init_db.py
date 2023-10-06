from sqlmodel import SQLModel

from secret_santa.database import engine
from secret_santa.models import *

def init_db():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
