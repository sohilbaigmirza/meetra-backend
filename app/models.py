from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=False)
    college = Column(String, default="Campus Member")
    branch = Column(String, default="1st Year")
    bio = Column(String, default="Up for quick cafe hangouts and exploring new spots!")
    phone_or_email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    rating = Column(Float, default=5.0)
    collabs_completed = Column(Integer, default=0)
    interests = Column(JSON, default=list)  # e.g. ["Food", "Cafes"]
    preferred_outing_types = Column(JSON, default=list)  # e.g. ["Budget Cafes", "Heritage Walk"]
    budget_preference = Column(Integer, default=300)
    created_at = Column(DateTime, default=datetime.utcnow)

class Outing(Base):
    __tablename__ = "outings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    distance = Column(String, default="3.5 km")
    travel_mode = Column(String, default="E-Rickshaw / Walk")
    event_time = Column(String, default="Weekend")
    total_expense = Column(Integer, nullable=False)
    expense_breakdown = Column(JSON, default=dict)
    tags = Column(JSON, default=list)
    max_seats = Column(Integer, default=4)
    is_solo = Column(Boolean, default=False)
    created_by = Column(String, nullable=False)
    created_by_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CollabRequest(Base):
    __tablename__ = "collab_requests"

    id = Column(Integer, primary_key=True, index=True)
    outing_id = Column(Integer, nullable=False)
    sender_id = Column(Integer, nullable=False)
    sender_name = Column(String, nullable=False)
    receiver_id = Column(Integer, nullable=False)
    receiver_name = Column(String, nullable=False)
    match_percentage = Column(Integer, default=90)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    collab_id = Column(Integer, nullable=False, index=True)
    sender_id = Column(Integer, nullable=False)
    sender_name = Column(String, nullable=False)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    collab_id = Column(Integer, nullable=False)
    reviewer_id = Column(Integer, nullable=False)
    reviewer_name = Column(String, nullable=False)
    reviewee_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)
    tags = Column(JSON, default=list)
    feedback = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Place(Base):
    __tablename__ = "places"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    approx_cost = Column(Integer, nullable=False)
    distance_km = Column(Float, default=2.0)
    landmark = Column(String, nullable=False)
    tags = Column(JSON, default=list)

class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, nullable=False)
    requester_name = Column(String, nullable=False)
    receiver_id = Column(Integer, nullable=False)
    receiver_name = Column(String, nullable=False)
    status = Column(String, default="pending")  # 'pending', 'accepted', 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)