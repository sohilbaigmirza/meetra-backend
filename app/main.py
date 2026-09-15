from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .database import engine, Base, get_db
from . import models, schemas

# Auto-create tables in Neon on launch
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MeetRa API",
    description="Central API engine for MeetRa Web and Mobile apps",
    version="1.0.0"
)

# Allow React local dev and production web app
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