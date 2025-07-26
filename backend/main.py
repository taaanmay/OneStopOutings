# backend/main.py

import os
import httpx # New library for making API calls
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv # New library for loading .env files
from typing import List

from model.models import UserPreferences, Event, OutingPlan

# --- Load Environment Variables ---
# This will load the GOOGLE_API_KEY from your .env file
load_dotenv()

# --- Initialize our FastAPI app ---
app = FastAPI()

# --- Add CORS Middleware ---
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- NEW: Function to call the Gemini API ---
async def generate_plan_with_llm(preferences: UserPreferences):
    """
    Constructs a prompt and calls the Gemini API to get a plan.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Google API key not found.")

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    # This is our prompt. We're asking the LLM to act as a planner and return
    # a structured response. This is called "prompt engineering".
    prompt = f"""
    You are an expert Dublin tour planner. A user wants to plan a day out.
    Their preferences are:
    - Budget: {preferences.budget} euros
    - Interests: {', '.join(preferences.interests)}

    Create a simple, 3-event plan for them (morning, afternoon, evening).
    For each event, provide a type, name, estimated cost, and duration in minutes.
    
    IMPORTANT: Respond with ONLY the plan in a raw text format, like this example:
    
    Type: Breakfast, Name: The Early Bird Café, Cost: 15, Duration: 60
    Type: Activity, Name: National Museum of Ireland, Cost: 0, Duration: 120
    Type: Lunch, Name: Pizzeria Rustico, Cost: 25, Duration: 75
    """

    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=payload, timeout=30.0)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
            result = response.json()
            
            # Extract the text content from the Gemini response
            if result.get('candidates'):
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                # Handle cases where the response structure is unexpected
                print("Unexpected API response:", result)
                raise HTTPException(status_code=500, detail="Could not parse LLM response.")

        except httpx.RequestError as exc:
            raise HTTPException(status_code=500, detail=f"An error occurred while requesting the LLM: {exc}")
        except Exception as e:
            # Catch other potential errors, e.g., parsing the response
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# --- NEW: Function to parse the LLM's text response ---
def parse_llm_response(text_response: str) -> List[Event]:
    events = []
    lines = text_response.strip().split('\n')
    for line in lines:
        if not line:
            continue
        try:
            parts = [p.strip() for p in line.split(',')]
            event_data = {}
            for part in parts:
                key, value = part.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                if key == 'type':
                    event_data['type'] = value
                elif key == 'name':
                    event_data['name'] = value
                elif key == 'cost':
                    event_data['cost'] = int(value)
                elif key == 'duration':
                    event_data['duration'] = int(value)
            events.append(Event(**event_data))
        except Exception as e:
            print(f"Skipping malformed line: '{line}'. Error: {e}")
            continue
    return events


# --- UPDATED: The API Endpoint ---
@app.post("/plan", response_model=OutingPlan)
async def create_outing_plan(preferences: UserPreferences):
    """
    Receives user preferences, gets a plan from the LLM, parses it,
    and returns it to the user.
    """
    print(f"Received preferences: {preferences}")

    # Step 1: Call the LLM to get a raw text plan
    llm_text_response = await generate_plan_with_llm(preferences)
    print("--- LLM Raw Response ---")
    print(llm_text_response)
    print("------------------------")

    # Step 2: Parse the text response into our Event models
    parsed_events = parse_llm_response(llm_text_response)
    
    if not parsed_events:
        raise HTTPException(status_code=500, detail="Failed to generate or parse a valid plan from the LLM.")

    # Step 3: Calculate totals and create the final OutingPlan object
    total_cost = sum(event.cost for event in parsed_events)
    total_duration = sum(event.duration for event in parsed_events)

    final_plan = OutingPlan(
        plan=parsed_events,
        total_cost=total_cost,
        total_duration=total_duration
    )
    
    return final_plan


@app.get("/")
def read_root():
    return {"message": "Welcome to the OneStopOutings API"}