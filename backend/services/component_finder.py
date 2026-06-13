from fastapi import APIRouter
import requests
import base64

router = APIRouter()

CLIENT_ID = "jwGEXGYCG9GYOZFS1MnCPDBIhXRdIxi0KfEXTusRJauNuJHj"
CLIENT_SECRET = "Zk5SSakgq9xv6FCmtMOV7ohdnfNhlWGCB1jG6A4Scf6wKiK0I8f4QDLLO7mpwrWz"
TOKEN_URL = "https://sandbox-api.digikey.com/v1/oauth2/token"
BASE_URL = "https://sandbox-api.digikey.com/products/v4/search/keyword"

def get_access_token():
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "X-DIGIKEY-Client-Id": CLIENT_ID,
        "Accept": "application/json",
        "X-DIGIKEY-Locale-Site": "CA",
        "X-DIGIKEY-Locale-Language": "en",
        "X-DIGIKEY-Locale-Currency": "CAD",
    }

    data = {
        "grant_type": "client_credentials"
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    if not response.ok:
        print(response.status_code)
        print(response.text)
        response.raise_for_status()
    return response.json()["access_token"]

# ---------------------------
# DIGIKEY SEARCH FUNCTION
# ---------------------------
def search_digikey(keyword: str):
    token = get_access_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "X-DIGIKEY-Client-Id": CLIENT_ID,
        "Content-Type": "application/json",
    }

    payload = {
        "Keywords": keyword,
        "RecordCount": 5
    }

    response = requests.post(BASE_URL, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()

@router.get("/search")
def search():
    keyword = "3492"
    results = search_digikey(keyword)
    return results