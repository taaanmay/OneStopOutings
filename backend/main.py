import os
import httpx
import logging
from logging.handlers import RotatingFileHandler # NEW: Import RotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import List

# Import the models
from model.models import UserPreferences, Event, OutingPlan, RegenerateRequest

# --- NEW: Setup for File-based Logging ---

# Create a 'logs' directory if it doesn't exist
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Configure the logger
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = os.path.join(log_directory, 'app.log')

# Use RotatingFileHandler to manage log file size
# This will create up to 5 log files, each 5MB in size.
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)

# Get the root logger and add our file handler
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Clear existing handlers to avoid duplicate logs in the console
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)

# Also add a console handler for development visibility
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)


# --- The rest of your application logic ---

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

def parse_llm_response(text_response: str) -> List[Event]:
    events = []
    lines = text_response.strip().split('\n')
    logging.info(f"Parsing {len(lines)} lines from LLM response.")
    for line in lines:
        if not line:
            continue
        try:
            parts = [p.strip() for p in line.split(',')]
            event_data = {}
            for part in parts:
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
                logging.warning(f"Skipping incomplete line: '{line}'")

        except Exception as e:
            logging.error(f"Skipping malformed line: '{line}'. Error: {e}", exc_info=True)
            continue
    return events

async def generate_plan_with_llm(preferences: UserPreferences):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logging.error("GOOGLE_API_KEY not found in environment variables.")
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
            logging.info("Sending request to Gemini API for a full plan.")
            response = await client.post(api_url, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            if result.get('candidates'):
                llm_response = result['candidates'][0]['content']['parts'][0]['text']
                logging.info("Successfully received response from Gemini API.")
                logging.info(f"LLM Response: {llm_response}") # NEW: Log the raw response
                return llm_response
            else:
                logging.error(f"Unexpected API response structure: {result}")
                raise HTTPException(status_code=500, detail="Could not parse LLM response.")
        except httpx.RequestError as exc:
            logging.error(f"An error occurred while requesting the LLM: {exc}")
            raise HTTPException(status_code=500, detail=f"An error occurred while requesting the LLM: {exc}")

async def get_single_replacement_event(request: RegenerateRequest):
    api_key = os.getenv("GOOGLE_API_KEY")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    if request.user_preferences.mode == 'surprise':
        mode_instruction = "Suggest a quirky, offbeat, or hidden gem alternative."
    else:  # 'must-see'
        mode_instruction = "Suggest an iconic or popular alternative."

    existing_event_names = [event.name for event in request.current_plan]
    
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
        logging.info("Sending request to Gemini API for a single replacement event.")
        response = await client.post(api_url, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        if result.get('candidates'):
            llm_response = result['candidates'][0]['content']['parts'][0]['text']
            logging.info("Successfully received replacement event from Gemini API.")
            logging.info(f"LLM Replacement Response: {llm_response}") # NEW: Log the raw response
            return llm_response
        else:
            logging.error(f"Unexpected API response structure for regeneration: {result}")
            raise HTTPException(status_code=500, detail="Could not parse LLM response for regeneration.")


# --- API Endpoints ---

@app.post("/plan", response_model=OutingPlan)
async def create_outing_plan(preferences: UserPreferences):
    logging.info(f"Received /plan request with preferences: {preferences}")
    llm_text_response = await generate_plan_with_llm(preferences)
    parsed_events = parse_llm_response(llm_text_response)
    if not parsed_events:
        logging.error("Failed to generate a valid plan after parsing.")
        raise HTTPException(status_code=500, detail="Failed to generate a valid plan.")
    total_cost = sum(event.cost for event in parsed_events)
    total_duration = sum(event.duration for event in parsed_events)
    logging.info(f"Successfully created plan with {len(parsed_events)} events.")
    return OutingPlan(plan=parsed_events, total_cost=total_cost, total_duration=total_duration)


@app.post("/regenerate-event", response_model=OutingPlan)
async def regenerate_event(request: RegenerateRequest):
    logging.info(f"Received /regenerate-event request for index: {request.event_index_to_replace}")
    new_event_text = await get_single_replacement_event(request)
    new_events = parse_llm_response(new_event_text)
    if not new_events:
        logging.error("Failed to parse regenerated event.")
        raise HTTPException(status_code=500, detail="Failed to parse regenerated event.")
    updated_plan_events = request.current_plan
    updated_plan_events[request.event_index_to_replace] = new_events[0]
    total_cost = sum(event.cost for event in updated_plan_events)
    total_duration = sum(event.duration for event in updated_plan_events)
    logging.info(f"Successfully regenerated event at index {request.event_index_to_replace}.")
    return OutingPlan(plan=updated_plan_events, total_cost=total_cost, total_duration=total_duration)


@app.get("/")
def read_root():
    return {"message": "Welcome to the OneStopOutings API"}
