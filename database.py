from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def save_data(value):
    db = SessionLocal()
    # simpan ke tabel (contoh sederhana)
    print("Saving to DB:", value)
    db.close()