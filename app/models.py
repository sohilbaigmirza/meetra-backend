from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    phone_or_email = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Outing(Base):
    __tablename__ = "outings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    distance = Column(String, nullable=True)
    travel_mode = Column(String, nullable=True)
    event_time = Column(String, nullable=True)
    total_expense = Column(Integer, nullable=False)
    expense_breakdown = Column(JSON, nullable=True)  # {"travel": 50, "entry": 0, "food": 150}
    tags = Column(JSON, nullable=True)               # ["Budget", "Chai"]
    max_seats = Column(Integer, default=4)
    is_solo = Column(Boolean, default=False)
    created_by = Column(String, nullable=False)