# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import json
import uuid
from zoneinfo import ZoneInfo

import os
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore
from google.genai import types

from app.a2ui_utils import build_a2ui_prompt, a2ui_after_model_callback

FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-d2603dc6aba2"
STORAGE_BUCKET_NAME = "smart-recipe-assistant-qwiklabs-gcp-03-d2603dc6aba2"


def record_user_allergy(allergen: str, tool_context: ToolContext) -> str:
    """Stores a user's food allergy as a key-value pair in the Firestore database.

    Args:
        allergen: The name of the food item or allergen (e.g. 'prawn', 'shrimp', 'peanuts', 'dairy').
        tool_context: ADK ToolContext automatically passed by the runner.

    Returns:
        Confirmation message that the allergy was recorded in Firestore.
    """
    try:
        user_id = getattr(tool_context, "user_id", "default_user") or "default_user"
        clean_allergen = allergen.strip().lower()
        if not clean_allergen:
            return "No allergen provided."

        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        doc_ref = db.collection("user_allergies").document(user_id)

        doc_ref.set({
            clean_allergen: True,
            "user_id": user_id,
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }, merge=True)

        return f"Successfully recorded key-value allergy '{clean_allergen}': True for user '{user_id}' in Firestore database."
    except Exception as e:
        return f"Error recording allergy in Firestore: {e}"


def check_user_allergies(tool_context: ToolContext) -> str:
    """Retrieves all stored key-value food allergies for the current user from Firestore.

    Args:
        tool_context: ADK ToolContext automatically passed by the runner.

    Returns:
        JSON string of active user allergies.
    """
    try:
        user_id = getattr(tool_context, "user_id", "default_user") or "default_user"
        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        doc = db.collection("user_allergies").document(user_id).get()

        if not doc.exists:
            return json.dumps([])

        data = doc.to_dict() or {}
        allergies = [k for k, v in data.items() if v is True and k not in ("user_id", "last_updated")]
        return json.dumps(allergies)
    except Exception as e:
        return f"Error checking user allergies from Firestore: {e}"


def search_recipes(query: str = "", max_prep_time_mins: int = 0, exclude_allergens: str = "") -> str:
    """Searches stored recipes in the Firestore database.

    Args:
        query: Optional search keyword for title, tags, or ingredients (e.g., 'salad', 'chicken', 'quick').
        max_prep_time_mins: Optional maximum preparation time in minutes.
        exclude_allergens: Optional comma-separated list of allergens to exclude (e.g., 'peanuts, shellfish').

    Returns:
        A JSON string containing the list of matching recipes.
    """
    try:
        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        recipes_ref = db.collection("recipes")
        docs = recipes_ref.stream()

        results = []
        excluded = [a.strip().lower() for a in exclude_allergens.split(",") if a.strip()]

        for doc in docs:
            data = doc.to_dict()
            title = data.get("title", "")
            tags = [t.lower() for t in data.get("tags", [])]
            ingredients = [i.lower() for i in data.get("ingredients", [])]
            prep_time = data.get("prep_time_mins", 0)
            doc_allergens = [a.lower() for a in data.get("allergens", [])]

            # Filter by max prep time
            if max_prep_time_mins > 0 and prep_time > max_prep_time_mins:
                continue

            # Filter by excluded allergens
            if any(allergen in doc_allergens for allergen in excluded):
                continue
            if any(allergen in " ".join(ingredients) for allergen in excluded):
                continue

            # Filter by query
            if query:
                q = query.lower()
                matches_title = q in title.lower()
                matches_tags = any(q in t for t in tags)
                matches_ingredients = any(q in i for i in ingredients)
                if not (matches_title or matches_tags or matches_ingredients):
                    continue

            results.append(data)

        if not results:
            return f"No recipes found in Firestore matching query '{query}'."
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error searching recipes in Firestore: {e}"


