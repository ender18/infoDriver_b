import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

AUTOCAB_DATABASE_URL = (
    f"postgresql://{os.getenv('AUTOCAB_DB_USER')}:{os.getenv('AUTOCAB_DB_PASSWORD')}"
    f"@{os.getenv('AUTOCAB_DB_HOST')}:{os.getenv('AUTOCAB_DB_PORT')}/{os.getenv('AUTOCAB_DB_NAME')}"
)

autocab_engine = create_engine(AUTOCAB_DATABASE_URL)
AutocabSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=autocab_engine)

@event.listens_for(autocab_engine, "checkout")
def set_autocab_timezone(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET timezone = 'America/Mexico_City'")
    cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_autocab_db():
    db = AutocabSessionLocal()
    try:
        yield db
    finally:
        db.close()