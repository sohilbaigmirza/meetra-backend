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

# Expanded Place Catalog
SAMPLE_PLACES = {
    "Food": [
        {"name": "Sarafa / Street Food Lane", "cost": 120, "act": "Evening Chaat & Street Food"},
        {"name": "Rolls & Shawarma Joint", "cost": 160, "act": "Quick Dinner & Shakes"}
    ],
    "Cafes": [
        {"name": "Artisan Coffee Roastery", "cost": 210, "act": "Cold Brew & Group Discussion"},
        {"name": "Open-Air Rooftop Cafe", "cost": 280, "act": "Sunset Views & Chai"}
    ],
    "Heritage": [
        {"name": "Historic Fort & Museum", "cost": 50, "act": "Architecture Walk & Photography"},
        {"name": "Royal Memorial Cenotaphs", "cost": 30, "act": "Historical Exploration"}
    ],
    "Adventure": [
        {"name": "Laser Tag & Arcade Arena", "cost": 350, "act": "Competitive Gaming"},
        {"name": "Go-Karting Speedway", "cost": 450, "act": "Sprint Racing Laps"}
    ],
    "Nature": [
        {"name": "Eco Botanical Garden & Lake", "cost": 40, "act": "Nature Trail & Chill"},
        {"name": "Valley View Point", "cost": 0, "act": "Sunset Sitting & Jamming"}
    ],
    "Budget": [
        {"name": "University Tapri Spot", "cost": 30, "act": "Cutting Chai & Maska Bun"},
        {"name": "Central Library Lawns", "cost": 0, "act": "Open Air Study Session"}
    ]
}

@app.post("/api/v1/itinerary/generate", response_model=ItineraryResponse)
def generate_itinerary(req: ItineraryRequest):
    budget = req.budget
    selected_stops = []
    running_cost = 0
    
    # 1. Start point
    selected_stops.append(ItineraryStop(
        time="2:00 PM",
        title=req.location,
        category="Start Point",
        est_cost=0,
        activity="Assemble & Depart"
    ))

    # 2. Pick spots matching user's selected interests
    candidate_spots = []
    for interest in req.interests:
        if interest in SAMPLE_PLACES:
            candidate_spots.extend(SAMPLE_PLACES[interest])
    
    if not candidate_spots:
        candidate_spots = SAMPLE_PLACES["Food"]

    random.shuffle(candidate_spots)

    current_hour = 14  # 2:00 PM
    for spot in candidate_spots:
        if len(selected_stops) >= 4:
            break
        if running_cost + spot["cost"] <= budget:
            current_hour += 1
            running_cost += spot["cost"]
            selected_stops.append(ItineraryStop(
                time=f"{current_hour % 12 or 12}:00 {'PM' if current_hour >= 12 else 'AM'}",
                title=spot["name"],
                category=spot["act"].split()[0],
                est_cost=spot["cost"],
                activity=spot["act"]
            ))

    transit_estimate = 30 if req.is_solo else 20
    calculated_total = running_cost + transit_estimate

    # Dynamic match score
    match_score = random.randint(85, 98) if not req.is_solo else None

    return ItineraryResponse(
        id=random.randint(1000, 9999),
        title=f"{req.location} to {req.outing_type}",
        total_cost=calculated_total,
        est_duration=f"{req.available_hours} hrs",
        timeline=selected_stops,
        match_score=match_score,
        potential_peers=[
            {"id": 1, "name": "Aarav Sharma", "college": "CSE '28", "interests": ["Food", "Cafes"], "rating": 4.9, "collabs": 7},
            {"id": 2, "name": "Sneha Patel", "college": "ECE '28", "interests": ["Cafes", "Photography"], "rating": 4.8, "collabs": 4},
            {"id": 3, "name": "Ashutosh G.", "college": "IT '27", "interests": ["Adventure", "Arcades"], "rating": 4.7, "collabs": 9}
        ] if not req.is_solo else []
    )