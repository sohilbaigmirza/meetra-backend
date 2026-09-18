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

# ----------------- User Profile Endpoints ----------------- #

@app.post("/api/v1/users/profile", response_model=schemas.UserProfileResponse)
def create_or_get_profile(user_in: schemas.UserProfileCreateOrUpdate, db: Session = Depends(get_db)):
    # Check if a user with this name already exists or create new
    user = db.query(models.User).filter(models.User.name == user_in.name).first()
    if not user:
        user = models.User(**user_in.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing
        for field, value in user_in.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
    return user

@app.get("/api/v1/users/{user_id}", response_model=schemas.UserProfileResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/v1/users", response_model=List[schemas.UserProfileResponse])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

# ----------------- Outing Persistence Endpoints ----------------- #

@app.get("/api/v1/outings", response_model=List[schemas.OutingResponse])
def get_outings(db: Session = Depends(get_db)):
    return db.query(models.Outing).order_by(models.Outing.id.desc()).all()

@app.post("/api/v1/outings", response_model=schemas.OutingResponse)
def create_outing(outing_in: schemas.OutingCreate, db: Session = Depends(get_db)):
    new_outing = models.Outing(**outing_in.model_dump())
    db.add(new_outing)
    db.commit()
    db.refresh(new_outing)
    return new_outing

# ----------------- Dynamic Itinerary Generator ----------------- #

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

SAMPLE_PLACES = {
    "Food": [
        {"name": "Sarafa / Street Food Lane", "cost": 120, "act": "Evening Chaat & Street Food"},
        {"name": "Rolls & Shawarma Point", "cost": 160, "act": "Quick Dinner & Shakes"}
    ],
    "Cafes": [
        {"name": "Artisan Coffee Roastery", "cost": 210, "act": "Cold Brew & Group Discussion"},
        {"name": "Open-Air Rooftop Cafe", "cost": 260, "act": "Sunset Views & Chai"}
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
        {"name": "Sunset View Point", "cost": 0, "act": "Sunset Sitting & Jamming"}
    ],
    "Budget": [
        {"name": "Campus Tapri Point", "cost": 30, "act": "Cutting Chai & Maska Bun"},
        {"name": "Central Library Greenery", "cost": 0, "act": "Open Air Study Session"}
    ]
}

@app.post("/api/v1/itinerary/generate", response_model=ItineraryResponse)
def generate_itinerary(req: ItineraryRequest):
    budget = req.budget
    selected_stops = []
    running_cost = 0

    selected_stops.append(ItineraryStop(
        time="2:00 PM",
        title=req.location,
        category="Start Point",
        est_cost=0,
        activity="Assemble & Depart"
    ))

    candidate_spots = []
    for interest in req.interests:
        if interest in SAMPLE_PLACES:
            candidate_spots.extend(SAMPLE_PLACES[interest])

    if not candidate_spots:
        candidate_spots = SAMPLE_PLACES["Food"]

    random.shuffle(candidate_spots)

    current_hour = 14
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

    return ItineraryResponse(
        id=random.randint(1000, 9999),
        title=f"{req.location} to {req.outing_type}",
        total_cost=calculated_total,
        est_duration=f"{req.available_hours} hrs",
        timeline=selected_stops,
        match_score=random.randint(86, 97) if not req.is_solo else None,
        potential_peers=[
            {"id": 1, "name": "Aarav Sharma", "college": "CSE '28", "interests": ["Food", "Cafes"], "rating": 4.9, "collabs": 7},
            {"id": 2, "name": "Sneha Patel", "college": "ECE '28", "interests": ["Cafes", "Photography"], "rating": 4.8, "collabs": 4},
            {"id": 3, "name": "Ashutosh G.", "college": "IT '27", "interests": ["Adventure", "Arcades"], "rating": 4.7, "collabs": 9}
        ] if not req.is_solo else []
    )