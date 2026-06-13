from dotenv import load_dotenv
load_dotenv()

from ai_vision.cv_layer import analyze_breadboard_from_bytes
import asyncio
import json
import os
import uuid
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.ioc_parser import router as ioc_parser_router, parse_ioc_content
from services.oauth3legtest import router as oauth3_router

app = FastAPI(title="Hardware Recon AI Backend")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    result = analyze_breadboard_from_bytes(image_bytes, mime_type=file.content_type)
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
    top_image: UploadFile = File(...),    # Top-down view of the breadboard
    side_image: UploadFile = File(...),   # Side profile view of the breadboard
    parts: Optional[str] = Form(None)
):
    # Validate .ioc file
    if not ioc_file.filename.endswith('.ioc'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zone A upload must be a valid STM32 .ioc configuration file."
        )

    # Validate both images
    for label, img in [("top_image", top_image), ("side_image", side_image)]:
        if not img.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{label}' upload must be a valid JPEG or PNG image."
            )

    try:
        ioc_contents = await ioc_file.read()
        top_bytes   = await top_image.read()
        side_bytes  = await side_image.read()

        session_id  = str(uuid.uuid4())
        session_dir = os.path.join(UPLOAD_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        # Persist all three files with descriptive names
        with open(os.path.join(session_dir, ioc_file.filename), "wb") as f:
            f.write(ioc_contents)
        with open(os.path.join(session_dir, f"top_{top_image.filename}"), "wb") as f:
            f.write(top_bytes)
        with open(os.path.join(session_dir, f"side_{side_image.filename}"), "wb") as f:
            f.write(side_bytes)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reconciliation engine failure: {str(e)}"
        )

    parsed_parts = []
    if parts:
        try:
            parsed_parts = json.loads(parts)
        except json.JSONDecodeError:
            pass
            
    # Call the CubeMX Parser asynchronously off the main thread
    ioc_text = ioc_contents.decode("utf-8", errors="replace")
    gemini_result = await asyncio.to_thread(parse_ioc_content, ioc_text)

    """
    response_data = {
        "confidence": 0.98 if parsed_parts else 0.94,
        "reasoning_log": (
            "✅ Analysis Complete\n------------------\n"
            f"Loaded manifest parts: {', '.join(parsed_parts) if parsed_parts else 'None'}\n"
            "Parsed 32 active controller pins from .ioc.\n"
            "Vision Engine located: 1x LED, 1x Resistor.\n"
            "Reconciled layout matching is correct."
        ),
        "netlist": {
            "components": [
                { "id": "U1", "type": "STM32F401" },
                { "id": "D1", "type": "LED", "color": "Red" },
                { "id": "R1", "type": "Resistor", "value": "220Ω" }
            ],
            "nets": [
                { "id": "N1", "nodes": ["U1.PA5", "D1.A"] },
                { "id": "N2", "nodes": ["D1.K", "R1.1"] },
                { "id": "GND", "nodes": ["R1.2", "U1.GND"] }
            ]
        },
        "schematic_url": "/static/schematics/output_schematic.kicad_sch"
    }
    """
    
    return {
        "confidence": 1.0,
        "reasoning_log": gemini_result,
        "netlist": {"components": [], "nets": []},
        "schematic_url": None
    }
    
app.include_router(ioc_parser_router, prefix="/preprocess_ioc")
app.include_router(oauth3_router, prefix="/test")