import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in the environment.")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def save_data(value):
    db = SessionLocal()

    print("Saving to DB:", value)

    db.close()
