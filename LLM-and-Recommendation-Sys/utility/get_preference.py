import requests
import json
import os

INVENTRA_API_BASE_URL = "https://api.inventra.ca/api"


def get_user_analysis(user_id: int):
    try:
        response = requests.get(f"{INVENTRA_API_BASE_URL}/beauty-preferences/{user_id}", timeout=5.0)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to fetch analysis for user {user_id}: {e}")
    