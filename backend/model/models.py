from pydantic import BaseModel
from typing import List

class UserPreferences(BaseModel):
    """Defines the data we expect from the user/frontend."""
    budget: int
    interests: List[str]
    # We'll add location, dietary needs, etc. later

class Event(BaseModel):
    """Defines a single event in the outing."""
    type: str
    name: str
    cost: int
    duration: int # in minutes

class OutingPlan(BaseModel):
    """Defines the final plan we send back to the user."""
    plan: List[Event]
    total_cost: int
    total_duration: int