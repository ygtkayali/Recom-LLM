import os
import json
import httpx
import certifi
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

# --- 1. Configuration ---
INVENTRA_API_BASE_URL = "https://api.inventra.ca/api"
PRODUCTS_CACHE_FILE = 'product_cache.json'

# --- 2. Application State ---
app_state = {
    "products_data": None
}

# --- 3. Import Core Logic ---
from recommendation_system.analysis_filter import filter_products_by_skin_analysis_api
from recommendation_system.preference_rec.preference_rec import filter_products_by_user_preferences


# --- 4. Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if os.path.exists(PRODUCTS_CACHE_FILE):
        print("Loading products from cache...")
        with open(PRODUCTS_CACHE_FILE, 'r') as f:
            app_state["products_data"] = json.load(f)
    else:
        print("No product cache found. Fetching from API...")
        await fetch_and_cache_products()
    print(f"Service ready. {len(app_state['products_data'].get('products', []))} products loaded.")
    yield
    # Shutdown (if needed)
    print("Shutting down service...")


# --- 5. FastAPI App ---
app = FastAPI(
    title="Recommendation Microservice",
    description="Generates product recommendations based on user skin analysis or explicit user preferences. Returns only product IDs.",
    version="3.1.0",
    lifespan=lifespan
)


# --- 6. Helper Functions (Async API Calls) ---
async def fetch_and_cache_products():
    async with httpx.AsyncClient(verify=certifi.where()) as client:
        try:
            response = await client.get(f"{INVENTRA_API_BASE_URL}/Product/getAllProducts", timeout=30.0)
            response.raise_for_status()
            products = response.json()
            app_state["products_data"] = products
            with open(PRODUCTS_CACHE_FILE, 'w') as f:
                json.dump(products, f, indent=2)
            print(f"Cached {len(products.get('products', []))} products")
        except httpx.RequestError as e:
            print(f"Error fetching products: {e}")
            app_state["products_data"] = {"products": []}


async def get_user_analysis(user_id: int) -> Dict:
    async with httpx.AsyncClient(verify=certifi.where()) as client:
        try:
            response = await client.get(f"{INVENTRA_API_BASE_URL}/SkinAnalysis/latest-all/{user_id}", timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"Failed to fetch analysis for user {user_id}: {e}")
            raise HTTPException(status_code=404, detail=f"Could not fetch analysis for user {user_id}")


async def get_user_preferences(user_id: int) -> Dict[str, Any]:
    url = f"{INVENTRA_API_BASE_URL}/beauty-preferences/{user_id}"
    print(f"Attempting to fetch user preferences from: {url}")
    async with httpx.AsyncClient(verify=certifi.where()) as client:
        try:
            response = await client.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"API error fetching preferences for user {user_id}: {e}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error fetching beauty preferences for user {user_id} from upstream API."
            )
        except httpx.RequestError as e:
            print(f"Network error fetching preferences for user {user_id}: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Could not connect to the beauty preferences service."
            )


# --- 7. Pydantic Models for Responses ---
class AnalysisRecommendationResponse(BaseModel):
    user_id: int
    confidence_threshold: float
    include_preferences: bool
    recommendations_by_condition: Dict[str, List[str]]
    all_product_ids: List[str]


class PreferenceRecommendationResponse(BaseModel):
    user_id: int
    recommended_product_ids: List[str]
    total_recommendations: int


# --- 8. API Endpoints ---
from fastapi.responses import HTMLResponse


@app.get("/", tags=["Documentation"], summary="API Ana Sayfa", description="SmartBeauty API ana sayfası - Swagger UI")
def root():
    html_content = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🧴 SmartBeauty API - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
        <style>
            html {
                box-sizing: border-box;
                overflow: -moz-scrollbars-vertical;
                overflow-y: scroll;
            }
            *, *:before, *:after {
                box-sizing: inherit;
            }
            body {
                margin:0;
                background: #fafafa;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: '/openapi.json',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    layout: "StandaloneLayout",
                    validatorUrl: null,
                    docExpansion: "list",
                    filter: true,
                    showExtensions: true,
                    showCommonExtensions: true,
                    tryItOutEnabled: true
                });
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health", tags=["Monitoring"], summary="Health Check",
         description="API'nin durumunu ve yüklenen ürün sayısını kontrol eder")
