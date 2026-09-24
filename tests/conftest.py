import os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-d2603dc6aba2")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
