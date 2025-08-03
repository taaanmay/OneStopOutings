import os
import httpx
import logging
import time
import json
import uuid
import random
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import List, Dict, Tuple, Optional

# Import the models
from backend.model.models import UserPreferences, Event, OutingPlan, RegenerateRequest

# --- Local data dictionary ---
from backend.utils.popular_spots import PopularSpots


# --- Cache and Limit Configuration ---
api_cache: Dict[str, Tuple[OutingPlan, float]] = {}
image_cache: Dict[str, str] = {}
CACHE_TTL_SECONDS = 86400
regeneration_counts: Dict[str, int] = {}
MAX_REGENERATIONS = 5
LOCAL_REGEN_LIMIT = 3

# --- Persistent Image Cache Setup ---
IMAGE_CACHE_FILE = "/tmp/learned_images.json"

def load_image_cache():
    if os.path.exists(IMAGE_CACHE_FILE):
        with open(IMAGE_CACHE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_image_cache():
    with open(IMAGE_CACHE_FILE, 'w') as f:
        json.dump(image_cache, f, indent=2)

image_cache = load_image_cache()

# Configure Logging
log_directory = "/tmp/logs"
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

# --- UPDATED: Dynamic CORS Middleware ---
# This will work for both local development and your Vercel deployment.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Vercel provides an environment variable with the deployment's URL
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    # The URL from Vercel doesn't include the protocol, so we add it
    origins.append(f"https://{vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper to get all popular spot names ---
def get_all_popular_spot_names():
    names = set()
    for category in PopularSpots.spots.values():
        for spot in category:
            names.add(spot['name'])
    return list(names)

all_popular_names = get_all_popular_spot_names()


# --- Helper to dynamically add events to the local dictionary ---
def add_event_to_local_dictionary(event: Event):
    logging.info(f"Checking if '{event.name}' can be added to local dictionary.")
    category = "Activity"
    if "museum" in event.type.lower(): category = "Museum"
    elif "pub" in event.type.lower(): category = "Pub"
    elif any(food_type in event.type.lower() for food_type in ["food", "lunch", "dinner", "breakfast", "treat"]): category = "Food"

    if category in PopularSpots.spots:
        if not any(spot['name'].lower() == event.name.lower() for spot in PopularSpots.spots[category]):
            new_spot = {
                "type": event.type,
                "name": event.name,
                "cost": event.cost,
                "duration": event.duration,
                "image_url": event.image_url
            }
            PopularSpots.spots[category].append(new_spot)
            logging.info(f"Successfully added '{event.name}' with its image to the '{category}' category in local data.")
        else:
            logging.info(f"'{event.name}' already exists in local data. Skipping addition.")
    else:
        logging.warning(f"Category '{category}' not found in local data for event '{event.name}'. Cannot add.")


# --- Function to get and cache images ---
async def get_image_for_event(event_name: str) -> str:
    if event_name in image_cache:
        logging.info(f"IMAGE CACHE HIT for: {event_name}")
        return image_cache[event_name]
    
    logging.info(f"IMAGE CACHE MISS for: {event_name}. Fetching from Pexels.")
    pexels_api_key = os.getenv("PEXELS_API_KEY")
    if not pexels_api_key:
        logging.warning("PEXELS_API_KEY not found. Cannot fetch images.")
        return ""

    headers = {"Authorization": pexels_api_key}
    query = f"{event_name} Dublin"
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=1"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if data['photos']:
                image_url = data['photos'][0]['src']['tiny']
                image_cache[event_name] = image_url
                save_image_cache()
                return image_url
    except Exception as e:
        logging.error(f"Failed to fetch image for '{event_name}'. Error: {e}")
    
    return ""


# --- LLM and Helper Functions ---

async def generate_plan_with_llm(preferences: UserPreferences):
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logging.error("GOOGLE_API_KEY not found.")
        raise HTTPException(status_code=500, detail="Google API key not found.")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    mode_instruction = "Focus on quirky, offbeat gems." if preferences.mode == 'surprise' else "Focus on iconic, popular landmarks."
    
    prompt = f"""
    You are a Dublin tour planner API. Your entire response must be only the raw JSON text.
    Plan a 3-event day in Dublin based on these user preferences:
    - Mode: {preferences.mode}
    - Budget: {preferences.budget}
    - Interests: {', '.join(preferences.interests)}
    Instruction: {mode_instruction}
    CRITICAL INSTRUCTION: Do not suggest any of the following well-known places: {', '.join(all_popular_names)}.
    IMPORTANT: Respond with ONLY a valid JSON array of objects, with no introductory text, no markdown, and no explanations.
    Example format:
    [
        {{"type": "Breakfast", "name": "The Early Bird Café", "cost": 15, "duration": 60}},
        {{"type": "Activity", "name": "A lesser-known gallery", "cost": 0, "duration": 120}},
        {{"type": "Lunch", "name": "A unique food market", "cost": 25, "duration": 75}}
    ]
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient() as client:
        logging.info("Sending request to Gemini API for a full plan.")
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

async def get_llm_replacement_event(request: RegenerateRequest) -> Event:
    try:
        logging.info("Attempting to get replacement from LLM first.")
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("API Key not found")
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        mode_instruction = "Suggest a quirky, offbeat alternative." if request.user_preferences.mode == 'surprise' else "Suggest an iconic or popular alternative."
        
        existing_event_names = {event.name for event in request.current_plan}
        exclusion_list = list(existing_event_names.union(set(all_popular_names)))

        prompt = f"""
        You are a Dublin tour planner API. Your entire response must be only the raw JSON text.
        A user wants to replace one event in their plan.
        - Event to Replace: "{request.current_plan[request.event_index_to_replace].name}"
        - User Interests: {', '.join(request.user_preferences.interests)}
        - Planning Mode: {request.user_preferences.mode}
        Instruction: {mode_instruction}
        CRITICAL INSTRUCTION: The new event must not be in the following list: {', '.join(exclusion_list)}.
        IMPORTANT: Respond with ONLY a single valid JSON object, with no introductory text, no markdown, and no explanations.
        Example format:
        {{"type": "Pub", "name": "A hidden local pub", "cost": 20, "duration": 90}}
        """
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            if result.get('candidates'):
                llm_response = result['candidates'][0]['content']['parts'][0]['text']
                logging.info(f"LLM Replacement Response: {llm_response}")
                cleaned_response = llm_response.strip().replace("```json", "").replace("```", "").strip()
                new_event_data = json.loads(cleaned_response)
                new_event = Event(**new_event_data)
                return new_event
            else:
                raise ValueError("LLM response did not contain candidates.")
    except Exception as e:
        logging.warning(f"LLM call failed for regeneration, attempting local fallback. Error: {e}")
        return get_local_replacement_event(request)

def get_local_replacement_event(request: RegenerateRequest) -> Optional[Event]:
    logging.info("Attempting to find a replacement from local data.")
    event_to_replace = request.current_plan[request.event_index_to_replace]
    category = "Activity"
    if "museum" in event_to_replace.type.lower(): category = "Museum"
    elif "pub" in event_to_replace.type.lower(): category = "Pub"
    elif any(food_type in event_to_replace.type.lower() for food_type in ["food", "lunch", "dinner", "breakfast"]): category = "Food"
    
    potential_replacements = PopularSpots.spots.get(category, [])
    existing_names = {e.name for e in request.current_plan}
    valid_choices = [spot for spot in potential_replacements if spot["name"] not in existing_names]
    
    if valid_choices:
        logging.info(f"Found {len(valid_choices)} local candidates for replacement.")
        local_choice = random.choice(valid_choices)
        return Event(**local_choice)
    else:
        logging.warning("No suitable local replacement found.")
        return None


# --- API Endpoints ---

@app.post("/api/plan", response_model=OutingPlan)
async def create_outing_plan(preferences: UserPreferences):
    logging.info(f"Creating outing plan with preferences: {preferences}")
    cache_key = f"plan-{preferences.mode}-{preferences.budget}-{'-'.join(sorted(preferences.interests))}"
    if cache_key in api_cache:
        cached_plan_data, timestamp = api_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL_SECONDS:
            logging.info(f"CACHE HIT for key: {cache_key}")
            outing_id = str(uuid.uuid4())
            regeneration_counts[outing_id] = 0
            new_session_plan = OutingPlan(plan=cached_plan_data.plan, total_cost=cached_plan_data.total_cost, total_duration=cached_plan_data.total_duration, outing_id=outing_id)
            return new_session_plan
        else:
            logging.info(f"CACHE EXPIRED for key: {cache_key}")
            del api_cache[cache_key]
    
    logging.info(f"Received /plan request with preferences: {preferences}")
    
    parsed_events = None
    is_llm_plan = False
    try:
        llm_text_response = await generate_plan_with_llm(preferences)
        cleaned_response = llm_text_response.strip().replace("```json", "").replace("```", "").strip()
        events_data = json.loads(cleaned_response)
        parsed_events = [Event(**data) for data in events_data]
        is_llm_plan = True
    except Exception as e:
        logging.error(f"LLM call failed for new plan, attempting local fallback. Error: {e}", exc_info=True)
        try:
            logging.info("Attempting to generate plan from local data as a fallback.")
            parsed_events = [
                Event(**random.choice(PopularSpots.spots["Food"])),
                Event(**random.choice(PopularSpots.spots["Activity"])),
                Event(**random.choice(PopularSpots.spots["Museum"])),
            ]
            if len({e.name for e in parsed_events}) != 3:
                 raise ValueError("Duplicate events selected in fallback.")
        except (KeyError, IndexError, ValueError) as fallback_e:
             logging.error(f"Local fallback also failed. Error: {fallback_e}")
             raise HTTPException(status_code=500, detail="Failed to generate plan from any source.")

    if not parsed_events:
        logging.error("Failed to generate a valid plan after all attempts.")
        raise HTTPException(status_code=500, detail="Failed to generate a valid plan.")
    
    for event in parsed_events:
        if not event.image_url:
            event.image_url = await get_image_for_event(event.name)
        if is_llm_plan:
            add_event_to_local_dictionary(event)

    total_cost = sum(event.cost for event in parsed_events)
    total_duration = sum(event.duration for event in parsed_events)
    
    outing_id = str(uuid.uuid4())
    regeneration_counts[outing_id] = 0
    
    final_plan = OutingPlan(plan=parsed_events, total_cost=total_cost, total_duration=total_duration, outing_id=outing_id)
    
    if is_llm_plan:
        api_cache[cache_key] = (final_plan, time.time())
        logging.info(f"Successfully created and cached LLM plan with {len(parsed_events)} events. Outing ID: {outing_id}")
    else:
        logging.info(f"Successfully created local fallback plan with {len(parsed_events)} events. Outing ID: {outing_id}")

    return final_plan

@app.post("/api/regenerate-event", response_model=OutingPlan)
async def regenerate_event(request: RegenerateRequest):
    current_regen_count = regeneration_counts.get(request.outing_id, 0)
    if current_regen_count >= MAX_REGENERATIONS:
        logging.warning(f"Regeneration limit reached for outing_id: {request.outing_id}")
        raise HTTPException(status_code=403, detail=f"Regeneration limit of {MAX_REGENERATIONS} reached for this outing.")

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

    logging.info(f"Received /regenerate-event request for outing_id {request.outing_id}, index: {request.event_index_to_replace}. Count: {current_regen_count}")
    
    new_event = None
    if current_regen_count < LOCAL_REGEN_LIMIT:
        logging.info("Attempting local-first regeneration.")
        new_event = get_local_replacement_event(request)
        if not new_event:
            logging.warning("Local-first failed, escalating to LLM.")
            new_event = await get_llm_replacement_event(request)
    else:
        logging.info("Local limit reached, using LLM-first regeneration.")
        new_event = await get_llm_replacement_event(request)

    if not new_event:
        raise HTTPException(status_code=500, detail="Could not find a suitable replacement from any source.")

    if not new_event.image_url:
        new_event.image_url = await get_image_for_event(new_event.name)
    
    add_event_to_local_dictionary(new_event)

    updated_plan_events = request.current_plan
    updated_plan_events[request.event_index_to_replace] = new_event
    total_cost = sum(event.cost for event in updated_plan_events)
    total_duration = sum(event.duration for event in updated_plan_events)
    
    final_plan = OutingPlan(plan=updated_plan_events, total_cost=total_cost, total_duration=total_duration, outing_id=request.outing_id)
    
    api_cache[cache_key] = (final_plan, time.time())
    
    regeneration_counts[request.outing_id] = current_regen_count + 1
    logging.info(f"Successfully regenerated event at index {request.event_index_to_replace}. New count: {regeneration_counts[request.outing_id]}")
    
    return final_plan

@app.get("/api")
def read_root():
    return {"message": "Welcome to the OneStopOutings API"}
