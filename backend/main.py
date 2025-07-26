import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import List

# Import the updated models
from model.models import UserPreferences, Event, OutingPlan, RegenerateRequest

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# CORS Middleware setup
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UPDATED: More robust parsing function ---
def parse_llm_response(text_response: str) -> List[Event]:
    """
    Parses the text response from the LLM into a list of Event objects.
    This version is more robust and handles 'Free' for cost and malformed lines.
    """
    events = []
    lines = text_response.strip().split('\n')
    for line in lines:
        if not line:
            continue
        try:
            parts = [p.strip() for p in line.split(',')]
            event_data = {}
            for part in parts:
                # --- FIX: Ensure the part contains a colon before splitting ---
                if ':' not in part:
                    continue
                
                key, value = part.split(':', 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                
                if key == 'type':
                    event_data['type'] = value
                elif key == 'name':
                    event_data['name'] = value
                elif key == 'cost':
                    if value.lower() == 'free':
                        event_data['cost'] = 0
                    else:
                        event_data['cost'] = int(value)
                elif key == 'duration':
                    event_data['duration'] = int(value)
            
            if all(k in event_data for k in ['type', 'name', 'cost', 'duration']):
                events.append(Event(**event_data))
            else:
                print(f"Skipping incomplete line: '{line}'")

        except Exception as e:
            print(f"Skipping malformed line: '{line}'. Error: {e}")
            continue
    return events


# --- UPDATED: Function to call the Gemini API for a full plan ---
async def generate_plan_with_llm(preferences: UserPreferences):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google API key not found.")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    if preferences.mode == 'surprise':
        mode_instruction = "Focus on quirky, offbeat, or hidden gem locations that a typical tourist might miss."
    else:  # 'must-see'
        mode_instruction = "Focus on iconic, popular, or can't-miss landmarks and experiences in Dublin."

    prompt = f"""
    You are an expert Dublin tour planner. A user wants to plan a day out.
    Their planning mode is "{preferences.mode}".
    Their preferences are:
    - Budget: {preferences.budget} euros
    - Interests: {', '.join(preferences.interests)}

    {mode_instruction}

    Create a simple, 3-event plan for them (morning, afternoon, evening).
    For each event, provide a type, name, estimated cost, and duration in minutes.
    IMPORTANT: For free events, use a cost of 0. Respond with ONLY the plan in a raw text format, like this example:
    Type: Breakfast, Name: The Early Bird Café, Cost: 15, Duration: 60
    Type: Activity, Name: National Museum of Ireland, Cost: 0, Duration: 120
    Type: Lunch, Name: Pizzeria Rustico, Cost: 25, Duration: 75
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            if result.get('candidates'):
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                raise HTTPException(status_code=500, detail="Could not parse LLM response.")
        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"An error occurred while requesting the LLM: {exc}")


# --- UPDATED: Function to get a single replacement event ---
async def get_single_replacement_event(request: RegenerateRequest):
    api_key = os.getenv("GOOGLE_API_KEY")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    if request.user_preferences.mode == 'surprise':
        mode_instruction = "Suggest a quirky, offbeat, or hidden gem alternative."
    else:  # 'must-see'
        mode_instruction = "Suggest an iconic or popular alternative."

    existing_event_names = [event.name for event in request.current_plan]
    
    # --- FIX: Format the current plan into a simple string for the prompt ---
    formatted_plan = "\n".join(
        [f"Type: {e.type}, Name: {e.name}, Cost: {e.cost}, Duration: {e.duration}" for e in request.current_plan]
    )

    prompt = f"""
    You are an expert Dublin tour planner. A user wants to replace one event in their current plan.
    User Preferences:
    - Interests: {', '.join(request.user_preferences.interests)}
    - Planning Mode: {request.user_preferences.mode}
    
    Current Plan:
    {formatted_plan}
    
    The user wants to replace the event: "{request.current_plan[request.event_index_to_replace].name}"
    
    {mode_instruction}
    
    The suggestion must be different from all the events currently in the plan ({', '.join(existing_event_names)}).
    
    IMPORTANT: For free events, use a cost of 0. Respond with ONLY the single new event in a raw text format, like this example:
    Type: Pub, Name: The Brazen Head, Cost: 20, Duration: 90
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        if result.get('candidates'):
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            raise HTTPException(status_code=500, detail="Could not parse LLM response for regeneration.")


# --- API Endpoints ---

@app.post("/plan", response_model=OutingPlan)
async def create_outing_plan(preferences: UserPreferences):
    llm_text_response = await generate_plan_with_llm(preferences)
    parsed_events = parse_llm_response(llm_text_response)
    if not parsed_events:
        raise HTTPException(status_code=500, detail="Failed to generate a valid plan.")
    total_cost = sum(event.cost for event in parsed_events)
    total_duration = sum(event.duration for event in parsed_events)
    return OutingPlan(plan=parsed_events, total_cost=total_cost, total_duration=total_duration)


@app.post("/regenerate-event", response_model=OutingPlan)
async def regenerate_event(request: RegenerateRequest):
    new_event_text = await get_single_replacement_event(request)
    new_events = parse_llm_response(new_event_text)
    if not new_events:
        raise HTTPException(status_code=500, detail="Failed to parse regenerated event.")
    updated_plan_events = request.current_plan
    updated_plan_events[request.event_index_to_replace] = new_events[0]
    total_cost = sum(event.cost for event in updated_plan_events)
    total_duration = sum(event.duration for event in updated_plan_events)
    return OutingPlan(plan=updated_plan_events, total_cost=total_cost, total_duration=total_duration)


@app.get("/")
def read_root():
    return {"message": "Welcome to the OneStopOutings API"}
