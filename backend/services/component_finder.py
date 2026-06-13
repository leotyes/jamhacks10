from fastapi import APIRouter, HTTPException
import requests
import time
from dotenv import load_dotenv
load_dotenv()
import os
import json

router = APIRouter()

CLIENT_ID = os.getenv("DIGIKEY_CLIENT_ID")
CLIENT_SECRET = os.getenv("DIGIKEY_CLIENT_SECRET")
DIGIKEY_TOKEN_URL_V4 = 'https://sandbox-api.digikey.com/v1/oauth2/token'
DIGIKEY_PRODUCT_SEARCH_URL_V4 = 'https://sandbox-api.digikey.com/products/v4/search/keyword'

# Simple in-memory token cache
_token_cache = {
    "access_token": None,
    "expires_at": 0,  # epoch timestamp
}


def oauthV2_get_simple_access_token(url, client_id, client_secret):
    response = requests.post(
        url,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }
    )
    response.raise_for_status()
    return response.json()


def get_cached_access_token():
    """Return a cached token if still valid, otherwise fetch a new one."""
    now = time.time()

    # Add a buffer (e.g. 60s) so we refresh slightly before actual expiry
    if _token_cache["access_token"] and _token_cache["expires_at"] - 60 > now:
        return _token_cache["access_token"]

    token_response = oauthV2_get_simple_access_token(
        DIGIKEY_TOKEN_URL_V4, CLIENT_ID, CLIENT_SECRET
    )

    _token_cache["access_token"] = token_response["access_token"]
    _token_cache["expires_at"] = now + token_response.get("expires_in", 600)

    return _token_cache["access_token"]


def oauthv2_product_search(url, client_id, token, keyword):
    data_payload = {"Keywords": str(keyword)}
    print(token)
    print(client_id)
    response = requests.post(
        url,
        headers={
            "X-DIGIKEY-Client-Id": client_id,
            "authorization": f"Bearer {token}",
            "content-type": "application/json",
            "accept": "application/json",
        },
        data=json.dumps(data_payload)
    )
    response.raise_for_status()
    return response.json()


@router.get("/search")
def search(keyword: str = "4346"):
    try:
        access_token = get_cached_access_token()
        search_result = oauthv2_product_search(
            DIGIKEY_PRODUCT_SEARCH_URL_V4, CLIENT_ID, access_token, keyword
        )
        return search_result
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"DigiKey API error: {e}")