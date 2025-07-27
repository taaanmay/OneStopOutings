import os
import httpx
import logging
import time
import json
import uuid
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import List, Dict, Tuple

# Import the models
from model.models import UserPreferences, Event, OutingPlan, RegenerateRequest

# --- In-Memory Cache with TTL ---
api_cache: Dict[str, Tuple[OutingPlan, float]] = {}
CACHE_TTL_SECONDS = 86400

# --- Regeneration Limit Tracking ---
regeneration_counts: Dict[str, int] = {}
MAX_REGENERATIONS = 5

# Configure Logging
log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = os.path.join(log_directory, 'app.log')
file_handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
file_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

load_dotenv()
app = FastAPI()

# CORS Middleware
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- LLM and Parsing Functions ---

async def generate_plan_with_llm(preferences: UserPreferences):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logging.error("GOOGLE_API_KEY not found.")
        raise HTTPException(status_code=500, detail="Google API key not found.")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    mode_instruction = "Focus on quirky, offbeat gems." if preferences.mode == 'surprise' else "Focus on iconic, popular landmarks."
    prompt = f"""
    You are a Dublin tour planner API. Your response must be a valid JSON array of objects.
    Plan a 3-event day in Dublin based on these user preferences:
    - Mode: {preferences.mode}
    - Budget: {preferences.budget}
    - Interests: {', '.join(preferences.interests)}
    Instruction: {mode_instruction}
    IMPORTANT: Respond with ONLY the JSON array, nothing else. For free events, use a cost of 0.
    Example format:
    [
        {{"type": "Breakfast", "name": "The Early Bird Café", "cost": 15, "duration": 60}},
        {{"type": "Activity", "name": "National Museum of Ireland", "cost": 0, "duration": 120}},
        {{"type": "Lunch", "name": "Pizzeria Rustico", "cost": 25, "duration": 75}}
    ]
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        try:
            logging.info("CACHE MISS: Sending request to Gemini API for a full plan.")
            response = await client.post(api_url, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            if result.get('candidates'):
                llm_response = result['candidates'][0]['content']['parts'][0]['text']
                logging.info(f"LLM Response: {llm_response}")
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
    mode_instruction = "Suggest a quirky, offbeat alternative." if request.user_preferences.mode == 'surprise' else "Suggest an iconic or popular alternative."
    existing_event_names = [event.name for event in request.current_plan]
    prompt = f"""
    You are a Dublin tour planner API. Your response must be a single valid JSON object.
    A user wants to replace one event in their plan.
    - Event to Replace: "{request.current_plan[request.event_index_to_replace].name}"
    - User Interests: {', '.join(request.user_preferences.interests)}
    - Planning Mode: {request.user_preferences.mode}
    Instruction: {mode_instruction} The new event must not be in the existing plan: {', '.join(existing_event_names)}.
    IMPORTANT: Respond with ONLY the single JSON object, nothing else. For free events, use a cost of 0.
    Example format:
    {{"type": "Pub", "name": "The Brazen Head", "cost": 20, "duration": 90}}
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        logging.info("CACHE MISS: Sending request to Gemini API for a single replacement event.")
        response = await client.post(api_url, json=payload, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        if result.get('candidates'):
            llm_response = result['candidates'][0]['content']['parts'][0]['text']
            logging.info(f"LLM Replacement Response: {llm_response}")
            return llm_response
        else:
            logging.error(f"Unexpected API response for regeneration: {result}")
            raise HTTPException(status_code=500, detail="Could not parse LLM response for regeneration.")

# --- API Endpoints with Caching and Limits ---

@app.post("/plan", response_model=OutingPlan)
async def create_outing_plan(preferences: UserPreferences):
    cache_key = f"plan-{preferences.mode}-{preferences.budget}-{'-'.join(sorted(preferences.interests))}"
    if cache_key in api_cache:
        cached_plan_data, timestamp = api_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            logging.info(f"CACHE HIT for key: {cache_key}")
            outing_id = str(uuid.uuid4())
            regeneration_counts[outing_id] = 0
            new_session_plan = OutingPlan(
                plan=cached_plan_data.plan,
                total_cost=cached_plan_data.total_cost,
                total_duration=cached_plan_data.total_duration,
                outing_id=outing_id
            )
            return new_session_plan
        else:
            logging.info(f"CACHE EXPIRED for key: {cache_key}")
            del api_cache[cache_key]
    
    logging.info(f"Received /plan request with preferences: {preferences}")
    llm_text_response = await generate_plan_with_llm(preferences)
    
    try:
        cleaned_response = llm_text_response.strip().replace("```json", "").replace("```", "").strip()
        events_data = json.loads(cleaned_response)
        parsed_events = [Event(**data) for data in events_data]
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Failed to decode JSON from LLM response: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to parse plan from LLM.")

    if not parsed_events:
        logging.error("Failed to generate a valid plan after parsing.")
        raise HTTPException(status_code=500, detail="Failed to generate a valid plan.")
    
    total_cost = sum(event.cost for event in parsed_events)
    total_duration = sum(event.duration for event in parsed_events)
    
    outing_id = str(uuid.uuid4())
    regeneration_counts[outing_id] = 0
    
    final_plan = OutingPlan(plan=parsed_events, total_cost=total_cost, total_duration=total_duration, outing_id=outing_id)
    
    api_cache[cache_key] = (final_plan, time.time())
    logging.info(f"Successfully created and cached plan with {len(parsed_events)} events. Outing ID: {outing_id}")
    return final_plan

@app.post("/regenerate-event", response_model=OutingPlan)
async def regenerate_event(request: RegenerateRequest):
    current_regen_count = regeneration_counts.get(request.outing_id, 0)
    if current_regen_count >= MAX_REGENERATIONS:
        logging.warning(f"Regeneration limit reached for outing_id: {request.outing_id}")
        raise HTTPException(status_code=403, detail=f"Regeneration limit of {MAX_REGENERATIONS} reached for this outing.")

    # --- FIX: Make the cache key more specific to avoid incorrect hits ---
    event_to_replace_name = request.current_plan[request.event_index_to_replace].name
    cache_key = f"regen-{request.outing_id}-{request.event_index_to_replace}-{event_to_replace_name}"
    
    if cache_key in api_cache:
        cached_plan, timestamp = api_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            logging.info(f"CACHE HIT for regeneration key: {cache_key}")
            regeneration_counts[request.outing_id] = current_regen_count + 1
            return cached_plan
        else:
            logging.info(f"CACHE EXPIRED for regeneration key: {cache_key}")
            del api_cache[cache_key]

    logging.info(f"Received /regenerate-event request for outing_id {request.outing_id}, index: {request.event_index_to_replace}")
    new_event_text = await get_single_replacement_event(request)

    try:
        cleaned_response = new_event_text.strip().replace("```json", "").replace("```", "").strip()
        new_event_data = json.loads(cleaned_response)
        new_event = Event(**new_event_data)
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Failed to decode JSON from LLM for regeneration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to parse regenerated event.")

    updated_plan_events = request.current_plan
    updated_plan_events[request.event_index_to_replace] = new_event
    total_cost = sum(event.cost for event in updated_plan_events)
    total_duration = sum(event.duration for event in updated_plan_events)
    
    final_plan = OutingPlan(plan=updated_plan_events, total_cost=total_cost, total_duration=total_duration, outing_id=request.outing_id)
    
    api_cache[cache_key] = (final_plan, time.time())
    
    regeneration_counts[request.outing_id] = current_regen_count + 1
    logging.info(f"Successfully regenerated event at index {request.event_index_to_replace}. New count: {regeneration_counts[request.outing_id]}")
    
    return final_plan

@app.get("/")
def read_root():
    return {"message": "Welcome to the OneStopOutings API"}
