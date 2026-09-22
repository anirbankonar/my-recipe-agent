# Copyright 2026 Google LLC
# Seed script for Firestore recipes collection in smart-recipe-assistant

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-03-d94214de97af"

SEED_RECIPES = [
    {
        "id": "recipe-mediterranean-quinoa-salad",
        "title": "Mediterranean Quinoa Salad",
        "prep_time_mins": 15,
        "ingredients": [
            "1 cup cooked quinoa",
            "1/2 cucumber, diced",
            "1 cup cherry tomatoes, halved",
            "1/4 red onion, diced",
            "1/2 cup chickpeas",
            "2 tbsp olive oil",
            "1 tbsp lemon juice"
        ],
        "instructions": "Combine all ingredients in a bowl, drizzle with olive oil and lemon juice, and toss well.",
        "allergens": [],
        "tags": ["vegetarian", "gluten-free", "healthy", "salad", "peanut-free", "shellfish-free"]
    },
    {
        "id": "recipe-peanut-free-chicken-stir-fry",
        "title": "Garlic Ginger Chicken Stir-Fry",
        "prep_time_mins": 20,
        "ingredients": [
            "1 lb chicken breast, sliced",
            "2 cups broccoli florets",
            "1 red bell pepper, sliced",
            "2 tbsp soy sauce",
            "1 tbsp minced ginger",
            "2 cloves garlic, minced",
            "1 tbsp sesame oil"
        ],
        "instructions": "Sauté chicken in sesame oil until browned. Add vegetables, garlic, ginger, and soy sauce. Stir-fry for 5-7 minutes.",
        "allergens": ["soy", "sesame"],
        "tags": ["dairy-free", "peanut-free", "shellfish-free", "high-protein"]
    },
    {
        "id": "recipe-avocado-egg-toast",
        "title": "Avocado & Poached Egg Toast",
        "prep_time_mins": 10,
        "ingredients": [
            "2 slices sourdough bread, toasted",
            "1 ripe avocado, mashed",
            "2 poached eggs",
            "Salt, black pepper, and red pepper flakes to taste"
        ],
        "instructions": "Spread mashed avocado onto toast. Top each slice with a poached egg and season to taste.",
        "allergens": ["egg", "gluten"],
        "tags": ["vegetarian", "breakfast", "peanut-free", "shellfish-free", "quick"]
    },
    {
        "id": "recipe-salmon-buddha-bowl",
        "title": "Roasted Salmon & Sweet Potato Bowl",
        "prep_time_mins": 25,
        "ingredients": [
            "2 salmon fillets",
            "1 sweet potato, cubed and roasted",
            "2 cups steamed spinach",
            "1 tbsp olive oil",
            "1 tbsp honey mustard dressing"
        ],
        "instructions": "Roast salmon and sweet potatoes at 400°F for 20 minutes. Assemble in bowls over steamed spinach and drizzle with dressing.",
        "allergens": ["fish"],
        "tags": ["gluten-free", "dairy-free", "peanut-free", "shellfish-free", "dinner"]
    }
]


def seed_database():
    print(f"Connecting to Firestore for project: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("recipes")

    for recipe in SEED_RECIPES:
        doc_id = recipe["id"]
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(recipe)
        print(f"  ✓ Seeded recipe: '{recipe['title']}' ({doc_id})")

    print("\n✅ Successfully seeded Firestore 'recipes' collection!")


if __name__ == "__main__":
    seed_database()
