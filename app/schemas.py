from pydantic import BaseModel
from typing import Optional, List, Dict

# User Schemas
class UserSync(BaseModel):
    firebase_uid: str
    name: str
    phone_or_email: Optional[str] = None
    branch: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserSync):
    id: int

    class Config:
        from_attributes = True

# Outing Schemas
class OutingCreate(BaseModel):
    title: str
    category: str
    distance: str
    travel_mode: str
    event_time: str
    total_expense: int
    expense_breakdown: Dict[str, int]
    tags: List[str]
    max_seats: int
    is_solo: bool = False
    created_by: str

class OutingResponse(OutingCreate):
    id: int

    class Config:
        from_attributes = True