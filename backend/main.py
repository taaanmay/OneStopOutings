# backend/main.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

# --- 1. Define our Data Structures ---

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

# --- Initialize our FastAPI app ---
app = FastAPI()


# --- 2. Create our API Endpoint ---

@app.post("/plan", response_model=OutingPlan)
def create_outing_plan(preferences: UserPreferences):
    """
    Receives user preferences and returns a personalized outing plan.
    """
    # For now, we'll print the preferences to see if we received them
    print(f"Received preferences: {preferences}")

    # --- 3. Implement Mock Logic ---
    # In the future, this is where we'll call the Gemini LLM.
    # For now, we return a hardcoded "dummy" plan.
    
    mock_plan = OutingPlan(
        plan=[
            Event(type="Breakfast", name="The Early Bird Café", cost=15, duration=60),
            Event(type="Activity", name="National Museum of Ireland", cost=0, duration=120),
            Event(type="Lunch", name="Pizzeria Rustico", cost=25, duration=75),
        ],
        total_cost=40,
        total_duration=255
    )
    
    return mock_plan

@app.get("/")
def read_root():
    return {"message": "Welcome to the OneStopOutings API"}