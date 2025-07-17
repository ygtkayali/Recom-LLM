import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load API Key from .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Data Source Configuration ---
DATA_SOURCE_TYPE = "JSON"
PRODUCT_JSON_FILEPATH = "product_cache.json"
CLASS_DESCRIPTIONS_MODULE = "class_descriptions"

# --- PGVector and Database Configuration ---
DATABASE_CONNECTION_STRING = os.getenv("DATABASE_URL")
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
PRODUCTS_COLLECTION_NAME = "products"  # Table name for productse
CLASS_DESCRIPTIONS_COLLECTION_NAME = "skin_conditions"

# --- Embedding Model Configuration ---
SENTENCE_TRANSFORMER_MODEL_NAME = "all-mpnet-base-v2"

# --- LLM Configuration ---
LLM_MODEL_NAME = "gpt-3.5-turbo"  # or "gpt-3.5-turbo" etc.

# --- Product Features for Embedding Text ---
PRODUCT_FEATURES_FOR_EMBEDDING = [
    "name", "keyBenefits", "description", "howToUse", "timeOfUse",
    "recommendedUsageDuration", "doNotUseWith", "activeContent",
    "contents", "price", "discountedPrice","concerns", "skinTypes"
]

FEATURE_LABELS = {
    "name": "Product Name", 
    "keyBenefits": "Key Benefits", 
    "description": "Detailed Description",
    "howToUse": "How to Use", 
    "timeOfUse": "Recommended Time of Use",
    "recommendedUsageDuration": "Recommended Usage Duration", 
    "doNotUseWith": "Do Not Use With / Contraindications",
    "activeContent": "Key Active Ingredients", 
    "contents": "Full Ingredients List (INCI)",
    "price": "Price", 
    "discountedPrice": "Discounted Price",
    "concerns": "Target concerns",
    "skinTypes":"Usable Skin Types"
}
