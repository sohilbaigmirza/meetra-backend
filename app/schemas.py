from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class UserProfileCreateOrUpdate(BaseModel):
    name: str
    college: Optional[str] = "Campus Member"
    branch: Optional[str] = "1st Year"
    bio: Optional[str] = "Up for quick cafe hangouts and exploring new spots!"
    phone_or_email: Optional[str] = None
    avatar_url: Optional[str] = None
    interests: Optional[List[str]] = ["Food", "Cafes"]
    preferred_outing_types: Optional[List[str]] = ["Budget Cafes", "Street Food Crawl"]
    budget_preference: Optional[int] = 300

class UserProfileResponse(UserProfileCreateOrUpdate):
    id: int
    rating: float
    collabs_completed: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class OutingCreate(BaseModel):
    title: str
    category: str
    distance: Optional[str] = "3.5 km"
    travel_mode: Optional[str] = "E-Rickshaw / Walk"
    event_time: Optional[str] = "Weekend"
    total_expense: int
    expense_breakdown: Optional[Dict[str, Any]] = {}
    tags: Optional[List[str]] = []
    max_seats: Optional[int] = 4
    is_solo: Optional[bool] = False
    created_by: str
    created_by_id: Optional[int] = None

class OutingResponse(OutingCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CollabRequestCreate(BaseModel):
    outing_id: int
    sender_id: int
    sender_name: str
    receiver_id: int
    receiver_name: str
    match_percentage: Optional[int] = 90

class CollabRequestUpdate(BaseModel):
    status: str  # 'accepted' or 'rejected'

class CollabRequestResponse(CollabRequestCreate):
    id: int
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    collab_id: int
    sender_id: int
    sender_name: str
    text: str

class MessageResponse(MessageCreate):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True