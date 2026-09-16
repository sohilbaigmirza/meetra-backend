import random
from typing import List, Optional, Dict
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from . import models, schemas

# Auto-create tables in Neon on launch
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MeetRa API",
    description="Central API engine for MeetRa Web and Mobile apps",
    version="1.0.0"
)

# Allow React local dev, Vercel frontend, and mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "online", "system": "MeetRa Core API"}

# 1. Sync User from Firebase Auth
@app.post("/api/v1/auth/sync", response_model=schemas.UserResponse)
def sync_user(user_in: schemas.UserSync, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.firebase_uid == user_in.firebase_uid).first()
    if not user:
        user = models.User(
            firebase_uid=user_in.firebase_uid,
            name=user_in.name,
            phone_or_email=user_in.phone_or_email,
            branch=user_in.branch,
            avatar_url=user_in.avatar_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

# 2. Get All Outings Feed
@app.get("/api/v1/outings", response_model=List[schemas.OutingResponse])
def get_outings(db: Session = Depends(get_db)):
    return db.query(models.Outing).all()

# 3. Create Outing
@app.post("/api/v1/outings", response_model=schemas.OutingResponse)
def create_outing(outing_in: schemas.OutingCreate, db: Session = Depends(get_db)):
    new_outing = models.Outing(**outing_in.model_dump())
    db.add(new_outing)
    db.commit()
    db.refresh(new_outing)
    return new_outing

# ----------------- Itinerary Generator & Matching ----------------- #

class ItineraryRequest(BaseModel):
    available_hours: float
    budget: int
    location: str
    interests: List[str]
    outing_type: str
    is_solo: bool

class ItineraryStop(BaseModel):
    time: str
    title: str
    category: str
    est_cost: int
    activity: str

class ItineraryResponse(BaseModel):
    id: int
    title: str
    total_cost: int
    est_duration: str
    timeline: List[ItineraryStop]
    match_score: Optional[int] = None
    potential_peers: List[dict] = []

SAMPLE_PLACES = [
    {"name": "Heritage Fort & Sunset Point", "cat": "Heritage", "cost": 40, "act": "Sightseeing & Photos"},
    {"name": "Old City Street Food Street", "cat": "Food", "cost": 150, "act": "Evening Snacks & Chai"},
    {"name": "Artisan Coffee Roastery", "cat": "Cafes", "cost": 200, "act": "Coffee & Chill"},
    {"name": "Eco Botanical Gardens", "cat": "Nature", "cost": 30, "act": "Nature Walk"},
    {"name": "Central Gaming Arcade", "cat": "Adventure", "cost": 250, "act": "Bowling & Arcade"},
]

@app.post("/api/v1/itinerary/generate", response_model=ItineraryResponse)
def generate_itinerary(req: ItineraryRequest):
    budget = req.budget
    selected = [p for p in SAMPLE_PLACES if p["cost"] <= budget]
    if not selected:
        selected = [SAMPLE_PLACES[1]]
    
    stops = []
    current_time = 14  # 2:00 PM start
    running_cost = 0

    stops.append(ItineraryStop(
        time="2:00 PM",
        title=req.location,
        category="Start Point",
        est_cost=0,
        activity="Assemble & Depart"
    ))

    for place in selected[:2]:
        if running_cost + place["cost"] <= budget:
            current_time += 1
            stops.append(ItineraryStop(
                time=f"{current_time}:00 PM",
                title=place["name"],
                category=place["cat"],
                est_cost=place["cost"],
                activity=place["act"]
            ))
            running_cost += place["cost"]

    return ItineraryResponse(
        id=random.randint(1000, 9999),
        title=f"{req.outing_type} Expedition",
        total_cost=running_cost + 40,
        est_duration=f"{req.available_hours} hours",
        timeline=stops,
        match_score=94 if not req.is_solo else None,
        potential_peers=[
            {"id": 1, "name": "Aarav Sharma", "college": "CSE '28", "interests": ["Food", "Cafes"], "rating": 4.9, "collabs": 7},
            {"id": 2, "name": "Sneha Patel", "college": "ECE '28", "interests": ["Cafes", "Photography"], "rating": 4.8, "collabs": 4}
        ] if not req.is_solo else []
    )