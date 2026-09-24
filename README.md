# Smart Recipe & Dietary Assistant

An intelligent personal chef and dietary safety guardian agent built with Google's Agent Development Kit (ADK), Google Cloud Firestore, Imagen image generation, and A2UI dynamic user interface rendering.

![Smart Recipe Assistant Demo](demo.gif)

---

## 🌟 What the Agent Does

The **Smart Recipe & Dietary Assistant** helps users discover customized recipes, scale ingredient portions, search nearby grocery markets, and enforce strict dietary safety boundaries.

### Implemented Capabilities

* **🛡️ Key-Value Allergy Memory (Firestore)**
  * Stores user dietary restrictions as key-value pairs in **Google Cloud Firestore** (`user_allergies` collection).
  * Automatically retrieves active allergy rules on every turn and strictly refuses recipes containing forbidden allergens.

* **🍲 Recipe Search & Strict Exclusion Filtering**
  * Searches stored recipes in Firestore (`search_recipes`) and live online sources (`fetch_online_recipes`).
  * Enforces allergen exclusion parameters to ensure no unsafe ingredients reach the user.

* **📊 Portion Scaling & Nutritional Macro Calculation**
  * Calculates scaled ingredient quantities based on custom serving counts (`scale_and_calculate_nutrition`).
  * Computes total calories, protein, carbohydrates, and fats.

* **📸 Generative Food Photography**
  * Generates high-quality dish imagery using **Google GenAI / Imagen** (`generate_recipe_image`).
  * Uploads generated culinary photos directly to **Google Cloud Storage** bucket.

* **🌿 Nicholas Culpeper Herbal Remedies**
  * Consults historical 1653 Nicholas Culpeper herbal medicine lore (`consult_culpeper_herbal`) for plant-based wellness guidance.

* **🏪 Local Grocery Market Finder**
  * Locates nearby grocery stores, supermarkets, and specialty food markets (`find_nearby_grocery_stores`).

* **🎨 A2UI Dynamic Interface Protocol**
  * Emits rich, structural `<a2ui-json>` protocol blocks parsed by the Fast API web interface into interactive Cards, Columns, Rows, Text, Images, and Action Buttons.

* **🧠 Multi-Turn Session Memory**
  * Retains multi-turn conversation context across sessions using ADK `MemoryService` and `PreloadMemoryTool`.

---

## 📋 Capabilities Matrix

| Service / Feature | Capability | Status |
| :--- | :--- | :--- |
| **Google Cloud Firestore** | Key-value allergy storage (`user_allergies`) & recipe queries | ✅ Implemented |
| **Google Cloud Storage** | Image artifact storage bucket | ✅ Implemented |
| **Vertex AI / Imagen** | Generative culinary photography (`generate_recipe_image`) | ✅ Implemented |
| **A2UI Protocol** | Rich dynamic UI rendering (`<a2ui-json>`) | ✅ Implemented |
| **Memory Bank** | Multi-turn dialogue session persistence (`PreloadMemoryTool`) | ✅ Implemented |
| **FastAPI Proxy Frontend** | Glassmorphic web chat interface & active allergy bar | ✅ Implemented |
| **Culpeper Herbal Database** | Historical plant remedy lookup | ✅ Implemented |
| **Smart Oven IoT Control** | Direct integration with smart appliances | ⏳ Planned (Not yet implemented) |
| **Automated Checkout** | Direct Instacart / Delivery cart population | ⏳ Planned (Not yet implemented) |

---

## 📁 Project Structure

```
smart-recipe-assistant/
├── app/                      # Core ADK Agent implementation
│   ├── agent.py              # Main agent definition & tool functions
│   ├── a2ui_utils.py         # A2UI prompt builder & callbacks
│   └── fast_api_app.py       # FastAPI backend entrypoint
├── frontend/                 # Web interface application
│   ├── app.py                # FastAPI proxy server & Firestore endpoints
│   └── static/index.html     # Rebranded A2UI glassmorphic chat interface
├── tests/                    # Unit and integration test suite
├── demo.gif                  # Recorded inline demonstration
├── pyproject.toml            # Project dependencies
└── agents-cli-manifest.yaml  # Agents CLI deployment manifest
```

---

## 🚀 Setup & Running Locally

### Prerequisites

* **Python**: 3.12+
* **uv**: Package manager ([Installation Guide](https://docs.astral.sh/uv/getting-started/installation/))
* **Google Cloud SDK**: Authenticated with `gcloud auth application-default login`

### 1. Installation

Install project dependencies using `agents-cli` or `uv`:

```bash
uv tool install google-agents-cli
agents-cli install
```

### 2. Run Agent Playground (Local Interactive CLI)

Test the agent logic locally in playground mode:

```bash
agents-cli playground
```

### 3. Run Web Frontend (Local Chat UI)

Launch the FastAPI web server to test the rebranded interface and A2UI dynamic components locally:

```bash
uv run python -m frontend.app
```

Once started, open your web browser to `http://localhost:8080` (or `http://127.0.0.1:8080`).

---

## 🧪 Testing & Evaluation

Run unit and integration tests:

```bash
uv run pytest tests/unit tests/integration
```

Evaluate agent behavior using `agents-cli`:

```bash
agents-cli eval generate
agents-cli eval grade
```

---

## ☁️ Deployment

To deploy the agent runtime and web frontend to Google Cloud:

```bash
# Set your target project ID
gcloud config set project <your-project-id>

# Deploy Agent Runtime
agents-cli deploy

# Deploy Web Frontend to Cloud Run
gcloud run deploy recipe-assistant-frontend --source ./frontend --region us-east1
```
