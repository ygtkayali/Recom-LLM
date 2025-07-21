from webbrowser import get
import requests
import json
import os

INVENTRA_API_BASE_URL = "https://api.inventra.ca/api"
PRODUCTS_CACHE_FILE = './product_cache.json'

def fetch_and_cache_products():
    try:
        response = requests.get(f"{INVENTRA_API_BASE_URL}/Product/getAllProducts", timeout=30.0)
        response.raise_for_status()
        products = response.json()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cache_file_path = os.path.join(current_dir, PRODUCTS_CACHE_FILE)
        
        with open(cache_file_path, 'w') as f:
            json.dump(products, f, indent=2)
        print(f"Cached {len(products.get('products', []))} products")
    except requests.RequestException as e:
        print(f"Error fetching products: {e}")
        
        
if __name__ == "__main__":
    fetch_and_cache_products()
    print("Product caching complete.")