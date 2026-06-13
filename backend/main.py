from dotenv import load_dotenv
load_dotenv()

from ai_vision.cv_layer import analyze_breadboard_from_bytes
import json
import os
import uuid
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.ioc_parser import router as ioc_parser_router, parse_ioc_content
from services.oauth3legtest import router as oauth3_router, get_access_token, product_search

app = FastAPI(title="Hardware Recon AI Backend")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    image_bytes = await file.read()
    result = analyze_breadboard_from_bytes([(image_bytes, file.content_type)])
    return result

# Define response models
class ReconciliationResponse(BaseModel):
    confidence: float
    reasoning_log: str
    netlist: dict
    schematic_url: Optional[str] = None

@app.post("/api/reconcile", response_model=ReconciliationResponse)
async def reconcile_hardware(
    ioc_file: UploadFile = File(...),
    image_file: UploadFile = File(...),
    parts: Optional[str] = Form(None)
):
    if not ioc_file.filename.endswith('.ioc'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone A upload must be a valid STM32 .ioc configuration file."
        )
        
    if not image_file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone B upload must be a valid JPEG or PNG image."
        )

    try:
        ioc_contents = await ioc_file.read()
        image_bytes = await image_file.read()

        session_id = str(uuid.uuid4())
        session_dir = os.path.join(UPLOAD_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        with open(os.path.join(session_dir, ioc_file.filename), "wb") as f:
            f.write(ioc_contents)
        with open(os.path.join(session_dir, image_file.filename), "wb") as f:
            f.write(image_bytes)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File I/O failure: {str(e)}"
        )

    parsed_parts = []
    if parts:
        try:
            parsed_parts = json.loads(parts)
        except json.JSONDecodeError:
            pass

    # 1. CV — flat wire-segment netlist from the hardware photo
    cv_result = analyze_breadboard_from_bytes([(image_bytes, image_file.content_type)])

    # 2. DigiKey keyword search — one call per part in the manifest
    parts_search_results = {}
    if parsed_parts:
        try:
            token = get_access_token()
            for part in parsed_parts:
                try:
                    parts_search_results[part] = product_search(part, token)
                except Exception as e:
                    parts_search_results[part] = {"error": str(e)}
        except Exception as e:
            parts_search_results = {"error": f"DigiKey auth failed: {str(e)}"}

    # 3. IOC — CubeMX pin-assignment analysis
    ioc_text = ioc_contents.decode("utf-8", errors="replace")
    ioc_result = parse_ioc_content(ioc_text)

    # TODO: run fusion on cv_result, parts_search_results, ioc_result

    return {
        "confidence": 1.0,
        "reasoning_log": ioc_result,
        "netlist": cv_result,
        "schematic_url": None
    }
    
app.include_router(ioc_parser_router, prefix="/preprocess_ioc")
app.include_router(oauth3_router, prefix="/test")