def save_recipe(title: str, prep_time_mins: int, ingredients: str, instructions: str, allergens: str = "", tags: str = "") -> str:
    """Saves a new custom recipe to the Firestore database.

    Args:
        title: The name of the recipe.
        prep_time_mins: Preparation time in minutes.
        ingredients: Comma-separated list of ingredients.
        instructions: Step-by-step cooking instructions.
        allergens: Comma-separated list of allergens contained in the recipe (e.g. 'peanuts, soy').
        tags: Comma-separated list of descriptive tags (e.g. 'vegetarian, dinner').

    Returns:
        A string confirming successful creation with the document ID.
    """
    try:
        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        doc_id = f"recipe-{uuid.uuid4().hex[:8]}"

        ingredient_list = [i.strip() for i in ingredients.split(",") if i.strip()]
        allergen_list = [a.strip().lower() for a in allergens.split(",") if a.strip()]
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]

        recipe_doc = {
            "id": doc_id,
            "title": title,
            "prep_time_mins": prep_time_mins,
            "ingredients": ingredient_list,
            "instructions": instructions,
            "allergens": allergen_list,
            "tags": tag_list,
        }

        db.collection("recipes").document(doc_id).set(recipe_doc)
        return f"Successfully saved recipe '{title}' to Firestore with ID '{doc_id}'."
    except Exception as e:
        return f"Error saving recipe to Firestore: {e}"


def scale_and_calculate_nutrition(
    servings_original: int,
    servings_target: int,
    ingredients_summary: str = "",
    base_calories_per_serving: int = 400,
) -> str:
    """Scales recipe ingredient proportions and calculates estimated nutrition information.

    Args:
        servings_original: The original number of servings for the recipe (e.g. 2 or 4).
        servings_target: The target number of servings desired by the user (e.g. 6).
        ingredients_summary: A brief description or list of main ingredients.
        base_calories_per_serving: Estimated base calories per serving (default 400).

    Returns:
        A JSON string with scaling multiplier, target servings, and estimated total calories & macronutrients.
    """
    if servings_original <= 0:
        servings_original = 1
    if servings_target <= 0:
        servings_target = 1

    scale_factor = round(servings_target / servings_original, 2)
    total_calories = base_calories_per_serving * servings_target
    protein_g = round(servings_target * 20, 1)
    carbs_g = round(servings_target * 45, 1)
    fat_g = round(servings_target * 15, 1)

    result = {
        "servings_original": servings_original,
        "servings_target": servings_target,
        "scale_factor": scale_factor,
        "ingredients_summary": ingredients_summary,
        "nutrition_estimate": {
            "calories_per_serving": base_calories_per_serving,
            "total_calories": total_calories,
            "estimated_protein_g": protein_g,
            "estimated_carbs_g": carbs_g,
            "estimated_fat_g": fat_g,
        },
        "note": f"To adjust ingredient quantities, multiply all base ingredient amounts by {scale_factor}x.",
    }
    return json.dumps(result, indent=2)


