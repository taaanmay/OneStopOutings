from pydantic import BaseModel
from typing import List

class UserPreferences(BaseModel):
    """
    Defines the data we expect from the user/frontend.
    The 'mode' tells us whether to generate a standard or quirky plan.
    """
    budget: int
    interests: List[str]
    mode: str  # 'surprise' or 'must-see'

class Event(BaseModel):
    """Defines a single event in the outing."""
    type: str
    name: str
    cost: int
    duration: int

class OutingPlan(BaseModel):
    """Defines the final plan we send back to the user."""
    plan: List[Event]
    total_cost: int
    total_duration: int

class RegenerateRequest(BaseModel):
    """
    Defines the data needed to regenerate a single event.
    It includes the full user preferences so we can respect the 'mode'.
    """
    current_plan: List[Event]
    event_index_to_replace: int
    user_preferences: UserPreferences
