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

origins = [
    "https://meetra-frontend-sable.vercel.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
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

@app.post("/api/v1/itinerary/generate")
def generate_itinerary(req: schemas.ItineraryGenerateRequest, db: Session = Depends(get_db)):
    # 1. Query real places from Neon filtered by budget
    db_places = db.query(models.Place).filter(models.Place.approx_cost <= req.budget).all()
    
    # Fallback to all places if budget query is empty
    if not db_places:
        db_places = db.query(models.Place).all()

    import random
    selected_spots = random.sample(db_places, min(len(db_places), 3)) if db_places else []

    timeline = []
    total_cost = 40  # baseline auto/travel split
    start_hour = 16  # 4:00 PM

    for idx, spot in enumerate(selected_spots):
        timeline.append({
            "time": f"{start_hour + idx}:00 PM",
            "title": spot.name,
            "activity": f"{spot.category} hangout at {spot.landmark}",
            "est_cost": spot.approx_cost
        })
        total_cost += spot.approx_cost

    # 2. Fetch real peers from Neon instead of dummy users
    real_users = db.query(models.User).all()
    peers_list = []
    for u in real_users:
        peers_list.append({
            "id": u.id,
            "name": u.name,
            "college": u.college,
            "collabs": u.collabs_completed or 0,
            "interests": u.interests or ["Food", "Cafes"]
        })

    return {
        "id": random.randint(1000, 9999),
        "title": f"Campus to {selected_spots[0].name if selected_spots else 'Gwalior Hotspots'}",
        "est_duration": f"{req.available_hours}.0 hrs",
        "total_cost": min(total_cost, req.budget),
        "timeline": timeline,
        "match_score": 94,
        "potential_peers": peers_list
    }

# ----------------- Collab Request Endpoints ----------------- #

@app.post("/api/v1/collabs", response_model=schemas.CollabRequestResponse)
def send_collab_request(req_in: schemas.CollabRequestCreate, db: Session = Depends(get_db)):
    # Check if request already sent
    existing = db.query(models.CollabRequest).filter(
        models.CollabRequest.outing_id == req_in.outing_id,
        models.CollabRequest.sender_id == req_in.sender_id,
        models.CollabRequest.receiver_id == req_in.receiver_id
    ).first()
    if existing:
        return existing
    
    collab = models.CollabRequest(**req_in.model_dump())
    db.add(collab)
    db.commit()
    db.refresh(collab)
    return collab

@app.get("/api/v1/collabs/user/{user_id}", response_model=List[schemas.CollabRequestResponse])
def get_user_collab_requests(user_id: int, db: Session = Depends(get_db)):
    # Fetch pending incoming requests for this user
    return db.query(models.CollabRequest).filter(
        (models.CollabRequest.receiver_id == user_id) | (models.CollabRequest.sender_id == user_id)
    ).order_by(models.CollabRequest.id.desc()).all()

@app.put("/api/v1/collabs/{collab_id}", response_model=schemas.CollabRequestResponse)
def update_collab_status(collab_id: int, update_in: schemas.CollabRequestUpdate, db: Session = Depends(get_db)):
    collab = db.query(models.CollabRequest).filter(models.CollabRequest.id == collab_id).first()
    if not collab:
        raise HTTPException(status_code=404, detail="Collab request not found")
    
    collab.status = update_in.status
    db.commit()
    db.refresh(collab)
    return collab

# ----------------- Chat Endpoints ----------------- #

@app.get("/api/v1/chat/{collab_id}", response_model=List[schemas.MessageResponse])
def get_messages(collab_id: int, db: Session = Depends(get_db)):
    return db.query(models.Message).filter(models.Message.collab_id == collab_id).order_by(models.Message.id.asc()).all()

@app.post("/api/v1/chat", response_model=schemas.MessageResponse)
def send_message(msg_in: schemas.MessageCreate, db: Session = Depends(get_db)):
    msg = models.Message(**msg_in.model_dump())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

from fastapi import Response

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# ----------------- Review & Outing Completion ----------------- #

@app.post("/api/v1/reviews", response_model=schemas.ReviewResponse)
def submit_review(review_in: schemas.ReviewCreate, db: Session = Depends(get_db)):
    # 1. Save Review
    new_review = models.Review(**review_in.model_dump())
    db.add(new_review)
    
    # 2. Update Reviewee user stats: increment collabs_completed and recalculate rating
    reviewee = db.query(models.User).filter(models.User.id == review_in.reviewee_id).first()
    if reviewee:
        reviewee.collabs_completed = (reviewee.collabs_completed or 0) + 1
        # Recalculate average rating
        all_reviews = db.query(models.Review).filter(models.Review.reviewee_id == review_in.reviewee_id).all()
        ratings = [r.rating for r in all_reviews] + [review_in.rating]
        reviewee.rating = round(sum(ratings) / len(ratings), 1)

    # 3. Mark collab status as completed
    collab = db.query(models.CollabRequest).filter(models.CollabRequest.id == review_in.collab_id).first()
    if collab:
        collab.status = "completed"

    db.commit()
    db.refresh(new_review)
    return new_review

@app.post("/api/v1/auth/sync", response_model=schemas.UserProfileResponse)
def sync_user_profile(user_in: schemas.UserProfileCreateOrUpdate, db: Session = Depends(get_db)):
    # Check if user already exists by firebase_uid or phone_or_email
    user = None
    if user_in.firebase_uid:
        user = db.query(models.User).filter(models.User.firebase_uid == user_in.firebase_uid).first()
    elif user_in.phone_or_email:
        user = db.query(models.User).filter(models.User.phone_or_email == user_in.phone_or_email).first()
        
    if not user:
        user = models.User(**user_in.model_dump())
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update existing profile
        for key, val in user_in.model_dump(exclude_unset=True).items():
            setattr(user, key, val)
        db.commit()
        db.refresh(user)
    return user

@app.get("/api/v1/users/peers/{current_user_id}", response_model=List[schemas.UserProfileResponse])
def get_all_peers(current_user_id: int, db: Session = Depends(get_db)):
    # Returns all real registered users excluding the current logged-in user
    return db.query(models.User).filter(models.User.id != current_user_id).all()