def fetch_online_recipes(query: str = "chicken", exclude_allergens: str = "") -> str:
    """Fetches real online recipes and meal ideas from the free public TheMealDB API, excluding any specified allergens.

    Args:
        query: Search keyword for online recipes (e.g., 'chicken', 'pasta', 'salad', 'curry').
        exclude_allergens: Optional comma-separated list of allergens to strictly exclude (e.g., 'prawn, shellfish, peanuts').

    Returns:
        A JSON string containing real online recipes with ingredients, category, area, and instructions.
    """
    import os
    import urllib.parse
    import urllib.request

    api_key = os.getenv("THEMEALDB_API_KEY", "1")
    raw_query = (query or "chicken").strip().lower()
    excluded = [a.strip().lower() for a in exclude_allergens.split(",") if a.strip()]

    for exc in excluded:
        if exc in raw_query:
            return json.dumps({
                "status": "REFUSED_ALLERGEN",
                "allergen": exc,
                "message": f"REFUSAL MANDATED: The requested query '{query}' contains the user's stored allergen '{exc}'. You MUST POLITELY REFUSE this request and ask for a different recipe name."
            })

    def fetch_meals_for_term(term: str):
        safe_term = urllib.parse.quote(term)
        url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={safe_term}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SmartRecipeAssistant/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                return data.get("meals") or []
        except Exception:
            return []

    try:
        words = [w for w in raw_query.split() if w not in ("with", "and", "in", "of", "for", "a", "the")]
        search_terms = [raw_query] + words

        # Expand search terms for pasta/noodle queries
        if "pasta" in words or "noodle" in words or "spaghetti" in words:
            search_terms.extend(["alfredo", "fettuccine", "spaghetti", "penne", "macaroni", "lasagne", "linguine", "pasta"])
        if "chicken" in words:
            search_terms.extend(["chicken"])

        seen_ids = set()
        all_meals = []

        for term in search_terms:
            term_meals = fetch_meals_for_term(term)
            for meal in term_meals:
                meal_id = meal.get("idMeal")
                if meal_id and meal_id not in seen_ids:
                    seen_ids.add(meal_id)
                    all_meals.append(meal)

        pasta_synonyms = {"pasta", "spaghetti", "fettuccine", "penne", "macaroni", "lasagne", "linguine", "alfredo", "rigatoni", "tagliatelle", "passata"}

        def score_meal(m):
            title = (m.get("strMeal") or "").lower()
            cat = (m.get("strCategory") or "").lower()
            ingredients = " ".join([m.get(f"strIngredient{i}", "") or "" for i in range(1, 21)]).lower()
            text = f"{title} {cat} {ingredients} {m.get('strInstructions', '').lower()}"

            score = 0
            for w in words:
                if w in title:
                    score += 5
                elif w in cat or w in ingredients:
                    score += 3
                elif w in text:
                    score += 1

            has_chicken = "chicken" in title or "chicken" in ingredients or "chicken" in text
            has_pasta = any(ps in title or ps in ingredients for ps in pasta_synonyms)

            if "chicken" in words and ("pasta" in words or "spaghetti" in words or "noodle" in words):
                if has_chicken and has_pasta:
                    score += 20

            return score

        all_meals.sort(key=score_meal, reverse=True)

        simplified_meals = []
        for meal in all_meals:
            title = (meal.get("strMeal") or "").lower()
            ingredients = []
            ing_text_parts = []
            for i in range(1, 21):
                ing = meal.get(f"strIngredient{i}")
                measure = meal.get(f"strMeasure{i}")
                if ing and ing.strip():
                    ing_str = f"{measure.strip() if measure else ''} {ing.strip()}".strip()
                    ingredients.append(ing_str)
                    ing_text_parts.append(ing.strip().lower())

            full_meal_text = f"{title} {' '.join(ing_text_parts)}"

            # Exclude meal if any allergen is present
            if any(exc in full_meal_text for exc in excluded):
                continue

            raw_inst = (meal.get("strInstructions") or "").replace("\r\n", "\n").replace("\r", "\n").strip()
            simplified_meals.append({
                "id": meal.get("idMeal"),
                "title": meal.get("strMeal"),
                "category": meal.get("strCategory"),
                "area": meal.get("strArea"),
                "instructions": (raw_inst[:300] + "..." if len(raw_inst) > 300 else raw_inst),
                "ingredients": ingredients,
                "thumbnail_url": meal.get("strMealThumb"),
            })
            if len(simplified_meals) >= 5:
                break

        if not simplified_meals:
            return f"No online recipes found matching '{query}' that comply with allergen restrictions '{exclude_allergens}'."

        return json.dumps(simplified_meals, indent=2)
    except Exception as e:
        return f"Error fetching online recipes from public API: {e}"


def geocode_address(address: str) -> str:
    """Converts a human-readable street address into geographic coordinates (latitude and longitude) using Google Maps Geocoding API.

    Args:
        address: The street address or location name to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A JSON string containing the formatted address, latitude, longitude, and place_id.
    """
    import os
    import urllib.parse
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    safe_address = urllib.parse.quote(address.strip())
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={safe_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            results = data.get("results", [])
            if not results:
                return f"No location results found for address '{address}'."

            first = results[0]
            loc = first.get("geometry", {}).get("location", {})
            return json.dumps(
                {
                    "formatted_address": first.get("formatted_address"),
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng"),
                    "place_id": first.get("place_id"),
                },
                indent=2,
            )
    except Exception as e:
        return f"Error geocoding address: {e}"


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "supermarket",
    radius_meters: float = 1500.0,
) -> str:
    """Finds nearby places of a given type around a latitude/longitude location using Google Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g. 'supermarket', 'grocery_store', 'restaurant', 'bakery').
        radius_meters: Search radius in meters (default 1500 meters).

    Returns:
        A JSON string listing nearby places with their name, address, and location coordinates.
    """
    import os
    import urllib.request

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return "Error: GOOGLE_MAPS_API_KEY environment variable is not set."

    url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "includedTypes": [place_type.strip().lower()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            }
        },
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            raw_places = data.get("places", [])
            if not raw_places:
                return f"No nearby places found of type '{place_type}'."

            places = []
            for p in raw_places:
                display_name = p.get("displayName", {}).get("text", "")
                formatted_address = p.get("formattedAddress", "")
                loc = p.get("location", {})
                places.append({
                    "name": display_name,
                    "address": formatted_address,
                    "location": loc,
                })

            return json.dumps(places, indent=2)
    except Exception as e:
        return f"Error finding nearby places: {e}"


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


