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

import json
import os
from pathlib import Path
import google.auth
import google.auth.transport.requests
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

def _get_default_agent_engine_resource_name() -> str:
    metadata_path = Path(__file__).parent.parent / "deployment_metadata.json"
    if metadata_path.exists():
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            if rt_id := data.get("remote_agent_runtime_id"):
                return rt_id
        except Exception:
            pass
    return "projects/17832453200/locations/us-east1/reasoningEngines/7132358206545723392"

AGENT_ENGINE_RESOURCE_NAME = os.getenv("AGENT_ENGINE_RESOURCE_NAME") or _get_default_agent_engine_resource_name()
AGENT_DIRECTORY = os.getenv("AGENT_DIRECTORY", "app")

app = FastAPI(title="Smart Recipe Assistant Frontend Proxy")

# Mount static files
frontend_dir = Path(__file__).parent
static_dir = frontend_dir / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def get_gcp_access_token() -> str:
    """Retrieves standard GCP access token using ADC."""
    credentials, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token


@app.get("/", response_class=HTMLResponse)
async def get_chat_ui():
    """Serves the main chat UI HTML page."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h2>Smart Recipe Assistant Chat UI</h2>")


FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-d2603dc6aba2"


@app.get("/api/config")
async def get_config():
    """Returns frontend configuration and agent binding details."""
    return {
        "agent_engine_resource_name": AGENT_ENGINE_RESOURCE_NAME,
        "agent_directory": AGENT_DIRECTORY,
        "status": "ready",
    }


@app.get("/api/allergies")
async def get_user_allergies(user_id: str):
    """Retrieves all active allergies stored in Firestore for a given user."""
    try:
        from google.cloud import firestore

        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        doc = db.collection("user_allergies").document(user_id).get()
        if not doc.exists:
            return {"allergies": []}
        data = doc.to_dict() or {}
        allergies = [k for k, v in data.items() if v is True and k not in ("user_id", "last_updated")]
        return {"allergies": allergies}
    except Exception as e:
        return {"allergies": [], "error": str(e)}


@app.post("/api/allergies")
async def update_user_allergy(request: Request):
    """Adds or removes an allergy key-value pair in Firestore for a given user."""
    body = await request.json()
    user_id = body.get("user_id")
    allergen = (body.get("allergen") or "").strip().lower()
    action = body.get("action", "add")  # "add" or "remove"

    if not user_id or not allergen:
        raise HTTPException(status_code=400, detail="user_id and allergen required.")

    try:
        from google.cloud import firestore

        db = firestore.Client(project=FIRESTORE_PROJECT_ID)
        doc_ref = db.collection("user_allergies").document(user_id)
        if action == "add":
            doc_ref.set({allergen: True, "user_id": user_id}, merge=True)
        elif action == "remove":
            doc_ref.set({allergen: False}, merge=True)

        doc = doc_ref.get()
        data = doc.to_dict() or {}
        allergies = [k for k, v in data.items() if v is True and k not in ("user_id", "last_updated")]
        return {"allergies": allergies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_proxy(request: Request):
    """Non-streaming proxy endpoint querying the deployed Agent Engine and returning clean text."""
    body = await request.json()
    user_message = body.get("message", "")
    user_id = body.get("user_id", "default_user")

    if not user_message:
        raise HTTPException(status_code=400, detail="Message is required.")

    parts_res_name = AGENT_ENGINE_RESOURCE_NAME.split("/")
    location = parts_res_name[3] if len(parts_res_name) >= 6 else "us-east1"

    url = f"https://{location}-aiplatform.googleapis.com/v1/{AGENT_ENGINE_RESOURCE_NAME}:streamQuery"

    payload = {
        "classMethod": "async_stream_query",
        "input": {
            "user_id": user_id,
            "message": user_message,
        },
    }

    try:
        token = get_gcp_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Agent Engine error: {response.text}",
            )

        text_parts = []
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    if "content" in data and "parts" in data["content"]:
                        for part in data["content"]["parts"]:
                            if "text" in part:
                                text_parts.append(part["text"])
                    elif "raw" in data:
                        text_parts.append(data["raw"])
                except Exception:
                    pass

        full_text = "".join(text_parts).strip()
        if not full_text:
            full_text = "Received empty response from agent."

        return JSONResponse(content={"response": full_text})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
