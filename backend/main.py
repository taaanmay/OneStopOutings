# backend/main.py

from fastapi import FastAPI
from typing import List
from fastapi.middleware.cors import CORSMiddleware

# --- 1. Import your refactored data structures ---
from model.models import UserPreferences, Event, OutingPlan

# --- Initialize our FastAPI app ---
app = FastAPI()

# --- NEW: Add CORS Middleware ---
# This allows our frontend (running on a different port) to communicate with our backend.
origins = [
    "http://localhost:5173", # The default port for Vite React dev server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
)


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