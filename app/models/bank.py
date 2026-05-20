from sqlalchemy import Column, String
from app.database import Base


class Bank(Base):
    __tablename__ = "banks"

    code = Column(String(10),  primary_key=True)
    name = Column(String(100), nullable=False)
