import random
from typing import List, Optional, Dict
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Response
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

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

# ----------------- Google Sign-In & Auth ----------------- #

class GoogleAuthRequest(BaseModel):
    firebase_uid: str
    email: str
    name: str
    avatar_url: Optional[str] = None

@app.post("/api/v1/auth/google", response_model=schemas.GoogleAuthResponse)
def google_auth_login(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.firebase_uid == req.firebase_uid).first()

    if not user and req.email:
        user = db.query(models.User).filter(models.User.phone_or_email == req.email.strip()).first()
        if user:
            user.firebase_uid = req.firebase_uid
            db.commit()
            db.refresh(user)

    is_new = False
    if not user:
        is_new = True
        user = models.User(
            firebase_uid=req.firebase_uid,
            name=req.name.strip() if req.name else "Student",
            phone_or_email=req.email.strip(),
            avatar_url=req.avatar_url,
            age=19,
            college="ITM University",
            branch="B.Tech CSE • 1st Year",
            bio="Up for quick cafe hangouts & street food trails!",
            interests=["Food", "Cafes"],
            preferred_outing_types=["Budget Cafes", "Heritage Walk"],
            budget_preference=300,
            rating=5.0,
            collabs_completed=0
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    needs_setup = is_new or (user.college in ["Campus Member", None])
    return {
        "user": user,
        "is_new_user": needs_setup
    }

# ----------------- User Profile Endpoints ----------------- #

@app.post("/api/v1/users/profile", response_model=schemas.UserProfileResponse)
def create_or_update_profile(profile_in: schemas.UserProfileCreateOrUpdate, db: Session = Depends(get_db)):
    user = None
    profile_id = getattr(profile_in, "id", None)
    profile_phone = getattr(profile_in, "phone_or_email", None)
    profile_uid = getattr(profile_in, "firebase_uid", None)

    if profile_id:
        user = db.query(models.User).filter(models.User.id == profile_id).first()
    if not user and profile_phone:
        user = db.query(models.User).filter(models.User.phone_or_email == profile_phone.strip()).first()
    if not user and profile_uid:
        user = db.query(models.User).filter(models.User.firebase_uid == profile_uid).first()
    if not user and profile_in.name:
        user = db.query(models.User).filter(models.User.name == profile_in.name.strip()).first()

    if not user:
        user_data = profile_in.model_dump(exclude_unset=True)
        user_data.pop("id", None)
        user = models.User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        for key, value in profile_in.model_dump(exclude_unset=True).items():
            if key != "id" and value is not None:
                setattr(user, key, value)
        db.commit()
        db.refresh(user)

    return user

@app.get("/api/v1/users/{user_id}", response_model=schemas.UserProfileResponse)
def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/api/v1/users/peers/{current_user_id}", response_model=List[schemas.UserProfileResponse])
def get_all_peers(current_user_id: int, db: Session = Depends(get_db)):
    return db.query(models.User).filter(models.User.id != current_user_id).all()

# ----------------- Outings Feed & Filter Endpoints ----------------- #

@app.get("/api/v1/outings", response_model=List[schemas.OutingResponse])
def get_outings(
    tag: Optional[str] = None,
    max_budget: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Outing)
    if max_budget is not None:
        query = query.filter(models.Outing.total_expense <= max_budget)
    
    outings = query.order_by(models.Outing.id.desc()).all()
    
    if tag and tag.lower() != 'all':
        clean_tag = tag.lstrip('#').lower()
        outings = [
            o for o in outings 
            if o.tags and any(clean_tag == t.lstrip('#').lower() for t in o.tags)
        ]

    return outings

@app.post("/api/v1/outings", response_model=schemas.OutingResponse)
def create_outing(outing_in: schemas.OutingCreate, db: Session = Depends(get_db)):
    new_outing = models.Outing(**outing_in.model_dump())
    db.add(new_outing)
    db.commit()
    db.refresh(new_outing)
    return new_outing

# ----------------- Milestone 2.2: Bookmarks / Wishlist ----------------- #

@app.post("/api/v1/bookmarks/toggle")
def toggle_bookmark(req: schemas.BookmarkToggle, db: Session = Depends(get_db)):
    existing = db.query(models.Bookmark).filter(
        models.Bookmark.user_id == req.user_id,
        models.Bookmark.outing_id == req.outing_id
    ).first()

    if existing:
        db.delete(existing)
        db.commit()
        return {"bookmarked": False, "outing_id": req.outing_id}
    else:
        new_bookmark = models.Bookmark(user_id=req.user_id, outing_id=req.outing_id)
        db.add(new_bookmark)
        db.commit()
        return {"bookmarked": True, "outing_id": req.outing_id}

@app.get("/api/v1/bookmarks/{user_id}")
def get_user_bookmarks(user_id: int, db: Session = Depends(get_db)):
    bookmarked_rows = db.query(models.Bookmark).filter(models.Bookmark.user_id == user_id).all()
    outing_ids = [b.outing_id for b in bookmarked_rows]
    if not outing_ids:
        return []
    return db.query(models.Outing).filter(models.Outing.id.in_(outing_ids)).all()

# ----------------- Dynamic Itinerary Generator ----------------- #

@app.post("/api/v1/itinerary/generate")
def generate_itinerary(req: schemas.ItineraryGenerateRequest, db: Session = Depends(get_db)):
    db_places = db.query(models.Place).filter(models.Place.approx_cost <= req.budget).all()
    if not db_places:
        db_places = db.query(models.Place).all()

    selected_spots = random.sample(db_places, min(len(db_places), 3)) if db_places else []

    timeline = []
    total_cost = 40
    start_hour = 16

    for idx, spot in enumerate(selected_spots):
        timeline.append({
            "time": f"{start_hour + idx}:00 PM",
            "title": spot.name,
            "activity": f"{spot.category} hangout at {spot.landmark}",
            "est_cost": spot.approx_cost
        })
        total_cost += spot.approx_cost

    user_query = db.query(models.User)
    if req.user_id:
        user_query = user_query.filter(models.User.id != req.user_id)
    real_users = user_query.all()

    peers_list = []
    for u in real_users:
        peers_list.append({
            "id": u.id,
            "name": u.name,
            "college": u.college,
            "avatar_url": u.avatar_url,
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

# ----------------- Review & Outing Completion ----------------- #

@app.post("/api/v1/reviews", response_model=schemas.ReviewResponse)
def submit_review(review_in: schemas.ReviewCreate, db: Session = Depends(get_db)):
    new_review = models.Review(**review_in.model_dump())
    db.add(new_review)
    
    reviewee = db.query(models.User).filter(models.User.id == review_in.reviewee_id).first()
    if reviewee:
        reviewee.collabs_completed = (reviewee.collabs_completed or 0) + 1
        all_reviews = db.query(models.Review).filter(models.Review.reviewee_id == review_in.reviewee_id).all()
        ratings = [r.rating for r in all_reviews] + [review_in.rating]
        reviewee.rating = round(sum(ratings) / len(ratings), 1)

    collab = db.query(models.CollabRequest).filter(models.CollabRequest.id == review_in.collab_id).first()
    if collab:
        collab.status = "completed"

    db.commit()
    db.refresh(new_review)
    return new_review

# ----------------- Milestone 2.1: Friends & Connections ----------------- #

@app.post("/api/v1/friends/request", response_model=schemas.FriendshipResponse)
def send_friend_request(req: schemas.FriendshipCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Friendship).filter(
        ((models.Friendship.requester_id == req.requester_id) & (models.Friendship.receiver_id == req.receiver_id)) |
        ((models.Friendship.requester_id == req.receiver_id) & (models.Friendship.receiver_id == req.requester_id))
    ).first()
    if existing:
        return existing

    new_friendship = models.Friendship(**req.model_dump())
    db.add(new_friendship)
    db.commit()
    db.refresh(new_friendship)
    return new_friendship

@app.put("/api/v1/friends/{friendship_id}", response_model=schemas.FriendshipResponse)
def respond_friend_request(friendship_id: int, update_data: schemas.FriendshipUpdate, db: Session = Depends(get_db)):
    f = db.query(models.Friendship).filter(models.Friendship.id == friendship_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Friend request not found")
    f.status = update_data.status
    db.commit()
    db.refresh(f)
    return f

@app.get("/api/v1/friends/{user_id}")
def get_user_friends(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Friendship).filter(
        (models.Friendship.requester_id == user_id) | (models.Friendship.receiver_id == user_id)
    ).all()