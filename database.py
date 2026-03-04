from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:root@localhost:5432/skripsi_backend"

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