from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import os
import uuid
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ai_vision.cv_layer import analyze_breadboard_from_bytes
from schematic_generator import generate_schematic

try:
    from services.ioc_parser import router as ioc_parser_router, parse_ioc_content
    from services.oauth3legtest import router as oauth3_router, get_access_token, product_search
    _ioc_parser_available = True
except Exception:
    _ioc_parser_available = False
    ioc_parser_router = None
    oauth3_router = None
    parse_ioc_content = None
    get_access_token = None
    product_search = None

app = FastAPI(title="Circuit Sync Backend")

UPLOAD_DIR = "uploads"
SCHEMATICS_DIR = "schematics"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SCHEMATICS_DIR, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Models ----------

class ReconciliationResponse(BaseModel):
    confidence: float
    reasoning_log: str
    netlist: dict
    schematic_url: Optional[str] = None

class NetlistRequest(BaseModel):
    netlist: dict


# ---------- Endpoints ----------

@app.get("/")
def read_root():
    return {"message": "Circuit Sync backend is running."}


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """Quick single-image breadboard analysis (dev/debug endpoint)."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    image_bytes = await file.read()
    result = analyze_breadboard_from_bytes([(image_bytes, file.content_type)])
    return result


@app.post("/api/reconcile", response_model=ReconciliationResponse)
async def reconcile_hardware(
    ioc_file:   UploadFile = File(...),
    top_image:  UploadFile = File(...),   # Top-down view of the breadboard
    side_image: UploadFile = File(...),   # Side profile view of the breadboard
    parts:      Optional[str] = Form(None)
):
    # --- Validate file types ---
    if not ioc_file.filename.endswith('.ioc'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ioc_file must be a valid STM32 .ioc configuration file."
        )
    for label, img in [("top_image", top_image), ("side_image", side_image)]:
        if not img.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{label}' must be a valid JPEG or PNG image."
            )

    # --- Read file bytes ---
    try:
        ioc_contents = await ioc_file.read()
        top_bytes    = await top_image.read()
        side_bytes   = await side_image.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read uploaded files: {str(e)}"
        )

    # --- Persist to a unique session directory ---
    try:
        session_id  = str(uuid.uuid4())
        session_dir = os.path.join(UPLOAD_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)

        with open(os.path.join(session_dir, ioc_file.filename), "wb") as f:
            f.write(ioc_contents)
        with open(os.path.join(session_dir, f"top_{top_image.filename}"), "wb") as f:
            f.write(top_bytes)
        with open(os.path.join(session_dir, f"side_{side_image.filename}"), "wb") as f:
            f.write(side_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File I/O failure: {str(e)}"
        )

    # --- Parse BOM manifest ---
    parsed_parts: list = []
    if parts:
        try:
            parsed_parts = json.loads(parts)
        except json.JSONDecodeError:
            pass  # Gracefully fall back to empty list

    # --- 1. Vision: wire-segment netlist from both breadboard photos ---
    cv_result = analyze_breadboard_from_bytes([
        (top_bytes,  top_image.content_type),
        (side_bytes, side_image.content_type),
    ])

    # --- 2. DigiKey: keyword search per BOM part ---
    parts_search_results: dict = {}
    if parsed_parts and get_access_token and product_search:
        try:
            token = get_access_token()
            for part in parsed_parts:
                try:
                    parts_search_results[part] = product_search(part, token)
                except Exception as e:
                    parts_search_results[part] = {"error": str(e)}
        except Exception as e:
            parts_search_results = {"error": f"DigiKey auth failed: {str(e)}"}

    # --- 3. IOC: CubeMX pin-assignment analysis (runs in thread to avoid blocking) ---
    ioc_text = ioc_contents.decode("utf-8", errors="replace")
    if parse_ioc_content:
        ioc_result = await asyncio.to_thread(parse_ioc_content, ioc_text)
    else:
        ioc_result = "IOC parser unavailable."

    # --- TODO: fuse cv_result + parts_search_results + ioc_result ---

    return {
        "confidence": 1.0,
        "reasoning_log": ioc_result,
        "netlist": cv_result,
        "schematic_url": None,
    }


@app.post("/generate-schematic")
async def generate_schematic_endpoint(request: NetlistRequest):
    """Generate a KiCad schematic from a netlist dict."""
    output_path = os.path.join(SCHEMATICS_DIR, f"circuit_{uuid.uuid4().hex[:8]}.kicad_sch")
    try:
        generate_schematic(request.netlist, output_file=output_path)
        return FileResponse(
            output_path,
            media_type="application/octet-stream",
            filename="circuit.kicad_sch"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# --- Conditionally register sub-routers ---
if _ioc_parser_available:
    app.include_router(ioc_parser_router, prefix="/preprocess_ioc")
    app.include_router(oauth3_router, prefix="/test")