async def generate_memories_callback(callback_context: CallbackContext):
    """Sends the session events to Vertex AI Memory Bank after each turn to save user preferences, allergies, and interactions."""
    if getattr(callback_context, "memory_service", None) is not None:
        try:
            await callback_context.add_session_to_memory()
        except Exception as e:
            print(f"Memory save notification: {e}")
    return None


def consult_herbal_docs(query: str) -> str:
    """Search Nicholas Culpeper's Complete Herbal corpus for medicinal plants, herbs, natural remedies, and historical recipes.

    Args:
        query: What to look up in the herbal corpus (e.g. 'rosemary remedy for headache', 'thyme virtues', or 'mint').
    Returns:
        The matched passages from Nicholas Culpeper's Complete Herbal.
    """
    import os
    import re
    import vertexai
    from vertexai.preview import rag

    # 1. Attempt Vertex AI RAG Engine retrieval_query
    try:
        vertexai.init(project=FIRESTORE_PROJECT_ID, location="us-west1")
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[
                rag.RagResource(
                    rag_corpus="projects/qwiklabs-gcp-03-d94214de97af/locations/us-west1/ragCorpora/4611686018427387904"
                )
            ],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        if passages:
            return "\n\n---\n\n".join(passages)
    except Exception:
        pass

    # 2. Local fallback retrieval on pg49513.txt
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pg49513.txt")
    if not os.path.exists(local_path):
        return "Herbal document corpus file not found."

    try:
        with open(local_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        query_words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
        scored = []
        for p in paragraphs:
            p_lower = p.lower()
            score = sum(1 for w in query_words if w in p_lower)
            if score > 0:
                scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = [p for s, p in scored[:5]]
        return "\n\n---\n\n".join(top_matches) if top_matches else "No matching passages found in the herbal corpus."
    except Exception as e:
        return f"Retrieval failed: {e}"


async def generate_recipe_image(dish_name: str, tool_context: ToolContext) -> str:
    """Generates a visual image of a recipe dish using AI, saves it as an artifact, uploads it to public Cloud Storage, and returns its public URL.

    Args:
        dish_name: The name or description of the recipe dish to generate an image for (e.g., 'Fresh Basil Tomato Pasta' or 'Strawberry Mint Soup').
        tool_context: The ADK tool context provided automatically by the runner.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    import inspect
    import re
    import uuid
    from google import genai
    from google.cloud import storage
    from google.genai import types

    # 1. Generate image using gemini-3.1-flash-lite-image in global region
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    prompt = f"A professional, vibrant, delicious culinary photograph of {dish_name}, beautifully plated and ready to serve."

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )
    except Exception as e:
        return f"Failed to generate image: {e}"

    image_bytes = None
    for candidate in getattr(response, "candidates", []):
        for part in getattr(candidate.content, "parts", []):
            if getattr(part, "inline_data", None):
                image_bytes = part.inline_data.data
                break
        if image_bytes:
            break

    if not image_bytes:
        return f"No image data was generated for '{dish_name}'."

    clean_name = re.sub(r"[^\w\-]", "_", dish_name.lower().strip())[:30]
    unique_filename = f"{clean_name}_{uuid.uuid4().hex[:8]}.png"

    # (1) Save artifact with tool_context.save_artifact so it shows up in Playground's Artifacts panel
    if tool_context and hasattr(tool_context, "save_artifact"):
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
            res = tool_context.save_artifact(filename=unique_filename, artifact=artifact_part)
            if inspect.isawaitable(res):
                await res
        except Exception as e:
            print(f"Warning: Failed to save artifact: {e}")

    # (2) Upload same image bytes to public Cloud Storage bucket and return public https URL
    try:
        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
        blob_path = f"dishes/{unique_filename}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type="image/png")
        public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/{blob_path}"
        return public_url
    except Exception as e:
        return f"Failed to upload image to Cloud Storage: {e}"


# Read Agent Engine resource name from deployment_metadata.json if present
_metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
_agent_engine_resource_name = None
if os.path.exists(_metadata_path):
    try:
        with open(_metadata_path, "r") as _f:
            _metadata = json.load(_f)
            _agent_engine_resource_name = _metadata.get("remote_agent_runtime_id")
    except Exception as _e:
        print(f"Warning: Failed to load deployment_metadata.json: {_e}")

code_executor = None
if _agent_engine_resource_name:
    try:
        code_executor = AgentEngineSandboxCodeExecutor(
            agent_engine_resource_name=_agent_engine_resource_name
        )
    except Exception as _e:
        print(f"Warning: Could not initialize AgentEngineSandboxCodeExecutor: {_e}")

_role_description = (
    "You are a Smart Recipe & Dietary Assistant.\n"
    "CRITICAL FIRESTORE ALLERGY & REFUSAL RULES:\n"
    "1. Whenever the user states or mentions an allergy, food restriction, or intolerance (e.g. 'I am allergic to prawn', 'allergy: peanuts', 'I cannot eat shrimp'), you MUST IMMEDIATELY call `record_user_allergy(allergen=...)` to store the allergy as a key-value pair in Firestore.\n"
    "2. BEFORE responding to ANY recipe request, food query, or meal recommendation, ALWAYS call `check_user_allergies()` to fetch all active user allergies stored in Firestore.\n"
    "3. POLITE REFUSAL RULE: If the user explicitly asks for a dish or recipe that contains their stored allergy in the name or ingredients (e.g. asking for 'prawn pasta' or 'prawn curry' when allergic to prawn), or if any searched recipe contains their stored allergen in the title or ingredients: You MUST POLITELY REFUSE the request (e.g. 'I see you are allergic to prawn, so I cannot provide a prawn recipe for your safety.') AND ask the user to request a different recipe name (e.g. 'Would you like a Chicken Alfredo or Vegetable Pasta recipe instead?'). DO NOT render an A2UI card for a refused dish.\n"
    "4. When searching for recipes, ALWAYS pass all stored user allergies into `exclude_allergens` in `search_recipes` and `fetch_online_recipes`.\n"
    "5. ABSOLUTELY NEVER suggest, list, or present any recipe or ingredient containing a user allergen.\n"
    "6. Use `save_recipe` when the user asks to save or store a new recipe.\n"
    "7. Use `scale_and_calculate_nutrition` when the user asks to adjust serving sizes or scale recipe quantities.\n"
    "8. Use `fetch_online_recipes` to search for real global recipes.\n"
    "9. Use `geocode_address` to turn street addresses into geographic coordinates.\n"
    "10. Use `find_nearby_places` to find nearby supermarkets, grocery stores, restaurants, or bakeries.\n"
    "11. Use `consult_herbal_docs` to search Nicholas Culpeper's Complete Herbal document corpus.\n"
    "12. Use `generate_recipe_image` to generate a photo of a dish using AI.\n"
    "13. ALWAYS render safe non-refused recipes using A2UI UI JSON components wrapped in <a2ui-json> and </a2ui-json> tags. If a request is refused due to allergies, reply with plain polite text and ask for a different recipe name."
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        vertexai=True,
        project=FIRESTORE_PROJECT_ID,
        location="us-east1",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=build_a2ui_prompt(_role_description, version="0.8"),
    tools=[
        PreloadMemoryTool(),
        record_user_allergy,
        check_user_allergies,
        search_recipes,
        save_recipe,
        scale_and_calculate_nutrition,
        fetch_online_recipes,
        geocode_address,
        find_nearby_places,
        consult_herbal_docs,
        generate_recipe_image,
        get_weather,
        get_current_time,
    ],
    code_executor=code_executor,
    after_model_callback=a2ui_after_model_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)

