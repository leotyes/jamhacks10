from fastapi import APIRouter, HTTPException
import requests
import time
import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from google.genai import types
load_dotenv()

GEMINI_MODEL = "gemini-3.5-flash"


class PinInterface(BaseModel):
    pins: list[str]          # signal names exposed by the component, e.g. ["GND", "3V3", "CLK", "DAT"]
    notes: str               # brief description of what each pin does / wiring notes

router = APIRouter()

CLIENT_ID = os.getenv("DIGIKEY_CLIENT_ID")
CLIENT_SECRET = os.getenv("DIGIKEY_CLIENT_SECRET")
DIGIKEY_TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
DIGIKEY_SEARCH_URL = "https://api.digikey.com/products/v4/search/keyword"

TOKEN_FILE = "digikey_refresh_cache.json"


def load_token_cache():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
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
    _token_cache["refresh_token"] = data["refresh_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 1800)

    save_token_cache(_token_cache)

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


def enrich_product(product: dict) -> dict:
    """Given the first DigiKey product match, fetch its datasheet and ask Gemini
    to extract the pin/wire interface. Returns an enriched dict with pins + photo."""
    description = (
        product.get("Description", {}).get("DetailedDescription", "")
        or product.get("Description", {}).get("ProductDescription", "")
    )
    datasheet_url = product.get("DatasheetUrl", "")
    photo_url     = product.get("PhotoUrl", "")
    product_url   = product.get("ProductUrl", "")
    manufacturer  = product.get("Manufacturer", {}).get("Name", "")
    part_number   = product.get("ManufacturerProductNumber", "")
    unit_price    = product.get("UnitPrice", None)

    # --- build Gemini contents ---
    api_key = os.environ.get("GEMINI_API_KEY")
    print(api_key)
    client  = genai.Client(api_key=api_key)
    contents: list = []

    prompt = (
        f"You are a hardware pin-interface extraction assistant.\n"
        f"Component: {manufacturer} {part_number} — {description}\n\n"
        f"Your task: identify every signal/wire that connects to this component from the "
        f"datasheet or, if the datasheet is unavailable, from your knowledge of the part.\n"
        f"Return a pins list with the canonical signal name for each pin (e.g. GND, 3V3, CLK, DAT, "
        f"SEL, LR, VDD, DATA, etc.) and a brief notes string summarising wiring requirements."
    )
    contents.append(types.Part.from_text(text=prompt))

    # attach datasheet PDF if fetchable
    if datasheet_url:
        if datasheet_url.startswith("//"):
            datasheet_url = "https:" + datasheet_url
        try:
            pdf_resp = requests.get(datasheet_url, timeout=15)
            pdf_resp.raise_for_status()
            contents.append(
                types.Part.from_bytes(
                    data=pdf_resp.content,
                    mime_type="application/pdf",
                )
            )
        except Exception as exc:
            print(f"[enrich_product] could not fetch datasheet ({exc}); using text-only knowledge")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PinInterface,
            temperature=0.0,
        ),
    )
    if response.parsed is not None:
        pin_iface: PinInterface = response.parsed
    else:
        pin_iface = PinInterface.model_validate(json.loads(response.text))

    return {
        "photo_url":     photo_url,
        "pins":          pin_iface.pins,
        "wiring_notes":  pin_iface.notes,
    }


@router.get("/search")
def search(keyword: str = "3492 mems microphone"):
    try:
        token = get_access_token()
        return product_search(keyword, token)
    except requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"DigiKey API error: {e}")