def health_check():
    return {
        "status": "healthy",
        "products_loaded": len(app_state["products_data"].get('products', [])) if app_state["products_data"] else 0,
        "timestamp": datetime.now().isoformat(),
        "version": "3.1.0"
    }


@app.post("/cache/refresh", status_code=200, tags=["Admin"], summary="Cache Yenileme",
          description="Ürün cache'ini yeniden yükler")
async def refresh_product_cache():
    await fetch_and_cache_products()
    return {
        "message": "Product cache refresh initiated.",
        "products_loaded": len(app_state['products_data'].get('products', [])),
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }


@app.get(
    "/recommendations/by-analysis/{user_id}",
    response_model=AnalysisRecommendationResponse,
    tags=["Recommendations"],
    summary="Cilt Analizi Önerileri",
    description="Kullanıcının cilt analizi sonuçlarına göre ürün önerileri oluşturur, isteğe bağlı olarak kullanıcı tercihlerini de dahil eder"
)
async def get_recommendations_by_analysis(
        user_id: int,
        confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence score for analysis."),
        max_products: int = Query(5, ge=1, le=50, description="Maximum products per condition."),
        include_preferences: bool = Query(True, description="Include user preferences for personalized scoring and allergen filtering.")
):
    if not app_state.get("products_data") or not app_state["products_data"].get("products"):
        raise HTTPException(status_code=503, detail="Product data is not available.")

    analysis_data = await get_user_analysis(user_id)
    
    # Get user preferences if requested
    user_preferences = None
    if include_preferences:
        try:
            user_preferences = await get_user_preferences(user_id)
        except HTTPException:
            # Continue without preferences if they can't be fetched
            print(f"Warning: Could not fetch preferences for user {user_id}, continuing without preferences")
            pass

    recommended_data_by_condition = filter_products_by_skin_analysis_api(
        analysis_data, app_state["products_data"],
        confidence_threshold=confidence, 
        max_products_per_condition=max_products,
        user_preferences=user_preferences
    )

    # Convert the new format to the expected response format
    formatted_recommendations = {}
    all_product_ids = set()
    
    for condition, products in recommended_data_by_condition.items():
        product_ids = []
        for product in products:
            if isinstance(product, dict) and 'id' in product:
                product_id = str(product['id'])
                product_ids.append(product_id)
                all_product_ids.add(product_id)
            else:
                # Backward compatibility for old format
                product_id = str(product)
                product_ids.append(product_id)
                all_product_ids.add(product_id)
        
        formatted_recommendations[condition] = product_ids

    return {
        "user_id": user_id,
        "confidence_threshold": confidence,
        "include_preferences": include_preferences,
        "recommendations_by_condition": formatted_recommendations,
        "all_product_ids": sorted(list(all_product_ids))
    }


@app.get(
    "/recommendations/by-preferences/{user_id}",
    response_model=PreferenceRecommendationResponse,
    tags=["Recommendations"],
    summary="Kullanıcı Tercihleri Önerileri",
    description="Kullanıcının tercihlerine göre ürün önerileri oluşturur"
)
async def get_recommendations_by_preferences(
        user_id: int,
        max_products: int = Query(20, ge=1, le=100, description="Maximum number of products to recommend.")
):
    if not app_state.get("products_data") or not app_state["products_data"].get("products"):
        raise HTTPException(status_code=503, detail="Product data is not available.")

    preferences_data = await get_user_preferences(user_id)

    recommended_ids = filter_products_by_user_preferences(
        user_preferences=preferences_data,
        products_data=app_state["products_data"],
        max_products=max_products
    )

    recommended_ids_str = [str(pid) for pid in recommended_ids]

    return {
        "user_id": user_id,
        "recommended_product_ids": recommended_ids_str,
        "total_recommendations": len(recommended_ids_str)
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5002)