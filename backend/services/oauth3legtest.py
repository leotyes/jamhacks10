from fastapi import APIRouter, HTTPException
import requests
import time
import os
import json
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()

CLIENT_ID = os.getenv("DIGIKEY_CLIENT_ID")
CLIENT_SECRET = os.getenv("DIGIKEY_CLIENT_SECRET")
DIGIKEY_TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
DIGIKEY_SEARCH_URL = "https://api.digikey.com/products/v4/search/keyword"

TOKEN_FILE = "digikey_refresh_cache.json"


def load_token_cache():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            print("wtf")
            return json.load(f)
    # Fallback for first run: seed from .env
    print("hi")
    return {
        "access_token": None,
        "refresh_token": os.getenv("DIGIKEY_REFRESH_TOKEN"),
        "expires_at": 0,
    }
    


def save_token_cache(cache):
    with open(TOKEN_FILE, "w") as f:
        json.dump(cache, f)


_token_cache = load_token_cache()


def refresh_access_token():
    print(refresh_access_token)
    response = requests.post(
        DIGIKEY_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": _token_cache["refresh_token"],
            "grant_type": "refresh_token",
        }
    )
    response.raise_for_status()
    data = response.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["refresh_token"] = data["refresh_token"]  # DigiKey rotates this!
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 1800)

    save_token_cache(_token_cache)  # persist immediately so restarts don't lose it

    return _token_cache["access_token"]


def get_access_token():
    if _token_cache["access_token"] and _token_cache["expires_at"] - 60 > time.time():
        return _token_cache["access_token"]
    return refresh_access_token()


def product_search(keyword, token):
    response = requests.post(
        DIGIKEY_SEARCH_URL,
        headers={
            "X-DIGIKEY-Client-Id": CLIENT_ID,
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Locale-Language": "en",
            "X-DIGIKEY-Locale-Site": "CA",
            "X-DIGIKEY-Locale-Currency": "CAD",
            "content-type": "application/json",
            "accept": "application/json",
        },
        data=json.dumps({"Keywords": keyword})
    )
    response.raise_for_status()
    return response.json()


@router.get("/search")
def search(keyword: str = "3492 mems microphone"):
    try:
        token = get_access_token()
        return product_search(keyword, token)
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"DigiKey API error: {e}")